class CoordinatedSupportManager:
    """协战状态管理器"""

    def __init__(self):
        self.coordinated_support = False
        self.update_tick = 0
        self.end_tick = 0
        self.max_duration = 1200
        self.max_count = 10
        self.after_shock_tag = "1361_CoAttack_A"
        self.count = 0
        self.update_count_box = {2: 4, 6: 6}
        self.update_tick_box = {2: 480, 6: 720}

    def update_myself(self, tick: int, skill_node):
        """传入skill_node，更新自身状态，该函数只负责刷新协战状态，不负责层数减少。"""
        tbl = skill_node.skill.trigger_buff_level
        if tbl in [2, 6]:
            self.refresh_myself(tbl, tick)

    def refresh_myself(self, tbl, tick):
        """更新协战状态的函数
            关于协战状态的结束时间（end_tick）的更新逻辑，这个比较复杂。
                    由于协战状态的池子中的剩余时间是可以叠加的，但又存在最大值。
                    如果用最无脑的写法，那应该写一个函数，每个tick更新一次所谓的“剩余时间”，但是这样做实在是太浪费计算资源了。
                    所以这里考虑了一个等效的算法，这个算法会在每次激活协战状态时，无脑更新start_tick和end_tick，
                    其中，end_tick的更新逻辑较为复杂，但是无论是哪一种情况，都可以表达为：
                    min(max(原结束时间 - 当期时间, 0) + 新增加的时间, 当前时间 + 最大持续时间) + 当前时间
                    图形理解：
                    情况1：新增时间∆t并未使Buff时间溢出
                    |---------|---------------|------------------------|-------------|
        情况说明：    tick_now            老end_tick         ∆t                 新end_tick     最大时间

                    情况2：新增时间∆t使得时间溢出
                    |---------|---------------|------------------------|-------------|
        情况说明：    tick_now            老end_tick         ∆t                最大时间        新end_tick

                    情况3：新增发生前，状态早已结束
                    |---------|---------------|------------------------|---------------------------|
        情况说明：   老end_tick            tick_now          ∆t                新end_tick                                  最大时间

                    纵观全部的触发情况，无外乎上面三种。而无论哪一种情况，公式都可以准确算出新end_tick的位置。"""
        self.coordinated_support = True
        self.update_tick = tick

        end_tick_new = (
            min(
                max(self.end_tick - tick, 0) + self.update_tick_box[tbl],
                tick + self.max_duration,
            )
            + tick
        )
        self.end_tick = end_tick_new
        self.count += self.update_count_box[tbl]
        self.count = min(self.count, self.max_count)
        # print(f'协战状态更新！当前层数：{self.count}，结束时间{self.end_tick}， 当前剩余时间：{self.end_tick - tick}')

    def is_active(self, tick: int):
        """检查自身Buff状态是否存在"""
        if self.end_tick > tick:
            if self.count > 0:
                return True
        return False

    def end(self, tick: int):
        """Buff结束"""
        # print(f'协战状态结束了，当前层数：{self.count}，当前剩余时间：{self.end_tick - tick}')
        self.coordinated_support = False
        self.count = 0
        self.update_tick = tick

    def spawn_after_shock(self, tick: int) -> str | None:
        """生成协同攻击的函数"""
        if self.is_active(tick):
            self.count -= 1
            # print(f'协战状态触发了一次协同攻击，剩余层数：{self.count}，当前剩余时间：{self.end_tick - tick}')
            if self.count <= 0:
                self.end(tick)
            return self.after_shock_tag
        return None
