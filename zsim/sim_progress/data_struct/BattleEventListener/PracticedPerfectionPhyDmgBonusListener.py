from typing import TYPE_CHECKING

from zsim.models.event_enums import ListenerBroadcastSignal as LBS

from .BaseListenerClass import BaseListener

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator


class PracticedPerfectionPhyDmgBonusListener(BaseListener):
    """十方锻星的物理增伤监听器，监听入场信号和强击信号"""

    def __init__(self, listener_id: str | None = None, sim_instance: "Simulator | None" = None):
        super().__init__(listener_id, sim_instance=sim_instance)
        self.buff_index: str | None = None  # 音擎增益的Buff index

    def listening_event(self, event, signal: LBS, **kwargs):
        """监听到角色入场事件，传递入场信号。"""
        if signal not in [LBS.ASSAULT_SPAWN, LBS.ENTER_BATTLE]:
            return
        self.listener_active(signal=signal)

    def listener_active(self, **kwargs):
        """监听器激活，根据信号类型进行不同的处理"""
        from zsim.sim_progress.Character.character import Character

        if self.buff_index is None:
            assert self.owner is not None, (
                "【十方锻星物理增伤监听器警告】监听器未绑定角色，请检查初始化"
            )

            assert isinstance(self.owner, Character), (
                "【十方锻星物理增伤监听器警告】监听器绑定的角色不是Character类型，请检查初始化"
            )
            assert self.owner.weapon_ID == "十方锻星", (
                f"【十方锻星物理增伤监听器警告】监听器绑定的武器是{self.owner.weapon_ID}，并非十方锻星，请检查初始化"
            )
            assert int(self.owner.weapon_level) in [
                1,
                2,
                3,
                4,
                5,
            ], (
                f"【十方锻星物理增伤监听器警告】监听器绑定的角色武器精炼等级为{self.owner.weapon_level}，不是合法的精炼等级，请检查初始化"
            )
            self.buff_index = f"Buff-武器-精{int(self.owner.weapon_level)}十方锻星-物理伤害增加"

        assert "signal" in kwargs, "【十方锻星物理增伤监听器警告】监听器激活时，未传入信号类型"
        signal: LBS = kwargs["signal"]
        from zsim.sim_progress.Buff.BuffAddStrategy import buff_add_strategy

        if signal == LBS.ENTER_BATTLE:
            assert isinstance(self.owner, Character), (
                "【十方锻星物理增伤监听器警告】监听器绑定的角色不是Character类型，请检查初始化"
            )
            benifit_list = [self.owner.NAME]
            buff_add_strategy(
                self.buff_index,
                benifit_list=benifit_list,
                specified_count=2,
                sim_instance=self.sim_instance,
            )
            buff_add_strategy(
                self.buff_index, benifit_list=benifit_list, sim_instance=self.sim_instance
            )
