from .. import Buff, JudgeTools, check_preparation, find_tick
from zsim.sim_progress.Enemy import Enemy
from zsim.define import HUGO_REPORT


class HugoCorePassiveTotalizeTriggerRecord:
    def __init__(self):
        self.char = None
        self.enemy: Enemy | None = None
        self.active_signal = None
        self.E_totalize_tag = "1291_CorePassive_E_EX"
        self.Q_totalize_tag = "1291_CorePassive_Q"
        self.totalize_buff_index = "Buff-角色-雨果-决算倍率增幅"
        self.abyss_reverb_buff_index = "Buff-角色-雨果-核心被动-暗渊回响"
        self.cinema_1_buff_index = "Buff-角色-雨果-1画-决算招式双暴增幅"
        self.cinema_2_buff_index = "Buff-角色-雨果-2画-决算招式无视防御力"
        self.cinema_6_buff_index = "Buff-角色-雨果-6画-决算招式增伤"
        self.preload_data = None
        self.shot_attack_list = [
            "1291_SNA_2_NFC",
            "1291_SNA_2_FC",
            "1291_SCA",
            "1291_SCA_FC",
            "1291_NA_A",
            "1291_NA_A_FC",
            "1291_BH_Aid_A",
            "1291_BH_Aid_A_FC",
        ]
        # self.fc_shot_attack_list = [
        #     "1291_SNA_2_FC",
        #     "1291_SCA_FC",
        #     "1291_NA_A_FC",
        #     "1291_BH_Aid_A_FC",
        # ]


