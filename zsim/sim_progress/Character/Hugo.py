from .character import Character


class Hugo(Character):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 虽然雨果自身没有特殊资源，但是需要创建他的专属监听器
        self.listener_creat = False

    def special_resources(self, *args, **kwargs) -> None:
        """雨果的特殊资源模块"""
        if not self.listener_creat:
            self.sim_instance.listener_manager.listener_factory(
                listener_owner=self,
                initiate_signal="Hugo",
                sim_instance=self.sim_instance,
            )
        return

    def get_resources(self) -> tuple[str, float]:
        pass

    def get_special_stats(self, *args, **kwargs) -> dict[str, int | float | bool]:
        pass
