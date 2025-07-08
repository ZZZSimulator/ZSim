from zsim.sim_progress.Preload import SkillNode

from .character import Character
from .utils.filters import _skill_node_filter


class Jane(Character):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.passion_stream: float = 0.0  # 狂热心流，0.0 ~ 100.0
        self.passion_state: bool = False  # 狂热状态
        self.salchow_jump: int = 0  # 萨霍夫跳剩余次数

    def __check_salchow_jump(self) -> None:
        """检查萨霍夫跳次数"""
        max_jumps = 1 if self.cinema == 0 else 2
        if self.salchow_jump > max_jumps:
            self.salchow_jump = max_jumps
        elif self.salchow_jump < 0:
            raise RuntimeError("萨霍夫跳次数不能为负数")

    def __reset_passion(self) -> None:
        """重置狂热"""
        self.passion_stream = 0.0
        self.passion_state = False
        self.__check_salchow_jump()

    def __get_into_passion_state(self) -> None:
        """进入狂热状态"""
        self.passion_stream = 100
        self.passion_state = True
        self.salchow_jump += 1
        self.__check_salchow_jump()

    def __passion_core(
        self, passion_get: float, passion_consume: float, passion_direct_add: float
    ) -> None:
        """狂热计算逻辑核心"""
        self.passion_stream += (
            passion_direct_add  # 直接添加的狂热值，闪反、QTE、大招、萨霍夫跳等
        )
        if not self.passion_state:
            # 非狂热心流状态下，结算狂热获得
            self.passion_stream += passion_get
            if self.passion_stream >= 100 - 1e-6:
                self.__get_into_passion_state()
        else:
            # 狂热心流状态下，结算狂热消耗
            self.passion_stream -= passion_consume
            if self.passion_stream <= 1e-6:
                self.__reset_passion()

    def special_resources(self, *args, **kwargs) -> None:
        """模拟简的狂热心流"""
        # 输入类型检查
        skill_nodes: list[SkillNode] = _skill_node_filter(*args, **kwargs)
        for node in skill_nodes:
            if node.char_name != "简":
                continue
            if node.skill_tag == "1301_SNA_1":
                self.salchow_jump -= 1
                self.__check_salchow_jump()

            labels = node.labels if node.labels is not None else {}
            passion_get = labels.get("passion_get", 0)
            passion_consume = labels.get("passion_consume", 0)
            passion_direct_add = labels.get("passion_direct_add", 0)
            self.__passion_core(passion_get, passion_consume, passion_direct_add)

        # TODO 关于萨霍夫跳的第一段（1301_SNA_1）的拆分问题：
        #  这一段攻击动作是可以提前停止的，
        #  所以我在考虑要不要在数据库中对该动作进行拆分——就像青衣的 NA_3 一样，只记录最小单位。
        #  因为开大抢队、或是即将到来的怪物进攻以及角色交互模块（估计在5月份我就一定会写），一定会涉及到各种动作的提前终止，
        #  虽然就目前的结构来说，提前终止在伤害、积蓄、失衡端都是已经可以满足的（我给Load阶段留了接口，可以调用函数暴力删除某个正在进行的动作），
        #  但是在特殊资源这一块，技能一旦传入就会拿到100%份额的心流恢复，这里和实战中提前打断萨霍夫跳的情况会有一定出入——这会干扰到后续APL对整个循环的递推。
        #  当然，现阶段可以不做这个，让简每次都打完完整的萨霍夫跳
        #  但是，类似于这种可重复的蓄力类动作的拆分，可以说是通用需求。在简这里碰到的问题，在其他角色那里一样会碰到，
        #   ---分割线---
        #   如果要拆的话，显然就要涉及一个判断“1301_SNA_1的首次传入”的需求，
        #   那可以看看char下面的lasting_node，那里的数据结构可以帮助你快速判断这个“首次传入”，就不需要在本地写一堆轮子了。

        # if self.cinema == 6:
        #     pass

    # TODO 六命后强击立刻进入狂热心流——由外部模块控制，调用接口强制启动心流即可，不需要在本函数中留接口。
    def external_passion_change(self):
        """
        外部强制开启心流状态的接口——主要为6画服务，尚未debug！！！这里只是留一个接口。
        至于为何要单写一个函数，因为要调用的是“__”开头的私有方法，直接调用IDE会报错，按照格式调用又不美观，索性单写一个函数
        """
        self.__get_into_passion_state()

    def get_resources(self) -> tuple[str, float]:
        return "狂热心流", self.passion_stream

    def get_special_stats(self, *args, **kwargs) -> dict[str, int | float | bool]:
        """获取简的特殊状态"""
        return {
            "狂热心流": self.passion_stream,
            "狂热状态": self.passion_state,
            "萨霍夫跳剩余次数": self.salchow_jump,
        }
