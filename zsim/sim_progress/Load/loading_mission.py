from zsim.sim_progress.Preload import SkillNode
from zsim.sim_progress.Report import report_to_log


class LoadingMission:
    def __init__(self, mission: SkillNode):
        self.mission_active_state = False
        self.mission_node = mission
        self.mission_dict = {}
        self.mission_start_tick = mission.preload_tick
        self.hitted_count = 0  # 已经结算的hit数量
        self.mission_tag = mission.skill_tag
        self.mission_end_tick = mission.end_tick
        self.mission_character = mission.char_name
        self.preload_tick = mission.preload_tick
        self.mission_node.loading_mission = self

    def mission_start(self, timenow, **kwargs):
        report = kwargs.get("report", True)
        self.mission_active_state = True
        timecost = self.mission_node.skill.ticks
        if timecost:
            time_step = (timecost - 1) / (self.mission_node.hit_times + 1)
            self.mission_dict[float(self.mission_node.preload_tick)] = "start"
            # if self.mission_node.hit_times == 1:
            #     self.mission_dict[float(self.mission_node.preload_tick+timecost - 1)/2] = "hit"
            # else:
            if self.mission_node.skill.tick_list:
                for hit_tick in self.mission_node.skill.tick_list:
                    tick_key = self.mission_node.preload_tick + hit_tick
                    self.mission_dict[tick_key] = "hit"
            else:
                for i in range(self.mission_node.hit_times):
                    tick_key = self.mission_node.preload_tick + time_step * (i + 1)
                    # 由于timetick在循环中的自增量是整数，所以为了保证能和键值准确匹配，
                    # 这里的键值也要向上取整，注意，这里产生的是一个int，所以要转化为float
                    self.mission_dict[tick_key] = "hit"
            self.mission_dict[float(self.mission_node.preload_tick + timecost)] = "end"
            report_to_log(
                f"[Skill LOAD]:{timenow}:{self.mission_tag}开始并拆分子任务。", level=4
            ) if report else None
        else:
            self.mission_dict[timenow] = "hit"

    def mission_end(self):
        self.mission_active_state = False
        self.hitted_count = 0
        self.mission_dict = {}

    def check_myself(self, timenow):
        if self.mission_end_tick < timenow:
            self.mission_end()
            return

    def get_first_hit(self):
        """返回首次命中的时间"""
        tick_list = list(self.mission_dict.keys())
        while tick_list:
            tick = min(tick_list)
            if self.mission_dict[tick] == "hit":
                return tick
            else:
                tick_list.remove(tick)

    def is_hit_now(self, tick_now: int) -> bool:
        """检测当前tick是否有hit事件。"""
        for _tick in self.mission_dict.keys():
            if tick_now - 1 < _tick <= tick_now:
                if self.mission_dict[_tick] == "hit":
                    return True
        else:
            return False

    def get_last_hit(self):
        """返回最后一次命中的时间"""
        tick_list = list(self.mission_dict.keys())
        while tick_list:
            tick = max(tick_list)
            if self.mission_dict[tick] == "hit":
                return tick
            else:
                tick_list.remove(tick)

    def is_first_hit(self, tick: int):
        return tick - 1 < self.get_first_hit() <= tick

    def is_last_hit(self, tick: int):
        return tick - 1 < self.get_last_hit() <= tick

    def is_heavy_hit(self, tick: int):
        if not self.is_last_hit(tick):
            return False
        else:
            if self.mission_node.skill.heavy_attack:
                return True
            else:
                return False
