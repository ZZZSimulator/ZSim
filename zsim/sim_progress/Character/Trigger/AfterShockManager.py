from zsim.define import TRIGGER_REPORT

from .TriggerCoordinatedSupportTrigger import CoordinatedSupportManager


class AfterShock:
    """协同攻击基类"""

    def __init__(self, skill_tag: str, cd: int, mode: int = 0):
        self.update_tick = 0
        self.cd = cd
        self.active_result = skill_tag
        if mode == 0:
            self.complex_cd_manager = None
        else:
            self.complex_cd_manager = self.ComplexCDManager()

    def is_ready(self, skill_node, tick: int):
        # TODO：先写一个临时的
        if self.complex_cd_manager is None:
            if self.update_tick == 0:
                return True
            if tick - self.update_tick >= self.cd:
                return True
            return False
        else:
            return self.complex_cd_manager.is_available(skill_node, tick)

    def after_shock_happend(self, tick: int):
        """抛出aftershock的skill_tag，并且更新自身信息"""
        self.update_tick = tick
        return self.active_result

    class ComplexCDManager:
        """这是强化协同攻击的复杂CD管理器"""

        def __init__(self):
            self.cdm_e = BasicCDManager()
            self.cdm_q = BasicCDManager()
            self.cdm_aid = BasicCDManager()
            self.cdm_map = {2: self.cdm_e, 6: self.cdm_q, 9: self.cdm_aid}

        def is_available(self, skill_node, tick: int) -> bool:
            """整个CD管理器的对外接口，用来更新、判断此次触发信号能否成功激发一次协同攻击。"""
            cdm = self.cdm_map.get(skill_node.skill.trigger_buff_level, None)
            if cdm is None:
                raise ValueError("传入的skill_node与complex_cd_manager不匹配")
            __available_result = cdm.update(tick)
            if not __available_result and TRIGGER_REPORT:
                print("==========CD Warnning===========")
                print(
                    f"{skill_node.skill_tag}企图触发扳机的强化协同攻击，但是尚未就绪！"
                )
                print("================================")
            return __available_result


class BasicCDManager:
    def __init__(self):
        self.cd = 1200
        self.max_count = 2
        self.count = 2
        self.start_tick = 0
        self.refresh_tick = 0
        self.active = False

    def refresh_myself(self, tick: int):
        self.count = self.max_count
        self.active = True
        self.start_tick = tick
        self.refresh_tick = tick + self.cd

    def start_myself(self, tick: int):
        self.refresh_myself(tick)
        self.count -= 1

    def update(self, tick: int) -> bool:
        """根据扳机的强化协同攻击的CD管理机制，写的等效逻辑。"""
        if self.count == 2:
            self.start_myself(tick)
            return True
        elif self.count == 1:
            if tick >= self.refresh_tick:
                self.start_myself(tick)
                return True
            else:
                self.count -= 1
                return True
        elif self.count == 0:
            if tick >= self.refresh_tick:
                self.start_myself(tick)
                return True
            else:
                pass
                # print(
                #     "由于层数耗尽且尚未到达刷新时间，扳机并未成功触发本次强化协同！！"
                # )
        return False


class AfterShockManager:
    """协同攻击管理器， 服务于角色——扳机"""

    def __init__(self, char_instance):
        self.char = char_instance
        normal_after_shock_cd = 180 if self.char.cinema < 1 else 120
        self.normal_after_shock = AfterShock(
            "1361_CoAttack_A", normal_after_shock_cd, mode=0
        )
        self.strong_after_shock = AfterShock("1361_CoAttack_1", 300, mode=1)
        self.coordinated_support_manager = CoordinatedSupportManager()

    def spawn_after_shock(self, tick: int, loading_mission) -> str | None:
        """
        根据传入的skill_node抛出对应的协同攻击，并且更新自身数据；
        这个函数接口是为Buff阶段服务的！请不要在Preload以及char的special_resource阶段调用本函数
        """
        if not self.char.is_available(tick):
            return None
        skill_node = loading_mission.mission_node
        """优先判断强协同攻击: 只有重击的最后一跳才能触发！"""
        if (
            tick - 1 < loading_mission.get_last_hit() <= tick
            and skill_node.skill.heavy_attack
        ):
            if skill_node.skill.trigger_buff_level in [2, 6, 9]:
                if self.strong_after_shock.is_ready(skill_node, tick):
                    if self.char.get_resources()[1] >= 5:
                        if self.strong_after_shock.complex_cd_manager.is_available(
                            skill_node, tick
                        ):
                            strong_after_shock_tag = (
                                self.strong_after_shock.after_shock_happend(tick)
                            )
                            self.char.update_purge(strong_after_shock_tag)
                            return strong_after_shock_tag
                else:
                    if TRIGGER_REPORT:
                        print("==========warnning==========")
                        print(
                            f"{skill_node.skill_tag}企图触发扳机的强化协同攻击但是失败"
                        )
                        print("==========warnning==========")
                    # else:
                    #     print(f'决意值为{self.char.get_resources()[1]}，无法触发强化协同攻击！')

        """其次判断协战状态的免费协同"""
        free_after_shock = self.coordinated_support_manager.spawn_after_shock(tick)
        if free_after_shock is not None:
            return free_after_shock

        """最后，判断消耗决意值的普通协同"""
        if skill_node.skill.trigger_buff_level in [0, 1, 3, 4, 7]:
            if self.normal_after_shock.is_ready(skill_node, tick):
                if self.char.get_resources()[1] >= 3:
                    normal_after_shock_tag = (
                        self.normal_after_shock.after_shock_happend(tick)
                    )
                    self.char.update_purge(normal_after_shock_tag)
                    return normal_after_shock_tag
                # else:
                #     print(f'决意值为{self.char.get_resources()[1]}，无法触发普通协同攻击！')

        return None
