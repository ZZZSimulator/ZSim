from .. import Buff, JudgeTools, check_preparation, find_tick


class TriggerAfterShockTriggerRecord:
    def __init__(self):
        self.char = None
        self.preload_data = None
        self.active_signal_mission = None
        self.after_shock_manager = None


class TriggerAfterShockTrigger(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """扳机的协同攻击触发器"""
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0 = None
        self.record = None
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
            )["扳机"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = TriggerAfterShockTriggerRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """
        触发器的xjudge函数，负责判断当前攻击是否能够触发协同攻击
        """
        self.check_record_module()
        self.get_prepared(char_CID=1361, preload_data=1)
        loading_mission = kwargs.get("loading_mission", None)
        if loading_mission is None:
            raise ValueError(
                f"{self.buff_instance.ft.index}的xjudge函数中，传入的loading_mission为None！"
            )
        from zsim.sim_progress.Load import LoadingMission

        if not isinstance(loading_mission, LoadingMission):
            raise TypeError(
                f"{self.buff_instance.ft.index}的xjudge函数中，传入的loading_mission类型错误！"
            )
        tick = find_tick(sim_instance=self.buff_instance.sim_instance)
        """如果当前mission不是hit，则不触发"""
        if not loading_mission.is_hit_now(tick):
            return False

        """如果当前mission是扳机自己的动作，也不触发"""
        if "1361" in loading_mission.mission_tag:
            return False

        """
        剩余情况汇总：队友的、正在命中的skill_node，即为可能触发协同攻击的skill_node，
        但是，这里是不包含 扳机 决意值 的判断逻辑的，
        因为在after_shock管理器中，决意值不够时会直接返回None。
        """
        self.record.active_signal_mission = loading_mission

        return True

    def special_hit_logic(self, **kwargs):
        """
        扳机的协同攻击触发的核心函数，负责抛出对应的协同攻击给Preload，
        同时更新角色的决意值、协战状态管理器数据
        """
        self.check_record_module()
        self.get_prepared(char_CID=1361, preload_data=1)
        if self.record.active_signal_mission is None:
            raise ValueError(
                f"{self.buff_instance.ft.index}的xjudge函数在本tick通过判定，但是并未将通过判定的skill_node传入自身的record中"
            )
        tick = find_tick(sim_instance=self.buff_instance.sim_instance)
        after_shock_tag = self.record.char.after_shock_manager.spawn_after_shock(
            tick, self.record.active_signal_mission
        )
        if after_shock_tag is not None:
            insert_tuple = (after_shock_tag, False, 0)
            self.record.preload_data.preload_action_list_before_confirm.append(
                insert_tuple
            )
