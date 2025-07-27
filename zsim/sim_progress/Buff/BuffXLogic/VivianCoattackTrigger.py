from zsim.define import VIVIAN_REPORT

from .. import Buff, JudgeTools, check_preparation, find_tick


class VivianCoattackTriggerRecord:
    def __init__(self):
        self.char = None
        self.preload_data = None
        self.last_update_node = None
        self.JUDGE_MAP = {
            "1221_E_EX_1": lambda: self.last_update_node.end_tick
            >= find_tick(sim_instance=self.char.sim_instance),
            "1221_E_EX_2": lambda: False,
        }


class VivianCoattackTrigger(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """薇薇安的协同攻击（落雨生花）触发器"""
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0 = None
        self.record = None
        self.xjudge = self.special_judge_logic
        self.xeffect = self.special_effect_logic

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["薇薇安"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = VivianCoattackTriggerRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """检测到队友释放强化E并且第一跳命中时放行。"""
        self.check_record_module()
        self.get_prepared(char_CID=1331, preload_data=1)
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            return
        from zsim.sim_progress.Load import LoadingMission
        from zsim.sim_progress.Preload import SkillNode

        if not isinstance(skill_node, SkillNode | LoadingMission):
            return
        if isinstance(skill_node, LoadingMission):
            skill_node = skill_node.mission_node
        # 首先过滤所有非强化E标签的技能
        if skill_node.skill.trigger_buff_level != 2:
            return False

        # 过滤所有并非第一跳的技能
        tick = find_tick(sim_instance=self.buff_instance.sim_instance)
        if not skill_node.loading_mission.is_first_hit(tick):
            return False

        # 如果是首次传入，直接放行
        if self.record.last_update_node is None:
            self.record.last_update_node = skill_node
            return True
        else:
            # 并非首次传入时，判断是否是同一个技能
            if skill_node.UUID == self.record.last_update_node.UUID:
                return False
            else:
                # 若是不同技能，进入最后一个判断分支
                if skill_node.skill_tag in self.record.JUDGE_MAP:
                    result = self.record.JUDGE_MAP[skill_node.skill_tag]()
                    if result:
                        self.record.last_update_node = skill_node
                    else:
                        return False
                else:
                    self.record.last_update_node = skill_node
                    return True

    def special_effect_logic(self, **kwargs):
        """执行后直接添加一次落雨生花到eventlist——该动作没有动画，所以直接进event_list即可"""
        self.check_record_module()
        self.get_prepared(char_CID=1361, preload_data=1)
        coattack_skill_tag = self.record.char.feather_manager.spawn_coattack()
        if coattack_skill_tag is None:
            if VIVIAN_REPORT:
                self.buff_instance.sim_instance.schedule_data.change_process_state()
                print(
                    f"【落雨生花】触发器：虽然监听到了队友的强化E：{self.record.last_update_node.skill_tag}，但是豆子不够！当前资源情况为：{self.record.char.get_special_stats()}"
                )
            return
        input_tuple = (coattack_skill_tag, False, 0)
        self.record.preload_data.external_add_skill(input_tuple)
        if VIVIAN_REPORT:
            self.buff_instance.sim_instance.schedule_data.change_process_state()
            print(
                f"【落雨生花】触发器：监测到强化特殊技{self.record.last_update_node.skill_tag}，薇薇安成功触发了一次落雨生花！(迟滞1tick）"
            )
