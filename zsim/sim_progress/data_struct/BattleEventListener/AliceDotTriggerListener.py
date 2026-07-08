from typing import TYPE_CHECKING

from zsim.define import ALICE_REPORT
from zsim.models.event_enums import ListenerBroadcastSignal as LBS
from zsim.sim_progress.anomaly_bar.CopyAnomalyForOutput import NewAnomaly

from ..schedule_dispatch import ScheduledEventEmitter, ScheduledEventEmitterProvider
from .BaseListenerClass import BaseListener

if TYPE_CHECKING:
    from zsim.sim_progress.Character.Alice import Alice
    from zsim.sim_progress.Character.character import Character
    from zsim.simulator.simulator_class import Simulator


class AliceDotTriggerListener(BaseListener):
    """这个监听器的作用是监听畏缩的激活与刷新"""

    def __init__(
        self,
        listener_id: str | None = None,
        sim_instance: "Simulator | None" = None,
        scheduled_event_emitter_provider: ScheduledEventEmitterProvider | None = None,
    ):
        super().__init__(listener_id, sim_instance=sim_instance)
        self.char: "Character | None | Alice" = None
        self._scheduled_event_emitter_provider = (
            scheduled_event_emitter_provider
            or ScheduledEventEmitterProvider.from_sim_instance_getter(lambda: self.sim_instance)
        )

    def _scheduled_event_emitter(self) -> ScheduledEventEmitter:
        return self._scheduled_event_emitter_provider.create_emitter()

    def listening_event(self, event, signal: LBS, **kwargs):
        """监听到紊乱信号时，激活"""
        if self.char is None:
            char_obj = self.sim_instance.char_data.find_char_obj(CID=1401)
            self.char = char_obj
        if signal not in [LBS.ASSAULT_STATE_ON]:
            return
        self.listener_active()

    def listener_active(self, **kwargs):
        """核心被动激活，给敌人添加Dot"""
        enemy = self.sim_instance.schedule_data.enemy
        # 验证
        if not enemy.dynamic.assault:
            raise ValueError(
                "【爱丽丝核心被动Dot监听器警告】敌人当前的状态不符合核心被动激活条件，请检查！"
            )

        from copy import deepcopy

        from zsim.sim_progress.Update.UpdateAnomaly import spawn_normal_dot

        """
        解释：deepcopy的对象为何来自enemy.anomaly_bars_dict而非enemy.dynamic.active_anomaly_bar_dicts？
        监听器的激活时间点位于enemy.dynamic.assault被赋值为True的时间点，
        该时间点比enemy.dynamic.active_anomaly_bar_dicts的更新更早，所以此时从enemy.dynamic.active_anomaly_bar_dicts中是获取不到我们想要的异常条的，
        此时刚激活的异常条的最新状态还处于enemy.anomaly_bars_dict中，所以要从这里获取。
        """
        phy_anomaly_bar = deepcopy(enemy.anomaly_bars_dict[0])
        phy_anomaly_bar.anomaly_settled()
        dot = spawn_normal_dot(
            dot_index="AliceCoreSkillAssaultDot",
            sim_instance=self.sim_instance,
            bar=phy_anomaly_bar,
        )
        dot.start(timenow=self.sim_instance.tick)
        from zsim.sim_progress.Dot.BaseDot import Dot

        for dots in enemy.dynamic.dynamic_dot_list:
            assert isinstance(dots, Dot)
            if dots.ft.index == dot.ft.index:
                dots.end(timenow=self.sim_instance.tick)
                enemy.dynamic.dynamic_dot_list.remove(dots)
                break

        dot.anomaly_data = NewAnomaly(dot.anomaly_data, sim_instance=self.sim_instance)
        enemy.dynamic.dynamic_dot_list.append(dot)
        self._scheduled_event_emitter().emit_scheduled(dot.anomaly_data)
        if ALICE_REPORT:
            self.sim_instance.schedule_data.change_process_state()
            print("【爱丽丝事件】检测到畏缩状态更新，核心被动Dot激活！")
