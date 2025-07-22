from abc import ABC, abstractmethod
from zsim.models.event_enums import SpecialStateUpdateSignal as SSUS
from zsim.sim_progress.Preload.PreloadEngine import (
    APLEngine,
    AttackResponseEngine,
    ConfirmEngine,
    ForceAddEngine,
    SwapCancelValidateEngine,
)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .PreloadDataClass import PreloadData


class BasePreloadStrategy(ABC):
    """基础策略，无论是什么策略，都会包含 APL、强制添加技能以及最终技能确认三个引擎。"""

    def __init__(self, data, apl_path):
        self.data: "PreloadData" = data
        self.apl_engine = APLEngine(data, apl_path=apl_path, preload_data=self.data)
        self.force_add_engine = ForceAddEngine(data)
        self.confirm_engine = ConfirmEngine(data)
        self.finish_post_init: bool = False         # 是否完成了后置初始化

    @abstractmethod
    def generate_actions(self, *args, **kwargs):
        pass

    @abstractmethod
    def check_myself(self, *args, **kwargs):
        pass

    @abstractmethod
    def reset_myself(self):
        pass


class SwapCancelStrategy(BasePreloadStrategy):
    def __init__(self, data, apl_path: str | None):
        super().__init__(data, apl_path=apl_path)
        self.swap_cancel_engine = SwapCancelValidateEngine(data)
        self.attack_response_engine = AttackResponseEngine(
            data=data, sim_instance=self.data.sim_instance
        )
        self.tick = 0

    def generate_actions(self, enemy, tick: int) -> None:
        """合轴逻辑"""
        # 0、自检
        self.check_myself(enemy, tick)
        self.data.sim_instance.schedule_data.enemy.special_state_manager.broadcast_and_update(signal=SSUS.BEFORE_PRELOAD)

        # 0.5、 EnemyAttack结构运行一次
        self.attack_response_engine.run_myself(tick=tick)

        # 1、APL引擎抛出本tick的主动动作
        apl_skill_node = self.apl_engine.run_myself(tick)
        if apl_skill_node is not None:
            apl_skill_tag = apl_skill_node.skill_tag
            priority = apl_skill_node.apl_priority
        else:
            apl_skill_tag = "wait"
            apl_skill_node = None
            priority = 0
        # print(apl_skill_tag, priority)
        # TODO：新增功能：Enemy进攻模块的反馈接口，即招架后Enemy动作被打断；或是角色动作被Enemy打断的功能；
        # TODO：“破招”事件需通过decibel manager向角色发放对应的喧响值奖励；

        #  2、ForceAdd引擎处理旧有的强制添加逻辑；
        self.force_add_engine.run_myself(tick)
        #  3、SwapCancel引擎 判定当前tick和技能是否能够成功合轴
        self.swap_cancel_engine.run_myself(
            apl_skill_tag, tick, apl_priority=priority, apl_skill_node=apl_skill_node
        )
        if (
            self.swap_cancel_engine.active_signal
            or self.force_add_engine.active_signal
            or self.swap_cancel_engine.external_update_signal
        ):
            #  4、Confirm引擎 清理data.preload_action_list_before_confirm，
            self.confirm_engine.run_myself(
                tick, apl_skill_node=apl_skill_node, apl_skill_tag=apl_skill_tag
            )


    def check_myself(self, enemy, tick, *args, **kwargs):
        """准备工作"""
        if not self.finish_post_init:
            self.post_init_all_object()
            self.finish_post_init = True
        self.data.chek_myself_before_start_preload(enemy, tick)

    def reset_myself(self):
        pass

    def post_init_all_object(self):
        """后置初始化所有数据"""
        from ...simulator.simulator_class import Simulator
        sim_insatnce: Simulator = self.data.sim_instance
        for char_obj in sim_insatnce.char_data.char_obj_list:
            char_obj.POST_INIT_DATA(sim_insatnce=sim_insatnce)


class SequenceStrategy:
    def generate_actions(self):
        # 封装顺序生成逻辑
        pass
