from zsim.sim_progress.Preload import SkillNode

from .character import Character
from .utils.filters import _skill_node_filter


class Soldier0_Anby(Character):
    """大安比的银星机制"""

    # TODO：把银星的逻辑写在Char里面是偷懒的做法！！！这本应该是一个debuff
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.silver_star: float = 0.0  # 银星
        self.white_thunder_update_tick: int = 0  # 白雷更新时间
        self.continuing_white_thunder_counter: int = 0  # 连续白雷的计数器
        self.white_thunder_answer: bool = False  # 白雷的触发响应器
        self.thunder_smite_answer: bool = False  # 雷殛的触发响应器
        self.continuing_e: bool = True  # E连击的触发响应器
        self.c1_answer: bool = False  # 1画的强化E白雷的触发响应器
        self.c1_counter: int = 0  # 1画的额外白雷结算次数。
        self.c2_counter: int = 0  # 2画的层数计数器
        self.c6_counter: int = 0  # 6画计数器
        self.c6_answer: bool = False  # 6画的触发响应器
        self.silver_star_basic_cost = 33.333333  # 单E的银星基本消耗
        self.max_silver_star: float = 100.1  # 银星上限
        self.silver_star_gain_dict: dict[str:float] = {
            "1381_NA_1": 4.6875,
            "1381_NA_2": 7.53472222,
            "1381_NA_3": 15.12152778,
            "1381_NA_4": 2.34375,
            "1381_NA_5": 18.75,
            "1381_E_B": 11.11,
            "1381_E_EX": 100.1,
            "1381_CA": 50.1,
            "1381_QTE": 21.09375,
            "1381_Q": 100.1,
            "1381_BH_Aid": 6.25,
            "1381_Assault_Aid": 6.25,
        }

    @property
    def full(self):
        if self.silver_star >= self.max_silver_star:
            return True
        else:
            return False

    def special_resources(self, *args, **kwargs) -> None:
        skill_nodes: list[SkillNode] = _skill_node_filter(*args, **kwargs)
        tick = kwargs.get("tick", 0)
        for nodes in skill_nodes:
            _skill_tag = nodes.skill_tag
            # 1、筛去不是本角色的技能
            if "1381" not in _skill_tag:
                continue

            # 2、处理传入的白雷、雷殛、6命
            if _skill_tag == "1381_CoAttack":
                self.__white_thunder_processor(tick)
            elif _skill_tag == "1381_E_Aid":
                self.__thunder_smite_processor()
            elif _skill_tag == "1381_Cinema_6":
                self.__cinema_6_filter()
            # 3、处理消层的E
            elif _skill_tag == "1381_E_A":
                self.__azure_flash_processor()

            # 4、处理其他技能——叠印记
            else:
                self.continuing_e = False
                if _skill_tag == "1381_E_EX" and self.cinema >= 1:
                    self.c1_answer = True
                if _skill_tag == "1381_Q" and self.cinema >= 2:
                    self.c2_counter += 6
                    if self.c2_counter > 6:
                        self.c2_counter = 6
                self.silver_star += self.silver_star_gain_dict.get(nodes.skill_tag, 0.0)
                # print(f'{_skill_tag}使银星层数增长了，当前层数为{self.silver_star:.2f}')
                """最大值检查"""
                if self.silver_star > self.max_silver_star:
                    self.silver_star = self.max_silver_star

    def __azure_flash_processor(self):
        """处理层数逻辑"""
        self.__check_myself()
        if self.full:
            self.continuing_e = True
        """在解锁2画，并且有预存层数的时候，优先使用层数，并且照常激活白雷。"""
        if self.cinema >= 2 and self.c2_counter > 0:
            self.c2_counter -= 1
        else:
            self.silver_star -= self.silver_star_basic_cost
        self.white_thunder_answer = True
        if self.silver_star < 0:
            print("银星扣过头了！")
            self.silver_star = 0

    def __thunder_smite_processor(self):
        """处理雷殛的函数。"""
        if not self.thunder_smite_answer:
            print("非法雷殛！在雷殛响应状态未开启的情况下，触发了雷殛！")
        self.thunder_smite_answer = False

    def __white_thunder_processor(self, tick):
        """针对白雷进行更新，包括来源判断、计数器更新、以及响应器更新。"""
        if not self.white_thunder_answer and not self.c1_answer:
            print(
                "非法白雷！在零号·安比白雷响应状态未开启、1画的强化E状态也未开启 的情况下，触发了白雷！"
            )
        if self.cinema >= 1 and self.c1_answer:
            self.c1_filter()
        else:
            self.c0_filter(tick)
        # 白雷计数器层数更新结束后，对雷殛进行更新。
        self.c6_updater()
        self.__thunder_smite_active()

    def c6_updater(self):
        """
        更新6画逻辑
        从文字描述上看，6画的添加行为应该属于协同攻击「白雷」的后置，但如果利用白雷的follow_up来进行c6的添加，那么就会导致以下问题：
        c6添加的时间点为白雷6 结束时，在这个Tick，白雷6会在Preload阶段的ForceAddEngine中被识别到结束信号，
        此时，ForceAddEngine会尝试读取白雷6的follow up以及对应的force_add_APL，
        由于ForceAddEngine每个Tick只能进行一次ForceAdd添加，这就会导致C6的协同攻击和雷殛相互抢队，谁排在前面，就执行谁。
        所以，在之前的debug中，我总能观察到C6的协同攻击被大幅度延后，以至于C6计数器都出现了问题。
        在后来的更新中，我将C6等价为雷殛的后置技能，从而摆脱了抢队问题。

        经验：同一个技能的多个follow up必须是互斥的，如果存在一个tick通过多个follow up 判定的可能，就要做特殊处理。否则一定会因为抢队出问题。
        """
        if self.cinema == 6:
            self.c6_counter += 1
            if self.c6_counter >= 6:
                self.c6_answer = True
                self.c6_counter = 0

    def c0_filter(self, tick):
        """通用逻辑"""
        self.white_thunder_answer = False
        """给了3帧的时间宽限"""
        if self.white_thunder_update_tick == 0:
            self.continuing_white_thunder_counter += 1
        elif tick - self.white_thunder_update_tick <= 30:
            self.continuing_white_thunder_counter += 1
        else:
            """超时则清空——这个分支就是“连续”的体现。"""
            self.continuing_white_thunder_counter = 1
        self.white_thunder_update_tick = tick

    def c1_filter(self):
        """解锁1画时，检测到c1_answer开启时，无视白雷响应器状态直接更新白雷计数器，计数器到3，把1画的强化响应器关闭。"""
        self.continuing_white_thunder_counter += 1
        self.c1_counter += 1
        if self.c1_counter >= 3:
            self.c1_answer = False
            self.c1_counter = 0

    def __thunder_smite_active(self):
        """在白雷计数器更新后，尝试对雷殛激活状态进行更新。"""
        if self.continuing_white_thunder_counter >= 3:
            if self.thunder_smite_answer:
                print("在未结算上一次雷殛的情况下，再次触发了雷殛！")
            self.thunder_smite_answer = True
            self.continuing_white_thunder_counter = 0

    def __check_myself(self):
        """自检"""
        if self.silver_star < self.silver_star_basic_cost and self.c2_counter == 0:
            print("当前可用的银星层数不够，传入的操作企图触发白雷，请检查APL！")
        if self.white_thunder_answer:
            print(
                "白雷响应状态仍保持开启的情况下，再次企图触发了白雷！ 当前存在未结算的白雷！！"
            )

    def __cinema_6_filter(self):
        if self.cinema != 6:
            raise ValueError("在未激活6画的情况下，触发了6画的追加攻击！")
        if not self.c6_answer:
            print("在6画的追加攻击响应器未开启的情况下，触发了6画的追加攻击！")
        self.c6_answer = False

    def get_resources(self) -> tuple[str | None, int | float | bool | None]:
        return (
            "银星层数",
            self.silver_star / self.silver_star_basic_cost + self.c2_counter,
        )

    def get_special_stats(self, *args, **kwargs) -> dict[str | None, object | None]:
        return {
            "白雷": self.white_thunder_answer,
            "雷殛": self.thunder_smite_answer,
            "6画状态": self.c6_answer,
            "1画状态": self.c1_answer,
            "白雷连击次数": self.continuing_white_thunder_counter,
            "E连击": self.continuing_e,
            "6画_白雷次数": self.c6_counter,
            "1画_白雷次数": self.c1_counter,
            "2画_电鸣": self.c2_counter,
            "满层": self.full,
        }
