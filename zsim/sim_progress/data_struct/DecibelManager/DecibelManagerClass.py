from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator


class Decibelmanager:
    def __init__(self, sim_instance: "Simulator"):
        # 原类属性改为实例属性
        self.sim_instance = sim_instance
        self.DECIBEL_EVENT_MAP = {
            "interrupt_enemy": [10],
            4: [20],
            "part_break": [20],
            "stun": [20],
            "anomaly": [35, 125, 170],
            "disorder": [15, 65, 85],
            5: [10],
            8: [200],
            "BH_Aid": [20],
            "BH_Aid_after_attacked": [30],
        }
        self.REPORT_MAP = {
            "interrupt_enemy": "打断敌人进攻",
            4: "极限闪避",
            "part_break": "部位破坏",
            "stun": "使敌人失衡",
            "anomaly": "使敌人触发属性异常",
            "disorder": "使敌人触发紊乱",
            5: "释放连携技",
            8: "释放招架支援",
            "BH_Aid": "支援角色触发的快速支援",
            "BH_Aid_after_attacked": "受击后触发的快速支援",
        }
        self.char_obj_list: list[object] = []
        self.enemy = None
        self.game_state = None

    def update(self, **kwargs):
        decibel_value, node, output_key = self.get_decibel_value(kwargs)
        if decibel_value == 0:
            return
        char_dict = self.split_char_list_by_cid(node)
        for char_kind, char_list in char_dict.items():
            if char_kind == "major":
                value_input = decibel_value * 1
                self.add_decibel_to_char(value_input, char_list[0], output_key)
            elif char_kind == "minor":
                value_input = decibel_value * 0.5
                for minor_char_name in char_list:
                    self.add_decibel_to_char(value_input, minor_char_name, output_key)
            else:
                raise ValueError(f"{char_kind}不是major或minor！")

    def add_decibel_to_char(self, decibel_value, char_name, output_key):
        from zsim.sim_progress.data_struct import ScheduleRefreshData

        refresh_data = ScheduleRefreshData(
            decibel_target=(char_name,), decibel_value=decibel_value
        )
        self.game_state["schedule_data"].event_list.append(refresh_data)
        # print(f"{char_name}因{self.REPORT_MAP[output_key]}获得了{decibel_value}点喧响值！")

    def get_decibel_value(self, kwargs):
        """根据程序的输入进行参数的初始化检查！并且返回本次运行所需要增加的喧响值"""
        if self.game_state is None:
            self.game_state = self.sim_instance.game_state
        key = kwargs.get("key", None)
        skill_node = kwargs.get("skill_node", None)
        single_hit = kwargs.get("single_hit", None)
        loading_mission = kwargs.get("loading_mission", None)
        if not any([skill_node, single_hit, loading_mission]):
            raise ValueError(
                "DecibelManager的update函数中，必须传入skill_node、single_hit、loading_mission中的一个！"
            )
        if skill_node:
            node = skill_node
        elif single_hit:
            node = single_hit.skill_node
        elif loading_mission:
            node = loading_mission.mission_node
        if key is None:
            if node.skill.trigger_buff_level not in self.DECIBEL_EVENT_MAP:
                decibel_value = 0
                output_key = 0
            else:
                if node.active_generation:
                    # EXPLAIN: 这里要筛选重攻击标签——因为像雅这种角色的连携技分3段，如果不筛选主动动作，那么雅就会多次吃到连携技的喧响值奖励
                    #  风险：暂未发现该筛选存在Bug风险。
                    decibel_value = self.DECIBEL_EVENT_MAP[
                        node.skill.trigger_buff_level
                    ][0]
                    output_key = node.skill.trigger_buff_level
                else:
                    decibel_value = 0
                    output_key = 0
        else:
            if key not in self.DECIBEL_EVENT_MAP:
                decibel_value = 0
                output_key = 0
            else:
                if key in ["anomaly", "disorder"]:
                    if self.enemy is None:
                        self.enemy = self.game_state["schedule_data"].enemy
                    decibel_value = self.DECIBEL_EVENT_MAP[key][
                        self.enemy.QTE_triggerable_times - 1
                    ]
                else:
                    decibel_value = self.DECIBEL_EVENT_MAP[key][0]
                output_key = key
        return decibel_value, node, output_key

    def split_char_list_by_cid(self, node):
        char_id = int(node.skill_tag.strip().split("_")[0])
        char_dict = {"major": [], "minor": []}
        if not self.char_obj_list:
            from zsim.sim_progress.Buff import find_char_list

            self.char_obj_list = find_char_list(sim_instance=self.sim_instance)
        for obj in self.char_obj_list:
            if obj.CID == char_id:
                char_dict["major"].append(obj.NAME)
            else:
                char_dict["minor"].append(obj.NAME)
        if len(char_dict["major"]) == 0:
            raise ValueError(f"并未找到CID为{char_id}的角色！")
        elif len(char_dict["major"]) > 1:
            raise ValueError(f"找到多个CID为{char_id}的角色！")
        else:
            return char_dict


# 模块加载时创建唯一实例
# decibel_manager_instance = Decibelmanager()