class HugoCorePassiveTotalizeTrigger(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """雨果核心被动，决算触发器"""
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0: Buff | None = None
        self.record: HugoCorePassiveTotalizeTriggerRecord | None = None
        self.xjudge = self.special_judge_logic
        self.xhit = self.special_hit_logic

    def get_prepared(self, **kwargs):
        return check_preparation(
            buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs
        )

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["雨果"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = HugoCorePassiveTotalizeTriggerRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """敌人处于失衡状态时，强化E、大招触发"""
        self.check_record_module()
        self.get_prepared(char_CID=1291, enemy=1, preload_data=1)
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        from zsim.sim_progress.Preload import SkillNode

        if not isinstance(skill_node, SkillNode):
            raise TypeError(
                f"{self.buff_instance.ft.index}的xjudge函数获取到的skill_node不是SkillNode类型"
            )

        # 过滤不是自己的技能
        if "1291" not in skill_node.skill_tag:
            return False

        # 过滤不是E、大招的技能
        if skill_node.skill.trigger_buff_level not in [2, 6]:
            """6画时，任何射击攻击都可以借由本触发器来执行暗渊回响Buff的触发"""
            if (
                self.record.char.cinema == 6
                and skill_node.skill_tag in self.record.shot_attack_list
            ):
                if skill_node.loading_mission is None:
                    raise ValueError(
                        f"{skill_node.skill_tag}本应该有loading_mission，但是没有"
                    )
                if not skill_node.loading_mission.is_last_hit(
                    find_tick(sim_instance=self.buff_instance.sim_instance)
                ):
                    return False
                else:
                    self.record.active_signal = skill_node.skill.trigger_buff_level
                    return True
            else:
                return False

        # 过滤掉无法触发决算的第一段强化E
        if skill_node.skill_tag == "1291_E_EX_1":
            return False

        # 过滤掉可能进入Buff循环的决算？？大概率不可能吧，决算能进BuffLoad那真的是见鬼了
        if skill_node.skill.labels is not None:
            if "totalize" in skill_node.skill.labels:
                return False

        # 过滤不是最后一次命中的技能
        if skill_node.loading_mission is None:
            return False
        if not skill_node.loading_mission.is_last_hit(
            find_tick(sim_instance=self.buff_instance.sim_instance)
        ):
            return False

        if self.record.active_signal is not None:
            raise ValueError(
                f"雨果的决算触发器在运行时候发现存在就一个未被结算的信号{self.record.active_signal}，这是不允许的"
            )
        # 如果是6命，则无条件放行强化E
        if self.record.char.cinema == 6 and skill_node.skill.trigger_buff_level == 2:
            self.record.active_signal = skill_node.skill.trigger_buff_level
            return True
        else:
            # 否则，检测敌人是否处于失衡状态
            if self.record.enemy.dynamic.stun:
                self.record.active_signal = skill_node.skill.trigger_buff_level
                return True
            else:
                return False

    def special_hit_logic(self, **kwargs):
        """结算E、大招"""
        self.check_record_module()
        self.get_prepared(char_CID=1291, enemy=1, preload_data=1)
        if self.record.active_signal is None:
            raise ValueError(
                "雨果的决算触发器的Xjudge函数放行了，但是Xhit函数却没有获取到触发信号"
            )
        if self.record.active_signal not in [0, 2, 6]:
            raise ValueError(
                f"雨果的决算触发器的Xjudge函数放行了，但是给出了非法信号！触发信号：{self.record.active_signal}"
            )
        elif self.record.active_signal == 0 and self.record.char.cinema != 6:
            raise ValueError(
                f"在非6画的情况下检测到了非法的触发信号：{self.record.active_signal}"
            )
        """准备数据"""
        event_list = JudgeTools.find_event_list(
            sim_instance=self.buff_instance.sim_instance
        )
        rest_tick = self.record.enemy.get_stun_rest_tick()
        ratio = (
            1000
            + min(300, rest_tick) / 60 * 280
            + min(600, max(rest_tick - 300, 0)) / 60 * 100
        )
        if self.record.active_signal in [2, 6]:
            if HUGO_REPORT:
                self.buff_instance.sim_instance.schedule_data.change_process_state()
                print(
                    f"雨果使用{'大招' if self.record.active_signal == 6 else '强化E'}触发了决算！本次决算结算的失衡时间为{rest_tick / 60:.2f}秒，结算倍率为{ratio:.2f}%，"
                )
        else:
            if HUGO_REPORT:
                self.buff_instance.sim_instance.schedule_data.change_process_state()
                print(
                    "6画触发：检测到射击攻击命中！为雨果触发一次暗渊回响Buff！"
                )

        """先处理Buff"""
        from zsim.sim_progress.Buff.BuffAddStrategy import buff_add_strategy

        if self.record.active_signal == 0:
            abyss_reverb_buff_index = self.record.abyss_reverb_buff_index
            buff_add_strategy(
                abyss_reverb_buff_index,
                benifit_list=["雨果"],
                sim_instance=self.buff_instance.sim_instance,
            )
            self.record.active_signal = None
            """触发信号为0时，只添加Buff，不执行后面的逻辑。"""
            return
        else:
            buff_index = self.record.totalize_buff_index
            buff_add_strategy(
                buff_index,
                specified_count=ratio,
                benifit_list=["雨果"],
                sim_instance=self.buff_instance.sim_instance,
            )
            stun_value_feed_back_ratio = min(rest_tick / 60, 5) * 0.05
            if self.record.char.cinema >= 1:
                cinema_1_buff_index = self.record.cinema_1_buff_index
                buff_add_strategy(
                    cinema_1_buff_index,
                    benifit_list=["雨果"],
                    sim_instance=self.buff_instance.sim_instance,
                )
            if self.record.char.cinema >= 2:
                cinema_2_buff_index = self.record.cinema_2_buff_index
                buff_add_strategy(
                    cinema_2_buff_index,
                    benifit_list=["雨果"],
                    sim_instance=self.buff_instance.sim_instance,
                )
            if self.record.char.cinema == 6:
                cinema_6_buff_index = self.record.cinema_6_buff_index
                buff_add_strategy(
                    cinema_6_buff_index,
                    benifit_list=["雨果"],
                    sim_instance=self.buff_instance.sim_instance,
                )

        """再生成决算的skill_node"""
        from zsim.sim_progress.Preload.SkillsQueue import spawn_node
        from zsim.sim_progress.Load import LoadingMission

        if self.record.active_signal == 2:
            node_tag = self.record.E_totalize_tag
        elif self.record.active_signal == 6:
            node_tag = self.record.Q_totalize_tag
        else:
            raise ValueError(
                "雨果的决算触发器的Xjudge函数放行了，但是给出的信号不是强化E、大招"
            )
        totalize_node = spawn_node(
            node_tag,
            find_tick(sim_instance=self.buff_instance.sim_instance),
            self.record.preload_data.skills,
        )
        """给予技能节点一个loading_mission"""
        totalize_node.loading_mission = LoadingMission(totalize_node)
        totalize_node.loading_mission.mission_start(
            find_tick(sim_instance=self.buff_instance.sim_instance)
        )
        event_list.append(totalize_node)

        """失衡状态强制结算事件"""
        from zsim.sim_progress.data_struct import StunForcedTerminationEvent

        if self.record.enemy.dynamic.stun:
            if self.record.char.cinema >= 2 and self.record.active_signal == 6:
                if HUGO_REPORT:
                    self.buff_instance.sim_instance.schedule_data.change_process_state()
                    print(
                        "2画触发：检测到雨果释放大招，根据2画效果，本次决算不终结失衡状态！"
                    )
                stun_event = None
            else:
                stun_event = StunForcedTerminationEvent(
                    self.record.enemy,
                    stun_value_feed_back_ratio,
                    execute_tick=find_tick(
                        sim_instance=self.buff_instance.sim_instance
                    ),
                    event_source="雨果",
                )
        else:
            if self.record.char.cinema != 6:
                raise ValueError(
                    "雨果的决算触发器的Xjudge函数放行了，但是敌人并未处于失衡状态，这对于非6画雨果来说是不允许的。"
                )
            elif self.record.active_signal != 2:
                raise ValueError(
                    f"触发信号为{self.record.active_signal}，这意味着6画雨果的大招在非失衡期触发了决算，这是不允许的"
                )
            else:
                stun_event = None

        """2画以上的大招触发决算时，不结算失衡状态。"""
        if stun_event is not None:
            event_list.append(stun_event)

        """重置信号"""
        self.record.active_signal = None
