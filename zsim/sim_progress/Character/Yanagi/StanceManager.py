from zsim.sim_progress.Buff import find_tick
from zsim.sim_progress.Preload import SkillNode


class Shinrabanshou:
    def __init__(self, cinema: int, char_instance):
        self.max_duration = 900 if cinema < 6 else 1800
        self.update_tick = 0
        self.char = char_instance

    def statement(self, tick: int):
        """查询 柳的森罗万象状态的方法"""
        if self.update_tick == 0:
            return False
        if tick - self.update_tick >= self.max_duration:
            return False
        return True

    @property
    def active(self):
        """更新森罗万象的时间！"""

        tick = find_tick(sim_instance=self.char.sim_instance)
        return tick < self.update_tick + self.max_duration


class StanceManager:
    """柳的架势管理器"""

    def __init__(self, char_instance):
        self.char = char_instance
        self.stance_jougen = True  # 上弦状态，初始化时就是上弦
        self.stance_kagen = False  # 下弦状态
        self.last_update_node = None  # 上次导致架势管理器的数据发生更新的skill_node
        self.shinrabanshou = Shinrabanshou(self.char.cinema, self.char)  # 森罗万象管理器
        self.ex_chain = False  # 突刺连段状态，也可以理解为'是否正在释放强化E'
        self.stance_changing_buff_index = "Buff-角色-柳-额外能力-积蓄效率"

    def update_myself(self, skill_node: SkillNode):
        """接收skill_node，并且判断自身架势是否要改变；"""
        skill_tag = skill_node.skill_tag

        """首先筛掉不是自己的skill_node"""
        if "1221" not in skill_tag:
            return

        """若传入的skill_node不能触发任何架势直接返回！"""
        if skill_tag not in [
            "1221_E",
            "1221_E_A",
            "1221_QTE",
            "1221_Assault_Aid",
            "1221_E_EX_1",
            "1221_E_EX_2",
        ]:
            return

        """若检测到强化E 突刺攻击，则需要分类讨论"""
        if skill_tag == "1221_E_EX_1":
            if (
                self.last_update_node is not None
                and self.last_update_node.skill_tag == "1221_E_EX_1"
            ):
                """当检测到上一个使架势管理器发生更新的技能是穿刺攻击时，直接返回"""
                if not self.ex_chain:
                    raise ValueError(
                        "检测到中间段强化E的突刺攻击时，架势管理器的ex_chain未处于打开状态！"
                    )
                return
            else:
                """其余情况，穿刺攻击的上一个技能都不会是穿刺攻击，所以可以放行。改变架势 + 启动森罗万象"""
                if self.ex_chain:
                    # raise ValueError(f'检测到首段强化E的突刺攻击时，架势管理器的ex_chain正处于打开状态！')
                    print("检测到首段强化E的突刺攻击时，架势管理器的ex_chain正处于打开状态！")
                self.ex_chain = True
                # print(f'强化E连段开始')
                tick = find_tick(sim_instance=self.char.sim_instance)
                self.shinrabanshou.update_tick = tick
                self.last_update_node = skill_node
                self.change_stance()

        elif skill_tag == "1221_E_EX_2":
            """检测到强化E的下落攻击分支"""
            if not self.ex_chain:
                raise ValueError(
                    "检测到强化E下落攻击传入，但是架势管理器的ex_chain未处于打开状态！"
                )
            self.ex_chain = False
            self.last_update_node = skill_node
            # print(f'强化E连段结束')
        else:
            """其余情况全部都执行一次架势切换"""
            self.change_stance()
            self.last_update_node = skill_node

    def change_stance(self):
        """更新架势"""
        if self.stance_jougen == self.stance_kagen:
            raise ValueError("上弦、下弦状态不能同时为True或False！")
        if self.stance_jougen:
            self.stance_jougen = False
            self.stance_kagen = True
        else:
            self.stance_jougen = True
            self.stance_kagen = False
        from zsim.sim_progress.Buff.BuffAddStrategy import buff_add_strategy

        buff_add_strategy(self.stance_changing_buff_index, sim_instance=self.char.sim_instance)

    @property
    def stance_now(self):
        """返回当前的架势状态，True是上弦，False是下弦"""
        if self.stance_jougen:
            return True
        elif self.stance_kagen:
            return False
        else:
            raise ValueError("上弦、下弦状态不能同时为True或False！")
