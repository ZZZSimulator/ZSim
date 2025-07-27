from zsim.sim_progress.Preload import SkillNode
from zsim.sim_progress.Report import report_to_log

from .character import Character
from .utils.filters import _skill_node_filter


class Lighter(Character):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.morale: int | float = 4000  # 士气初始40 整形为4000
        self.last_tick: int = 0

    def special_resources(self, *args, **kwargs) -> None:
        """
        模拟莱特的士气机制

        判断目前的时间，与上一次激活时做差，并更新士气值
        确保士气值不超过100

        将传入的skill_node消耗的能量转为士气值
        需要消耗士气时对应扣除
        """
        # 输入类型检查
        skill_nodes: list[SkillNode] = _skill_node_filter(*args, **kwargs)
        # 对输入的skill_node进行遍历
        for node in skill_nodes:
            # 累加逻辑
            if self.morale < 10000:
                # 消耗能量及时更新
                sp_consume = node.skill.sp_consume
                if sp_consume > 0:
                    self.morale += sp_consume * 26
                    # print(
                    #     f"检测到队友强化E{node.skill_tag}：当前士气：{self.morale / 100:.2f}"
                    # )

            if "1161" not in node.skill_tag:
                continue
            # 递减逻辑
            if node.skill_tag == "1161_NA_5_SH_EX":
                self.morale -= 1000
                report_to_log(f"[Character] 莱特的士气消耗至 {self.morale / 100:.2f}")
            elif node.skill_tag == "1161_NA_5_CoH_EX":
                self.morale -= 9000
                # print(f'检测到士气消耗动作，当前士气（处理前）：{self.morale}（处理后）：{self.morale / 100:.2f}')
                # TODO：这里需要一个函数来控制“夹断”技能的数据。思路：\n
                #       1、根据当前SkillNode类复制一个出来（__dict__），\n
                #       2、根据资源消耗量算出缩放比例，\n
                #       3、根据缩放比例修改新的复制SkillNode的所有数据。\n
                #       4、传给下一个环节。

                # FIXME: 20241208：
                #  观察到莱特的士气貌似只有首轮具有阈值，次轮开始就失效了
                report_to_log(f"[Character] 莱特的士气消耗至 {self.morale / 100:.2f}")

            if self.morale < 0:
                report_to_log(f"[Character] 莱特的士气消耗至 {self.morale / 100:.2f}, 请检查")
                self.morale = 0

        # 时间每 6 ticks 更新
        assert self.sim_instance is not None
        tick: int = self.sim_instance.tick
        if tick is not None:
            if (minus := tick - self.last_tick) >= 6:
                self.morale += minus // 6 * 29  # 地板除保证整形对齐
                self.last_tick = tick - minus % 6  # 求余以保证余数不计入本次计算
            self.morale = min(self.morale, 10000)

    def get_resources(self) -> tuple[str, float]:
        return "士气", self.morale / 100
