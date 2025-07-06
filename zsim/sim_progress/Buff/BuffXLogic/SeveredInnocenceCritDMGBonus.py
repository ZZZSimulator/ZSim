from .. import Buff, JudgeTools, check_preparation, find_tick


class SeveredInnocenceCritDMGBonusRecord:
    def __init__(self):
        self.char = None
        self.equipper = None
        self.update_signal = []
        self.active_tick_box = {
            0: {"start": 0, "end": 0},
            1: {"start": 0, "end": 0},
            2: {"start": 0, "end": 0},
        }
        self.sub_exist_buff_dict = None


class SeveredInnocenceCritDMGBonus(Buff.BuffLogic):
    """
    牺牲洁纯的层数判定
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0 = None
        self.equipper = None
        self.record = None
        self.xjudge = self.special_judge_logic
        self.xstart = self.special_start_logic

    def get_prepared(self, **kwargs):
        return check_preparation(
            buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs
        )

    def check_record_module(self):
        if self.equipper is None:
            self.equipper = JudgeTools.find_equipper(
                "牺牲洁纯", sim_instance=self.buff_instance.sim_instance
            )
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )[self.equipper][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = SeveredInnocenceCritDMGBonusRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """
        在判断函数阶段，就根据传入的skill_node，进行CID、mission子标签的筛选，
        将属于安比的、start子标签的 普攻、特殊技以及追加攻击记录下来，
        并且更新进record中的update_signal中
        """
        self.check_record_module()
        self.get_prepared(char_CID=1381, equipper="牺牲洁纯")
        _skill_node = kwargs.get("skill_node", None)
        _loading_mission = kwargs.get("loading_mission", None)
        if _skill_node is None:
            raise ValueError(
                f"{self.buff_instance.ft.index}的xjudge函数并未获取到skill_node"
            )
        if _loading_mission is None:
            raise ValueError(
                f"{self.buff_instance.ft.index}的xjudge函数并未获取到loading_mission"
            )
        from zsim.sim_progress.Preload import SkillNode

        if not isinstance(_skill_node, SkillNode):
            raise TypeError(f"{_skill_node}不是SkillNode类")
        tick = find_tick(sim_instance=self.buff_instance.sim_instance)
        if str(self.record.char.CID) not in _skill_node.skill_tag:
            return False
        if not tick - 1 < _skill_node.preload_tick <= tick:
            return False
        if _skill_node.skill.labels is not None:
            if "aftershock_attack" in _skill_node.skill.labels.keys():
                self.record.update_signal.append(2)
                return True
        elif _skill_node.skill.trigger_buff_level == 0:
            self.record.update_signal.append(0)
            return True
        elif _skill_node.skill.trigger_buff_level in [1, 2]:
            self.record.update_signal.append(1)
            return True
        else:
            return False

    def special_start_logic(self, **kwargs):
        """
        在正式更新阶段，对update_signal进行pop遍历，把每个signal挨个拿出来进行处理，
        并且按照individual_settled类Buff的更新规则，将其转换成built_in_buff_box，并且替换原有的。
        最终实现不同Buff层数的管理。
        """
        self.check_record_module()
        self.get_prepared(char_CID=1381, equipper="牺牲洁纯", sub_exist_buff_dict=1)
        tick = find_tick(sim_instance=self.buff_instance.sim_instance)
        if not self.record.update_signal:
            return
        reset_list = list(set(self.record.update_signal))
        while reset_list:
            update_signal = reset_list.pop()
            self.record.active_tick_box[update_signal]["start"] = tick
            self.record.active_tick_box[update_signal]["end"] = (
                tick + self.buff_instance.ft.maxduration
            )
        self.buff_instance.simple_start(
            tick, self.record.sub_exist_buff_dict, no_count=1
        )
        self.buff_instance.dy.built_in_buff_box = []
        for _mode_index, _sub_dict in self.record.active_tick_box.items():
            if self.record.active_tick_box[_mode_index]["end"] > tick:
                self.buff_instance.dy.built_in_buff_box.append(list(_sub_dict.values()))
        self.buff_instance.dy.count = len(self.buff_instance.dy.built_in_buff_box)
        self.buff_instance.update_to_buff_0(self.buff_0)
