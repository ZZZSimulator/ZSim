from .special_state_class import EnemySpecialState
from zsim.define import ElementType, YUZUHA_REPORT, ELEMENT_TYPE_MAPPING as ETM
from zsim.models.event_enums import SpecialStateUpdateSignal as SSUS
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zsim.sim_progress.Enemy import Enemy
    from .special_state_manager_class import SpecialStateManager
    from zsim.sim_progress.Preload import SkillNode
    from zsim.sim_progress.data_struct import SingleHit


class SweetScare(EnemySpecialState):
    """柚叶的甜蜜惊吓特殊状态"""

    def __init__(self, enemy_instance: "Enemy", manager_instance: "SpecialStateManager"):
        super().__init__(enemy_instance=enemy_instance, manager_instance=manager_instance)
        self.flavor_match_element: ElementType | None = None  # 染色种类
        self.leagle_skill_tag: list[str] = ["1411_SNA_A", "1411_SNA_B"]
        self.active_origin_skill_tag: list[str] = ["1411_E_EX_A", "1411_E_EX_B", "1411_Q"]
        self.max_duration: int = 2400  # 持续时间
        self.description = "甜蜜惊吓"
        self.sim_instance = self.enemy.sim_instance
        self.sugarburst_sparkless_max_trigger_origin_skill_tag: list[str] = [
            "1411_Assault_Aid_A",
            "1411_CoAttack_A",
        ]
        self.sugarburst_sparkless_max: str = "1411_SNA_B"
        self.sugarburst_sparkless: str = "1411_SNA_A"
        self.sugarburst_sparkless_update_tick: int = 0  # 彩糖花火上次更新的时间
        self.sugarburst_sparkless_cd: int = 60  # 彩糖花火CD

    @property
    def flavor_match(self) -> bool:
        """【十人十色】状态（是否被染色）"""
        if self.active and self.flavor_match_element is not None:
            return True
        else:
            return False

    def start(self):
        """甜蜜惊吓的启动逻辑"""
        self.active = True
        self.last_update_tick = self.enemy.sim_instance.tick
        self.flavor_match_element = None
        if YUZUHA_REPORT:
            sim_instance = self.enemy.sim_instance
            sim_instance.schedule_data.change_process_state()
            print(
                f"【甜蜜惊吓】状态激活！本次状态预计于{sim_instance.tick + self.max_duration}tick结束"
            )

    @property
    def sugarburst_sparkless_ready(self):
        if self.sugarburst_sparkless_update_tick == 0:
            return True
        if (
            self.sim_instance.tick - self.sugarburst_sparkless_update_tick
            >= self.sugarburst_sparkless_cd
        ):
            return True
        return False

    def end(self):
        """甜蜜惊吓的结束逻辑"""
        self.active = False
        self.flavor_match_element = None

    def update(self, update_signal: SSUS, **kwargs):
        """甜蜜惊吓的自更新函数，该函数需要在两个被广播式地调用，所以需要传入更新信号"""
        if update_signal == SSUS.RECEIVE_HIT:
            self.__update_when_receive_hit(**kwargs)
        elif update_signal == SSUS.BEFORE_PRELOAD:
            self.__update_when_after_preload()
        elif update_signal == SSUS.CHARACTER:
            self.__update_when_in_character(**kwargs)
        else:
            self.enemy.sim_instance.schedule_data.change_process_state()
            print(
                f"【特殊状态：甜蜜惊吓 警告】接收到了与自己分组无关的信号{update_signal.value}，请检查逻辑以及数据库填写"
            )
            return

    def try_change_attribute(self, skill_node: "SkillNode"):
        """外部调用接口，尝试进行染色"""
        if not self.flavor_match:
            return
        if skill_node.skill_tag in self.leagle_skill_tag:
            self.attribute_changing(skill_node)

    def attribute_changing(self, skill_node: "SkillNode"):
        """染色的业务逻辑"""
        if skill_node.skill_tag not in self.leagle_skill_tag:
            self.enemy.sim_instance.schedule_data.change_process_state()
            print(
                f"【特殊状态：甜蜜惊吓 警告】自检函数放行了一个不能被染色的技能：{skill_node.skill_tag}"
            )
            return

        skill_node.effective_anomaly_buildup = False  # 将其改为无效积蓄
        skill_node.element_type_change = self.flavor_match_element  # 染色
        # if YUZUHA_REPORT:
        #     self.enemy.sim_instance.schedule_data.change_process_state()
        #     print(f"【甜蜜惊吓染色】技能{skill_node.skill_tag}被染色为{ETM.get(skill_node.element_type)}属性")

    def flavor_match_update(self, skill_node: "SkillNode"):
        """【甜蜜惊吓】状态正式被染色"""
        self.flavor_match_element = skill_node.element_type
        if YUZUHA_REPORT:
            self.enemy.sim_instance.schedule_data.change_process_state()
            print(
                f"【甜蜜惊吓】状态被技能{skill_node.skill_tag}染为 {ETM.get(skill_node.element_type)} 属性！这将在接下来的2400tick内改变所有【彩糖花火】的属性！"
            )

    def __update_when_receive_hit(self, **kwargs):
        """在受到攻击时执行，主要负责：彩糖花火·极、甜蜜惊吓状态的开启、染色状态的开启"""
        single_hit: "SingleHit" = kwargs.get("single_hit")
        if single_hit is None:
            self.enemy.sim_instance.schedule_data.change_process_state()
            print(f"【特殊状态：甜蜜惊吓 警告】在receive_hit的节点没有接收到预期中的SingleHit")
            return
        """首先要检查的是彩糖花火·极的触发"""
        if single_hit.skill_tag in self.sugarburst_sparkless_max_trigger_origin_skill_tag:
            if single_hit.heavy_hit:
                from zsim.sim_progress.data_struct import schedule_preload_event_factory

                skill_tag_list = [self.sugarburst_sparkless_max]
                preload_tick_list = [self.sim_instance.tick]
                schedule_preload_event_factory(
                    skill_tag_list=skill_tag_list,
                    preload_tick_list=preload_tick_list,
                    preload_data=self.sim_instance.preload.preload_data,
                    apl_priority_list=[-1],
                    sim_instance=self.sim_instance,
                )
                if YUZUHA_REPORT:
                    self.sim_instance.schedule_data.change_process_state()
                    print(
                        f"【甜蜜惊吓触发】由 {single_hit.skill_node.skill.skill_text} 触发了一次【彩糖花火·极】"
                    )

        """若single_hit是那几个会刷新甜蜜惊吓状态的技能，那么优先执行重启判定"""
        if single_hit.skill_tag in self.active_origin_skill_tag:
            if single_hit.heavy_hit:
                if self.active:
                    self.end()
                self.start()
                return

        """剩下的所有hit情况，才会进入染色判定逻辑"""
        if self.active:
            if not self.flavor_match:
                if (
                    int(single_hit.skill_tag.strip().split("_")[0])
                    == self.sim_instance.preload.preload_data.operating_now
                ):
                    if single_hit.skill_node is None:
                        self.sim_instance.schedule_data.change_process_state()
                        print(
                            f"【特殊状态：甜蜜惊吓警告】在试图更新染色状态时，检测到SingleHit并未关联SkillNode！染色失败！"
                        )
                        return
                    self.flavor_match_update(skill_node=single_hit.skill_node)

    def __update_when_after_preload(self, **kwargs):
        """在Preload的最开始阶段执行，主要负责彩糖花火的触发"""
        if self.active:
            if self.sim_instance.tick - self.last_update_tick >= self.max_duration:
                self.end()
                return
            if self.sugarburst_sparkless_ready:
                from zsim.sim_progress.data_struct import schedule_preload_event_factory

                skill_tag_list = [self.sugarburst_sparkless]
                preload_tick_list = [self.sim_instance.tick]
                schedule_preload_event_factory(
                    skill_tag_list=skill_tag_list,
                    preload_tick_list=preload_tick_list,
                    preload_data=self.sim_instance.preload.preload_data,
                    apl_priority_list=[-1],
                    sim_instance=self.sim_instance,
                )
                self.sugarburst_sparkless_update_tick = self.sim_instance.tick

    def __update_when_in_character(self, **kwargs):
        """在Character内部执行，主要负责染色"""
        skill_node = kwargs.get("skill_node")
        self.try_change_attribute(skill_node=skill_node)
