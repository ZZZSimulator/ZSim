from copy import deepcopy

from .. import Buff, JudgeTools, check_preparation, find_tick


class YanagiPolarityDisorderTriggerRecord:
    def __init__(self):
        self.char = None
        self.enemy = None
        self.polarity_disorder_update_signal = (
            False  # 极性紊乱更新信号：理论上生命周期只有0个tick，本tick放行，本tick处理后重置
        )
        self.e_counter = {"update_from": "", "count": 0}  # 突刺攻击的计数器
        self.e_max_count = None  # 突刺攻击的最大次数
        self.polarity_disorder_basic_dmg_ratio = None  # 极性紊乱的基础倍率
        self.polarity_disorder_ap_ratio = 32  # 固定的3200%精通倍率


class YanagiPolarityDisorderTrigger(Buff.BuffLogic):
    """
    柳的极性紊乱的触发器。
    极性紊乱会在强化E下落攻击和Q的最后一个Hit触发，
    若是一个招式内同时触发了感电和极性紊乱，则应该先结算感电，再结算极性紊乱；
    根据目前ZSim的结构，属性异常检测、属性异常更新、Buff判断循环启动这几个步骤的顺序应该为：
    Buff判断循环启动 ——> 触发器启动 ——> 属性异常更新——> 技能伤害计算——> 异常条更新
    所以，如果在极性紊乱更新的Tick，同时触发了新的属性异常，
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xeffect = self.special_effect_logic
        self.buff_0 = None
        self.record = None

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["柳"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = YanagiPolarityDisorderTriggerRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs) -> bool:
        """
        柳的极性紊乱的触发器判断机制，即Enemy身上存在属性异常，就放行，并且向record释放更新信号。
        """
        self.check_record_module()
        self.get_prepared(char_CID=1221, enemy=1)
        obj_input = kwargs.get("skill_node", None)
        # 筛选出能够和极性紊乱系统互动的三种技能
        if obj_input is None:
            return False

        from zsim.sim_progress.Load import LoadingMission
        from zsim.sim_progress.Preload import SkillNode

        if not isinstance(obj_input, SkillNode | LoadingMission):
            raise TypeError(
                f"{self.buff_instance.ft.index}的xjudge模块中获取到的{obj_input}不是SkillNode类也不是LoadingMission类！"
            )
        skill_node = obj_input if isinstance(obj_input, SkillNode) else obj_input.mission_node
        if skill_node.skill_tag not in ["1221_E_EX_1", "1221_E_EX_2", "1221_Q"]:
            return False

        # 正确性判断
        if self.record.polarity_disorder_update_signal:
            raise ValueError("上一次极性紊乱的更新信号仍旧存在，请检查代码")

        # 如果检测到穿刺攻击，则进入对应分支——更新连击次数，但是最后要返回False——因为穿刺攻击无法结算极性紊乱；
        if skill_node.skill_tag == "1221_E_EX_1":
            # 如果上一次更新的UUID是空，则说明是第一个动作，或者是一个全新的强化E的开始，则直接跳过第一轮分支，进入连击次数更新环节。
            if self.record.e_counter["update_from"] == "":
                pass
            else:
                # 如果UUID相同，说明是同一个技能的不同hit，直接返回False
                if skill_node.UUID == self.record.e_counter["update_from"]:
                    return False

            if self.record.char.cinema >= 2:
                if self.record.e_max_count is None:
                    self.record.e_max_count = 2 if self.record.char.cinema < 6 else 4
                self.record.e_counter["count"] += 1
                if self.record.e_counter["count"] >= self.record.e_max_count:
                    self.record.e_counter["count"] = self.record.e_max_count
                self.record.e_counter["update_from"] = skill_node.UUID
            return False
        # 若是另外两个攻击，则应该检查是否是最后一跳，放行前，打开更新信号。
        else:
            tick = find_tick(sim_instance=self.buff_instance.sim_instance)
            if tick - 1 < skill_node.loading_mission.get_last_hit() <= tick:  # 此时就是最后一跳
                if self.record.enemy.dynamic.is_under_anomaly():  # 并且存在激活的属性异常
                    self.record.polarity_disorder_update_signal = True
                    return True
                self.record.e_counter = {"update_from": "", "count": 0}
            return False

    def special_effect_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(char_CID=1221, enemy=1)
        if not self.record.polarity_disorder_update_signal:
            raise ValueError("在极性紊乱触发信号未激活时，执行了触发函数！")

        # 根据角色命座，初始化基础倍率
        if self.record.polarity_disorder_basic_dmg_ratio is None:
            self.record.polarity_disorder_basic_dmg_ratio = (
                0.15 if self.record.char.cinema < 2 else 0.2
            )

        # 根据连击次数，计算最终缩放倍率
        final_ratio = (
            self.record.polarity_disorder_basic_dmg_ratio + 0.15 * self.record.e_counter["count"]
        )

        # 获取当前正在激活的属性异常条
        active_anomaly_bar = self.record.enemy.get_active_anomaly_bar()

        active_bar_deep_copy = deepcopy(active_anomaly_bar)

        # 构造极性紊乱对象
        from zsim.sim_progress.Update import spawn_output

        polarity_disorder_output = spawn_output(
            active_bar_deep_copy,
            mode_number=2,
            polarity_ratio=final_ratio,
            skill_node=kwargs["skill_node"],
            sim_instance=self.buff_instance.sim_instance,
        )
        # polarity_disorder_output = spawn_output(active_anomaly_bar, mode_number=1)
        # 置入event_list
        event_list = JudgeTools.find_event_list(sim_instance=self.buff_instance.sim_instance)
        event_list.append(polarity_disorder_output)

        # 清空记录，回收更新信号
        self.record.e_counter = {"update_from": "", "count": 0}
        self.record.polarity_disorder_update_signal = False
