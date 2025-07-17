from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from zsim.define import ENEMY_ATTACK_REPORT
from zsim.models.event_enums import ListenerBroadcastSignal as LBS

if TYPE_CHECKING:
    from zsim.sim_progress.Character.character import Character
    from zsim.sim_progress.data_struct.EnemyAttackEvent import EnemyAttackEventManager
    from zsim.sim_progress.Preload import SkillNode
    from zsim.sim_progress.Preload.PreloadDataClass import PreloadData


class ActionReplaceManager:
    """
    该对象主要用于阻塞、改写APL运行结果。
    由于是非常粗暴的接在APL的对外输出函数上进行拦截、修正，
    所以该对象的使用必须谨慎，以免大幅度影响APL手法的实现。
    """

    def __init__(self, preload_data):
        self.preload_data: "PreloadData" = preload_data
        self.quick_assist_strategy = self.QuickAssistStrategy(self.preload_data)
        self.parry_aid_strategy = self.ParryAidStrategy(self.preload_data)

    def action_replace_factory(
        self, CID: int, action: str, tick: int
    ) -> tuple[bool, str]:
        """该函数主要用于拦截APL的主动动作，使其被其他动作替代，用来模拟各种特殊情况"""
        """如果目前正处于黄光阶段（窗口期），那么此时的所有切人动作都会被无条件换成格挡，哪怕此时快支正处于激活状态"""
        if "耀嘉音" in self.preload_data.sim_instance.init_data.name_box:
            """有耀嘉音时，优先检测快支替换"""
            if self.quick_assist_strategy.condition_judge(
                CID=CID, action=action, tick=tick
            ):
                quick_assist_strategy_replace_result = (
                    self.quick_assist_strategy.spawn_new_action(CID, action)
                )
                if quick_assist_strategy_replace_result not in ["parry", "wait"]:
                    return True, quick_assist_strategy_replace_result

            parry_replace_result = self.parry_aid_strategy.spawn_new_action(
                CID=CID, action=action, tick=tick
            )
            if parry_replace_result != action:
                return True, parry_replace_result
            return False, action

        else:
            """没有耀嘉音时，优先检测招架替换"""
            parry_replace_result = self.parry_aid_strategy.spawn_new_action(
                CID=CID, action=action, tick=tick
            )
            if parry_replace_result != action:
                return True, parry_replace_result

            if self.quick_assist_strategy.condition_judge(
                CID=CID, action=action, tick=tick
            ):
                quick_assist_strategy_replace_result = (
                    self.quick_assist_strategy.spawn_new_action(CID, action)
                )
                return True, quick_assist_strategy_replace_result
            return False, action

    class __BaseStrategy(ABC):
        def __init__(self, preload_data):
            self.preload_data: "PreloadData" = preload_data

        @abstractmethod
        def condition_judge(self, *args, **kwargs):
            pass

        @abstractmethod
        def spawn_new_action(self, *args, **kwargs):
            pass

    class QuickAssistStrategy(__BaseStrategy):
        def __init__(self, preload_data):
            super().__init__(preload_data)
            self.manager_box = {}

        def condition_judge(
            self, CID: int, tick: int, action: str, *args, **kwargs
        ) -> bool:
            """
            该函数用于判定当前tick的动作是否需要被替换成快速支援：条件如下：
            1、当前角色快速支援亮起
            2、当前角色企图从后台切到前台
            """
            if CID is None or action is None:
                raise ValueError("CID或action为空！")
            if self.preload_data.quick_assist_system is None:
                """如果快速支援系统的对象还未建立，那么说明此时
                根本不可能有导致快速支援替换APL动作的情况发生，直接返回False即可。"""
                return False
            if CID not in self.manager_box:
                for manager in self.preload_data.quick_assist_system.quick_assist_manager_group.values():
                    if manager.char.CID == CID:
                        self.manager_box[CID] = manager
                        break
                else:
                    raise ValueError(f"没有找到{CID}角色的快速支援管理器！")
            current_manager = self.manager_box[CID]
            node_on_field = self.preload_data.get_on_field_node(tick - 1)
            """注意，这里传入tick-1的作用：当某些技能不能被合轴与终止时（比如QTE和Q），新动作会被SwapCancelEngine一直拦截，
            此时，就会出现1帧时间场上没有任何动作，这会导致调用该函数的一些判断出错。所以将时间提前了1帧，规避这些错误。"""
            if node_on_field is None:
                # FIXME:这里还是有问题，程序中有时会出现的current_node_on_field 为None的情况，一定会干扰模拟的进行，必须找时间解决掉！

                return False
            """当前角色的快速支援正处于激活状态，并且角色企图上场释放技能，则执行替换。"""
            if (
                current_manager.quick_assist_available
                and str(CID) not in node_on_field.skill_tag
            ):
                return True
            else:
                return False

        def spawn_new_action(self, CID: int, action: str):
            if action == "wait":
                return action
            for _obj in self.preload_data.skills:
                if _obj.CID != CID:
                    continue
                if "parry" in action:
                    do_immediately_info = True
                elif action == "auto_NA":
                    do_immediately_info = False
                else:
                    do_immediately_info = _obj.get_skill_info(
                        skill_tag=action, attr_info="do_immediately"
                    )

                if do_immediately_info:
                    return action
                else:
                    manager = self.manager_box[CID]
                    # print(f'执行快速支援！技能{action}替换成了{manager.quick_assist_skill}！')
                    return manager.quick_assist_skill
            else:
                raise ValueError(
                    f"没有找到CID为{CID}的技能对象！无法执行快速支援替换！"
                )

    class ParryAidStrategy(__BaseStrategy):
        """负责将技能tag替换成各类招架支援的结构"""

        def __init__(self, preload_data):
            super().__init__(preload_data)
            self.consecutive_parry_mode: bool = False  # 连续招架模式
            self.consecutive_parry_node: "SkillNode | None" = None  # 连续招架的技能节点
            self.parry_interaction_in_progress: bool = False  # 当前轮次招架交互正在进行
            self.parry_tag: str | None = None  # 当前轮次招架交互的招架技能标签。
            from zsim.define import PARRY_BASE_PARAMETERS

            self.chain_parry_tick = PARRY_BASE_PARAMETERS[
                "ChainParryActionTimeCost"
            ]  # 系统默认的连续招架时间消耗
            self._knock_back_signal = False  # 击退信号，在末次招架结算时，会由外部数据结构操作接口函数打开，并且在抛出击退信号后置为False
            self.final_parry_node: "SkillNode | None" = None

            """每次招架后，角色都会获得一次突击支援的机会，但是衔接突击支援的时间是有要求的，必须在突击支援失效之前进行（角色击退时间）"""
            self.assault_aid_disable_tick: int = 0
            self.assault_aid_enable: bool = False

        @property
        def knock_back_signal(self) -> bool:
            return self._knock_back_signal

        @knock_back_signal.setter
        def knock_back_signal(self, value: bool):
            print(f"【ActionReplaceManager】knock_back_signal被重新赋值为{value}")
            self._knock_back_signal = value

        def condition_judge(
            self, CID: int, tick: int, action: str, *args, **kwargs
        ) -> bool | str:
            """
            用来判断当前情景下，APL抛出的技能tag是否需要被强制替换为对应的招架类Tag。
            """
            if self.knock_back_signal:
                return "knock_back"
            atk_manager = self.preload_data.atk_manager
            char_on_field_cid = self.preload_data.operating_now
            if not atk_manager.attacking and not self.knock_back_signal:
                return False
            # 对于命中次数为0的进攻事件，应该将其送入【首次招架分支】：
            if atk_manager.hitted_count == 0:
                # 审查招架角色是否拥有招架的能力，是否满足招架的基本条件，同时时间窗口又是否允许？
                if self.__first_parry_condition_judge(
                    atk_manager=atk_manager,
                    CID=CID,
                    tick=tick,
                    action=action,
                    char_on_field_cid=char_on_field_cid,
                ):
                    return "first_parry"
            else:
                # 命中次数不为0的情况，主要分为两种：【连续招架】以及【单次招架的后续】。
                if self.consecutive_parry_mode:
                    # 若连续招架的开关打开，那么无需任何函数判定，都放行并且返回【连续招架】的更新信号
                    if atk_manager.hitted_count == atk_manager.action.hit - 1:
                        return "final_parry"
                    else:
                        return "consecutive_parry"
                # else:
                #     # 若连续招架开关关闭，那么则是【单次招架后续】分支，这里需要考虑是否要抛出“KnockBack”技能，模拟角色被击退。
                #     if self.knock_back_signal:
                #         return "knock_back"
            return False

        def __first_parry_condition_judge(
            self,
            atk_manager: "EnemyAttackEventManager",
            CID: int,
            tick: int,
            action: str,
            char_on_field_cid: int,
        ) -> bool:
            """
            判断当前情况是否满足第一次招架。条件有：
            0、当前有激活的进攻事件并且结算次数为0（已前置）
            1、有角色正尝试切换到前台
            2、该角色拥有招架能力
            3、时间窗口合法
            """
            # 条件1检查——角色尝试切换到前台
            if char_on_field_cid is not None:
                if char_on_field_cid == CID:
                    return False

            # 条件2检查——角色有招架能力
            char_obj: "Character" = (
                self.preload_data.sim_instance.char_data.find_char_obj(CID=CID)
            )
            if char_obj.aid_type != "招架":
                if "parry" in action.lower():
                    raise ValueError(
                        f"APL尝试让 {char_obj.NAME} 进行招架操作，但是该角色没有招架能力！"
                    )
                return False

            # 条件3检查——时间窗口合法
            if not atk_manager.is_in_response_window(tick=tick):
                return False
            else:
                return True

        def spawn_new_action(self, CID: int, action: str, tick: int, *args, **kwargs):
            """根据当前的状态，执行招架支援tag的替换。"""
            atk_manager = self.preload_data.atk_manager
            replace_signal: bool | str = self.condition_judge(
                CID=CID, action=action, tick=tick
            )
            # 若条件判断返回的是False，则说明不执行替换，返回原始tag。
            if not replace_signal:
                return action
            if replace_signal == "first_parry":
                return self.__first_parry_replace_handler(
                    atk_manager=atk_manager, CID=CID, action=action, tick=tick
                )
            elif replace_signal == "consecutive_parry":
                return self.__consecutive_parry_replace_handler(
                    atk_manager=atk_manager, CID=CID, action=action, tick=tick
                )
            elif replace_signal == "knock_back":
                return self.__knock_back_replace_handler(CID=CID)
            elif replace_signal == "final_parry":
                return self.__final_parry_replace_handler(
                    atk_manager=atk_manager, CID=CID
                )
            else:
                raise ValueError(f"无法识别的替换信号：{replace_signal}！")

        def spawn_parry_aid_tag(self, CID: int, mode: int):
            if mode == 0:
                return f"{CID}_Light_parry_Aid"
            elif mode == 1:
                return f"{self.consecutive_parry_node.skill_tag.strip().split('_')[0]}_Chain_parry_Aid"
            elif mode == 2:
                return f"{self.consecutive_parry_node.skill_tag.strip().split('_')[0]}_Heavy_parry_Aid"
            elif mode == 3:
                """这是衔接在招架支援后的后退动作，无法取消。"""
                return f"{self.final_parry_node.skill_tag.strip().split('_')[0]}_knock_back_cause_parry"
            else:
                raise ValueError(f"不支持的招架模式：{mode}！")

        def __first_parry_replace_handler(
            self,
            atk_manager: "EnemyAttackEventManager",
            CID: int,
            action: str,
            tick: int,
        ):
            """负责处理“首次招架”分支的tag替换业务"""
            # 注意，执行本函数的情况，正常情况下总是符合时间窗口的(APL和前方的信号函数都已经处理过这个逻辑了
            if not atk_manager.is_in_response_window(tick=tick):
                raise ValueError(
                    "首次招架的技能标签替换失败，因为当前时间窗口已经过期！"
                )
            if atk_manager.action.hit_type in ["Light", "Chain"]:
                return self.spawn_parry_aid_tag(CID=CID, mode=0)
            elif atk_manager.action.hit_type == "Heavy":
                return self.spawn_parry_aid_tag(CID=CID, mode=2)
            else:
                raise ValueError(
                    f"不支持的招架技能类型：{atk_manager.action.hit_type}！"
                )

        def __consecutive_parry_replace_handler(
            self,
            atk_manager: "EnemyAttackEventManager",
            CID: int,
            action: str,
            tick: int,
        ):
            """
            负责处理“连续招架”分支的tag替换业务
            当处于连续招架的情况下，应该在窗口合法时，第一时间抛出连续招架，
            若时间窗口尚未到来，则抛出wait，
            """

            settled_tick = tick + self.chain_parry_tick
            if atk_manager.hit_check(settled_tick):
                return self.spawn_parry_aid_tag(CID=CID, mode=1)
            else:
                return "wait"

        def __knock_back_replace_handler(self, CID: int):
            """
            负责处理“KnockBack”分支的tag替换业务
            该分支的职能是：准确识别“击退信号”并且抛出“击退”动作。
            首先，在检测到被击退信号之前，应当保持输出wait，
            而在识别到被击退信号之后，输出knock_back
            """
            if self.knock_back_signal:
                return self.spawn_parry_aid_tag(CID=CID, mode=3)
            else:
                raise ValueError("并未检测到击退信号！请检查函数逻辑！")

        def __final_parry_replace_handler(
            self, CID: int, atk_manager: "EnemyAttackEventManager"
        ):
            """
            负责处理“final_parry”分支的tag替换业务
            该分支的职能是：复核验证最后一击的判定结果，
            同时根据本次进攻信号的数量，抛出对应的tag
            """
            if atk_manager.hitted_count > atk_manager.action.hit - 1:
                raise ValueError(
                    "当前已结算次数与进攻信号的命中次数不匹配！这种情况理应不该送入“final_parry”分支，请检查函数逻辑。"
                )
            if atk_manager.action.hit < 3:
                return self.spawn_parry_aid_tag(CID=0, mode=1)
            else:
                return self.spawn_parry_aid_tag(CID=CID, mode=2)

        def update_myself(self, skill_node: "SkillNode", tick: int):
            """开放给外部的更新窗口"""
            if skill_node.skill.trigger_buff_level not in [7, 8, 9]:
                if "knock_back" not in skill_node.skill_tag:
                    return
            if "Light_parry" in skill_node.skill_tag:
                self.parry_interaction_in_progress = True
                if ENEMY_ATTACK_REPORT:
                    self.preload_data.sim_instance.schedule_data.change_process_state()
                    print(
                        f"检测到来自于{skill_node.char_name}的招架技能{skill_node.skill_tag}！招架交互开始！"
                    )
                if self.preload_data.atk_manager.action.hit > 1:
                    self.consecutive_parry_mode = True
                    self.consecutive_parry_node = skill_node
                    print("当前进攻事件是多次命中的，所以开启连续招架模式！")
            elif "knock_back" in skill_node.skill_tag:
                if ENEMY_ATTACK_REPORT:
                    self.preload_data.sim_instance.schedule_data.change_process_state()
                    print(f"角色 {skill_node.char_name} 因招架而被击退！")
                self.knock_back_signal = False
                self.final_parry_node = None
                self.parry_interaction_in_progress = False
                self.assault_aid_enable = True
                self.assault_aid_disable_tick = tick + 60
                listener_manager = self.preload_data.sim_instance.listener_manager
                listener_manager.broadcast_event(event=skill_node, signal=LBS.PARRY)
            elif "Assault_Aid" in skill_node.skill_tag:
                if tick > self.assault_aid_disable_tick:
                    raise ValueError(
                        f"{skill_node.char_name} 企图释放支援突击，但支援突击早就在{self.assault_aid_disable_tick}tick失效！请检查函数逻辑！"
                    )
                self.assault_aid_enable = False
                self.assault_aid_disable_tick = tick
                if ENEMY_ATTACK_REPORT:
                    self.preload_data.sim_instance.schedule_data.change_process_state()
                    print(f"角色 {skill_node.char_name} 在招架完成后释放支援突击！")
            elif any(
                [
                    _sub_tag in skill_node.skill_tag
                    for _sub_tag in ["Chain_parry", "Heavy_parry"]
                ]
            ):
                # 在检测连续招架或是重招架时，必须检测当前的命中次数，确保正确关闭连续招架状态。
                if (
                    self.preload_data.atk_manager.hitted_count
                    == self.preload_data.atk_manager.action.hit
                ):
                    self.consecutive_parry_mode = False
