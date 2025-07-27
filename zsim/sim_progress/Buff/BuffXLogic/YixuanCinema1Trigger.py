from typing import TYPE_CHECKING

from zsim.define import YIXUAN_REPORT

from .. import Buff, JudgeTools, check_preparation

if TYPE_CHECKING:
    from zsim.sim_progress.Character.Yixuan import Yixuan
    from zsim.sim_progress.Preload import SkillNode
    from zsim.sim_progress.Preload.PreloadDataClass import PreloadData


class YixuanCinema1TriggerRecord:
    def __init__(self):
        self.char = None
        self.lighting_strike_skill_tag = "1371_Cinema_1"
        self.preload_data = None
        self.adrenaline_value = 5
        self.sub_exist_buff_dict = None


class YixuanCinema1Trigger(Buff.BuffLogic):
    """仪玄1画的触发器"""

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xhit = self.special_hit_logic
        self.buff_0 = None
        self.record = None

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["仪玄"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = YixuanCinema1TriggerRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """仪玄1画的触发器逻辑，当任意技能命中时放行。"""
        self.check_record_module()
        self.get_prepared(char_CID=1371)
        skill_node: "SkillNode | None" = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        tick = self.buff_instance.sim_instance.tick
        if skill_node.char_name == "仪玄":
            return False
        if skill_node.is_hit_now(tick):
            return True
        return False

    def special_hit_logic(self, **kwargs):
        """向event_list抛出一个落雷以及恢复角色5点闪能值"""
        self.check_record_module()
        self.get_prepared(char_CID=1221, preload_data=1, sub_exist_buff_dict=1)
        preload_data: "PreloadData" = self.record.preload_data
        char: "Yixuan" = self.record.char
        simulator = self.buff_instance.sim_instance
        event_list = simulator.schedule_data.event_list
        tick = simulator.tick
        # 处理落雷
        from zsim.sim_progress.Load import LoadingMission
        from zsim.sim_progress.Preload.SkillsQueue import spawn_node

        lightning_strick_node: "SkillNode" = spawn_node(
            tag=self.record.lighting_strike_skill_tag,
            preload_tick=tick,
            skills=preload_data.skills,
        )
        loading_mission = LoadingMission(mission=lightning_strick_node)
        loading_mission.mission_start(tick)
        lightning_strick_node.loading_mission = loading_mission
        event_list.append(lightning_strick_node)

        char.update_adrenaline(sp_value=self.record.adrenaline_value)
        self.buff_instance.simple_start(
            timenow=tick, sub_exist_buff_dict=self.record.sub_exist_buff_dict
        )
        if YIXUAN_REPORT:
            print(
                f"1画：生成一道落雷，并且为仪玄回复5点闪能值，仪玄当前闪能值：{char.adrenaline: .2f}"
            )
            self.buff_instance.sim_instance.schedule_data.change_process_state()
