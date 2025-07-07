from zsim.define import HUGO_REPORT
from zsim.sim_progress.Enemy import Enemy


class StunForcedTerminationEvent:
    """
    强制结束失衡事件，该事件会强制结束怪物当前的失衡状态，并且返还一定比例的失衡值
    目前只服务于雨果的决算机制。
    """

    def __init__(
        self,
        enemy: Enemy,
        stun_feed_back_ratio: float,
        execute_tick: int,
        event_source: str = "雨果",
    ):
        self.enemy = enemy
        self.feed_back_ratio = stun_feed_back_ratio
        self.execute_tick = execute_tick  # 执行时间
        self.schedule_priority = 999
        self.source = event_source

    def execute_myself(self):
        """执行事件"""
        if not self.enemy.dynamic.stun:
            raise ValueError(
                f"执行强制结束失衡状态事件时，怪物{self.enemy.name}未处于失衡状态"
            )
        self.enemy.restore_stun()
        self.enemy.dynamic.stun_bar += self.enemy.max_stun * self.feed_back_ratio
        print(
            f"失衡状态重置已经执行！成功返还{self.feed_back_ratio * 100}%的失衡值！"
        ) if HUGO_REPORT else None
