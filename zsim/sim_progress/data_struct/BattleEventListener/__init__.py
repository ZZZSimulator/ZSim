import importlib
from collections import defaultdict
from typing import TYPE_CHECKING
from zsim.models.event_enums import ListenerBroadcastSignal as LBS
from .BaseListenerClass import BaseListener

if TYPE_CHECKING:
    from zsim.sim_progress.Character.character import Character
    from zsim.sim_progress.Enemy import Enemy
    from zsim.simulator.simulator_class import Simulator


class ListenerManger:
    """监听器组"""

    def __init__(self, sim_instance: "Simulator"):
        self.sim_instance = sim_instance
        self._listeners_group: defaultdict[str | int : dict[str, BaseListener]] = (
            defaultdict(dict)
        )
        self.__listener_map: dict[str, str] = {
            "Hugo_1": "HugoCorePassiveBuffListener",
            "Hormone_Punk_1": "HormonePunkListener",
            "Zenshin_Herb_Case_1": "ZanshinHerbCaseListener",
            "Heartstring_Nocturne_1": "HeartstringNocturneListener",
            "Yixuan_1": "YixuanAnomalyListener",
            "CinderCobalt_1": "CinderCobaltListener",
            "Yuzuha_1": "YuzuhaC2QTEListener",
            "Yuzuha_2": "YuzuhaC6ParryListener",
        }

    def add_listener(
        self, listener_owner: "Character | Enemy | None", listener: BaseListener
    ):
        """添加一个监听器"""
        owner_type = type(listener_owner).__bases__[0].__name__
        if owner_type == "Character":
            self._listeners_group[listener_owner.CID][listener.listener_id] = listener
        elif owner_type == "Enemy":
            self._listeners_group["enemy"][listener.listener_id] = listener
        else:
            raise TypeError(f"无法解析的监听器所有者类型: {type(listener_owner)}")

    def remove_listener(self, listener_owner, listener: BaseListener):
        """移除一个监听器"""
        if isinstance(listener_owner, Character):
            listeners_group = self._listeners_group[listener_owner.CID]
        elif isinstance(listener_owner, Enemy):
            listeners_group = self._listeners_group["enemy"]
        else:
            raise TypeError(f"无法解析的监听器所有者类型: {type(listener_owner)}")
        listeners_group.pop(listener.listener_id)

    def broadcast_event(self, event, signal: LBS, **kwargs):
        """广播事件，kwargs参数中记录了事件类型"""
        for owner_id, owner_dict in self._listeners_group.items():
            for __listener in owner_dict.values():
                __listener: BaseListener
                __listener.listening_event(event=event, signal=signal, **kwargs)

    def listener_factory(
        self,
        listener_owner: "Character | Enemy | None",
        initiate_signal: str = None,
        sim_instance: "Simulator" = None,
    ):
        """初始化监听器的工厂函数"""
        if initiate_signal is None:
            raise ValueError(
                "在初始化阶段调用监听器工厂函数时，必须传入有效的initiate_signal参数！"
            )
        if listener_owner is None:
            raise ValueError("调用监听器工厂函数时，listener_onwner参数不能为空！")
        for listener_id, listener_class_name in self.__listener_map.items():
            if initiate_signal in listener_id:
                module_name = listener_class_name
                try:
                    module = importlib.import_module(
                        f".{module_name}", package=__name__
                    )
                    listener_obj = getattr(module, listener_class_name)(
                        listener_id, sim_instance=sim_instance
                    )
                    self.add_listener(
                        listener_owner=listener_owner, listener=listener_obj
                    )
                    return listener_obj
                except ModuleNotFoundError:
                    raise ValueError(
                        "在初始化阶段调用监听器工厂函数时，找不到对应的监听器模块！"
                    )

    def get_listener(
        self, listener_owner: "Character | Enemy | None", listener_id: str
    ) -> BaseListener | None:
        """获取指定监听器"""
        owner_type = type(listener_owner).__bases__[0].__name__
        if owner_type == "Character":
            listener = self._listeners_group[listener_owner.CID].get(listener_id, None)
        elif owner_type == "Enemy":
            listener = self._listeners_group["enemy"].get(listener_id, None)
        else:
            raise TypeError(f"无法解析的监听器所有者类型: {type(listener_owner)}")
        if listener is None:
            raise ValueError(
                f"在获取监听器时，未找到对应的监听器 ID: {listener_id}，所有者: {listener_owner}"
            )
        return listener

    def __str__(self):
        print("==========监听器组的现状如下==========")
        for owner_id, owner_dict in self._listeners_group.items():
            print(f"监听器组子集 ID: {owner_id}")
            print(f"{['监听器' + __key + '  |  ' for __key in owner_dict.keys()]}")
        print("===================================")


#
# # import时，就创建一个单例
# listener_manager_instance = ListenerManger()
