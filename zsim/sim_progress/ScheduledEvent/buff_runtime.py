from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Mapping, Sequence

from zsim.sim_progress.Report import report_to_log

if TYPE_CHECKING:
    from zsim.sim_progress.anomaly_bar import AnomalyBar
    from zsim.sim_progress.Buff import Buff
    from zsim.sim_progress.Buff.BuffLoad import BuffLoadLifecycleCache
    from zsim.sim_progress.Enemy import Enemy
    from zsim.sim_progress.Load import LoadingMission
    from zsim.sim_progress.Preload import SkillNode
    from zsim.simulator.simulator_class import Simulator


class BuffRuntimeState:
    """单次模拟过程内的 Buff runtime 持有者。"""

    def __init__(
        self,
        *,
        template_registry: dict[str, dict[str, "Buff"]],
        pending_queue: dict[str, list["Buff"]],
        active_store: dict[str, list["Buff"]],
        enemy_mirror: list["Buff"],
    ) -> None:
        from zsim.sim_progress.Buff.BuffLoad import BuffLoadLifecycleCache

        self._template_registry = BuffTemplateRegistry(template_registry)
        self._pending_queue = PendingBuffQueue(pending_queue)
        self._load_lifecycle_cache: BuffLoadLifecycleCache = BuffLoadLifecycleCache()
        self._collapse_enemy_debuff_store(
            active_store,
            enemy_mirror,
        )
        self._active_store = ActiveBuffStore(active_store)
        self._enemy_mirror_owner = EnemyDebuffMirror(self._active_store.ensure_beneficiary("enemy"))

    @staticmethod
    def _collapse_enemy_debuff_store(
        active_store: dict[str, list["Buff"]],
        enemy_mirror: list["Buff"],
    ) -> list["Buff"]:
        enemy_active_store = active_store.get("enemy")
        if enemy_active_store is None:
            active_store["enemy"] = enemy_mirror
            return enemy_mirror
        if enemy_active_store is enemy_mirror:
            return enemy_mirror
        if enemy_active_store:
            enemy_mirror[:] = enemy_active_store
        active_store["enemy"] = enemy_mirror
        return enemy_mirror

    def create_facade(self) -> "BuffRuntimeFacade":
        return DefaultBuffRuntimeFacade(runtime_state=self)

    def create_read_port(self) -> "BuffRuntimeReadPort":
        return DefaultBuffRuntimeReadAdapter(runtime_state=self)

    def template_registry_owner(self) -> "BuffTemplateRegistry":
        return self._template_registry

    def pending_queue_owner(self) -> "PendingBuffQueue":
        return self._pending_queue

    def load_lifecycle_cache_owner(self) -> "BuffLoadLifecycleCache":
        return self._load_lifecycle_cache

    def active_store_owner(self) -> "ActiveBuffStore":
        return self._active_store

    def enemy_mirror_owner(self) -> "EnemyDebuffMirror":
        return self._enemy_mirror_owner


class BuffTemplateRegistry:
    """由 runtime 持有的 Buff 模板注册表。"""

    def __init__(self, registry: dict[str, dict[str, "Buff"]]) -> None:
        self._registry = registry

    def for_owner(self, owner: str) -> dict[str, "Buff"]:
        return self._registry[owner]

    def get_registered_buff(self, owner: str, buff_index: str) -> "Buff | None":
        return self._registry.get(owner, {}).get(buff_index)

    def owner_snapshot(self, owner: str) -> Mapping[str, "Buff"]:
        return MappingProxyType(dict(self._registry.get(owner, {})))

    def registry_snapshot(self) -> Mapping[str, Mapping[str, "Buff"]]:
        return MappingProxyType(
            {
                owner: MappingProxyType(dict(registered_buffs))
                for owner, registered_buffs in self._registry.items()
            }
        )

    def mutable_registry(self) -> dict[str, dict[str, "Buff"]]:
        return self._registry

    def items(self):
        return self._registry.items()


class PendingBuffQueue:
    """由 runtime 持有的待激活 Buff 队列。"""

    def __init__(self, queues: dict[str, list["Buff"]]) -> None:
        self._queues = queues

    def reset_for_beneficiaries(self, beneficiaries: list[str]) -> None:
        for beneficiary in beneficiaries:
            self._queues[beneficiary] = []

    def enqueue(self, beneficiary: str, buff: "Buff") -> None:
        self._queues[beneficiary].append(buff)

    def drain(self, beneficiary: str) -> list["Buff"]:
        queue = self.queue_for_runtime(beneficiary)
        drained: list["Buff"] = []
        while queue:
            drained.append(queue.pop())
        return drained

    def clear(self, beneficiary: str) -> None:
        self.queue_for_runtime(beneficiary).clear()

    def count(self) -> int:
        return sum(len(queue) for queue in self._queues.values())

    def beneficiaries(self) -> tuple[str, ...]:
        return tuple(self._queues)

    def queue_for_runtime(self, beneficiary: str) -> list["Buff"]:
        return self._queues.setdefault(beneficiary, [])

    def mutable_queues(self) -> dict[str, list["Buff"]]:
        return self._queues

    def __getitem__(self, beneficiary: str) -> list["Buff"]:
        return self._queues[beneficiary]

    def __setitem__(self, beneficiary: str, queue: list["Buff"]) -> None:
        self._queues[beneficiary] = queue

    def __iter__(self):
        return iter(self._queues)

    def __len__(self) -> int:
        return len(self._queues)

    def values(self):
        return self._queues.values()

    def items(self):
        return self._queues.items()


class ActiveBuffStore:
    """由 runtime 持有的激活 Buff 容器。"""

    def __init__(self, stores: dict[str, list["Buff"]]) -> None:
        self._stores = stores

    def ensure_beneficiary(self, beneficiary: str) -> list["Buff"]:
        return self._stores.setdefault(beneficiary, [])

    def append(self, beneficiary: str, buff: "Buff") -> None:
        self._stores[beneficiary].append(buff)

    def remove(self, beneficiary: str, buff: "Buff") -> None:
        self._stores[beneficiary].remove(buff)

    def find_by_index(self, beneficiary: str, buff_index: str) -> "Buff | None":
        return next(
            (
                active_buff
                for active_buff in self._stores[beneficiary]
                if active_buff.ft.index == buff_index
            ),
            None,
        )

    def active_buffs_snapshot(self, beneficiary: str) -> tuple["Buff", ...]:
        return tuple(self._stores.get(beneficiary, []))

    def active_buff_view_snapshot(self) -> Mapping[str, Sequence["Buff"]]:
        return MappingProxyType(
            {beneficiary: tuple(buffs) for beneficiary, buffs in self._stores.items()}
        )

    def mutable_stores(self) -> dict[str, list["Buff"]]:
        return self._stores

    def count(self) -> int:
        return sum(len(active_buffs) for active_buffs in self._stores.values())

    def beneficiaries(self) -> tuple[str, ...]:
        return tuple(self._stores)

    def items(self):
        return self._stores.items()


class EnemyDebuffMirror:
    """由 runtime 持有的敌人 Debuff 镜像，与敌人激活 Buff 容器绑定。"""

    def __init__(self, mirror: list["Buff"]) -> None:
        self._mirror = mirror

    def find_by_index(self, buff_index: str) -> "Buff | None":
        return next(
            (
                existing_buff
                for existing_buff in self._mirror
                if self._get_buff_index(existing_buff) == buff_index
            ),
            None,
        )

    def sync(self, buff: "Buff") -> None:
        existing_buff = self.find_by_index(self._get_buff_index(buff))
        if existing_buff is buff:
            return
        if existing_buff is not None:
            self._mirror.remove(existing_buff)
        if not any(mirrored_buff is buff for mirrored_buff in self._mirror):
            self._mirror.append(buff)

    def remove(self, buff: "Buff") -> None:
        existing_buff = self.find_by_index(self._get_buff_index(buff))
        if existing_buff is not None:
            self._mirror.remove(existing_buff)

    def mutable_mirror(self) -> list["Buff"]:
        return self._mirror

    @staticmethod
    def _get_buff_index(buff: "Buff") -> str:
        return buff.ft.index


class BuffRuntimeReadPort(ABC):
    """Buff runtime 只读接口。"""

    @abstractmethod
    def get_active_buffs(self, beneficiary: str) -> Sequence["Buff"]:
        """读取指定受益者当前激活中的 Buff。"""

    @abstractmethod
    def get_active_buff_view(self) -> Mapping[str, Sequence["Buff"]]:
        """读取全部受益者的激活 Buff 只读视图。"""

    @abstractmethod
    def get_exist_buff_snapshot(self, beneficiary: str) -> Mapping[str, "Buff"]:
        """读取指定受益者的模板 Buff 只读快照。"""

    @abstractmethod
    def get_exist_buff_snapshot_view(self) -> Mapping[str, Mapping[str, "Buff"]]:
        """读取全部受益者的模板 Buff 只读快照。"""


class DefaultBuffRuntimeReadAdapter(BuffRuntimeReadPort):
    """默认 Buff runtime 只读适配器，包装本轮模拟的 runtime state 持有者。"""

    def __init__(self, *, runtime_state: BuffRuntimeState) -> None:
        self._runtime_state = runtime_state

    def get_active_buffs(self, beneficiary: str) -> Sequence["Buff"]:
        return self._runtime_state.active_store_owner().active_buffs_snapshot(beneficiary)

    def get_active_buff_view(self) -> Mapping[str, Sequence["Buff"]]:
        return self._runtime_state.active_store_owner().active_buff_view_snapshot()

    def get_exist_buff_snapshot(self, beneficiary: str) -> Mapping[str, "Buff"]:
        return self._runtime_state.template_registry_owner().owner_snapshot(beneficiary)

    def get_exist_buff_snapshot_view(self) -> Mapping[str, Mapping[str, "Buff"]]:
        return self._runtime_state.template_registry_owner().registry_snapshot()


class BuffRuntimeFacade(ABC):
    """Buff runtime 写侧门面。"""

    @abstractmethod
    def get_registered_buff(self, beneficiary: str, buff_index: str) -> "Buff | None":
        """读取 runtime-owned 模板注册表中的 Buff。"""

    @abstractmethod
    def get_registered_buff_view(self, beneficiary: str) -> Mapping[str, "Buff"]:
        """读取 runtime-owned 模板注册表的只读视图。"""

    @abstractmethod
    def find_registered_buff_source(self, buff_index: str) -> tuple[str, "Buff"] | None:
        """查找包含指定 Buff 模板的受益者和模板。"""

    @abstractmethod
    def create_forced_add_buff(
        self,
        beneficiary: str,
        buff_index: str,
        *,
        tick: int,
        specified_count: int | float | None = None,
    ) -> "Buff":
        """从 runtime-owned 模板工厂创建并启动强制添加 Buff。"""

    @abstractmethod
    def enqueue_pending_buff(self, beneficiary: str, buff: "Buff") -> None:
        """写入本 tick 待激活 Buff 队列。"""

    @abstractmethod
    def drain_pending_buffs(self, beneficiary: str) -> list["Buff"]:
        """按旧 pop 顺序清空并返回本 tick 待激活 Buff。"""

    @abstractmethod
    def clear_pending_buffs(self, beneficiary: str) -> None:
        """清空本 tick 待激活 Buff 队列。"""

    @abstractmethod
    def append_active_buff(self, beneficiary: str, buff: "Buff") -> None:
        """写入激活 Buff 容器。"""

    @abstractmethod
    def remove_active_buff(self, beneficiary: str, buff: "Buff") -> None:
        """从激活 Buff 容器移除指定 Buff。"""

    @abstractmethod
    def end_active_buff(self, beneficiary: str, buff: "Buff", *, tick: int) -> None:
        """执行 Buff.end 并从旧 active 容器移除。"""

    @abstractmethod
    def settle_individual_buff_stack(self, buff: "Buff", *, tick: int) -> None:
        """结算层数独立 Buff 的过期 stack。"""

    @abstractmethod
    def sweep_active_buffs(self, *, tick: int) -> dict[str, list["Buff"]]:
        """遍历并结算本 tick 的激活 Buff 生命周期。"""

    @abstractmethod
    def find_active_buff_by_index(self, beneficiary: str, buff_index: str) -> "Buff | None":
        """按 Buff index 查找激活 Buff。"""

    @abstractmethod
    def sync_enemy_debuff_mirror(self, buff: "Buff") -> None:
        """按 Buff index 替换 enemy debuff 镜像并追加新 Buff。"""

    @abstractmethod
    def remove_enemy_debuff_mirror(self, buff: "Buff") -> None:
        """按 Buff index 从 enemy debuff 镜像移除 Buff。"""

    @abstractmethod
    def load_pending_buffs(
        self,
        *,
        time_now: int,
        load_mission_dict: dict,
        character_name_box: list[str],
        all_name_order_box: dict,
        sim_instance: "Simulator",
    ) -> dict[str, list["Buff"]]:
        """执行 Buff load 阶段并填充本 tick 待激活队列。"""

    @abstractmethod
    def activate_pending_buffs(self, *, timenow: float) -> dict[str, list["Buff"]]:
        """把本 tick 待激活 Buff 提升到旧 active 容器。"""

    @abstractmethod
    def update_time_related_effects(self, *, tick: int, enemy: "Enemy") -> dict[str, list["Buff"]]:
        """执行本 tick 的时间相关 Buff runtime 扫描。"""

    @abstractmethod
    def next_time_related_wakeup_tick(
        self,
        *,
        current_tick: int,
        enemy: "Enemy",
    ) -> int | None:
        """读取下一次时间相关 Buff/Dot/异常状态可能变化的 tick。"""

    @abstractmethod
    def settle_schedule_buffs(
        self,
        *,
        tick: int,
        enemy: "Enemy",
        sim_instance: "Simulator",
        skill_node: "SkillNode | LoadingMission | None" = None,
        anomaly_bar: "AnomalyBar | None" = None,
    ) -> None:
        """执行 Schedule 阶段 Buff 结算。"""


class DefaultBuffRuntimeFacade(BuffRuntimeFacade):
    """默认 Buff runtime 门面，包装本轮模拟的 runtime state 持有者。"""

    _EVENT_SETTLED_COMPLEX_EXIT_BUFFS = frozenset(
        {
            "Buff-角色-仪玄-4画-静心",
            "Buff-武器-精1索魂影眸-冲击力",
            "Buff-武器-精2索魂影眸-冲击力",
            "Buff-武器-精3索魂影眸-冲击力",
            "Buff-武器-精4索魂影眸-冲击力",
            "Buff-武器-精5索魂影眸-冲击力",
        }
    )

    def __init__(self, *, runtime_state: BuffRuntimeState) -> None:
        self._runtime_state = runtime_state
        self._post_activation_report_tick: int | None = None

    def get_registered_buff(self, beneficiary: str, buff_index: str) -> "Buff | None":
        return self._runtime_state.template_registry_owner().get_registered_buff(
            beneficiary, buff_index
        )

    def get_registered_buff_view(self, beneficiary: str) -> Mapping[str, "Buff"]:
        return self._runtime_state.template_registry_owner().owner_snapshot(beneficiary)

    def find_registered_buff_source(self, buff_index: str) -> tuple[str, "Buff"] | None:
        for beneficiary, registered_buffs in self._runtime_state.template_registry_owner().items():
            if buff_index in registered_buffs:
                return beneficiary, registered_buffs[buff_index]
        return None

    def create_forced_add_buff(
        self,
        beneficiary: str,
        buff_index: str,
        *,
        tick: int,
        specified_count: int | float | None = None,
    ) -> "Buff":
        from copy import deepcopy

        source_registry = self._runtime_state.template_registry_owner().for_owner(beneficiary)
        source_buff = source_registry[buff_index]
        buff_new = deepcopy(source_buff)
        buff_new.ft.operator = source_buff.ft.operator
        buff_new.ft.passively_updating = source_buff.ft.passively_updating
        buff_new.ft.beneficiary = source_buff.ft.beneficiary

        if source_buff.ft.simple_start_logic and buff_new.ft.simple_effect_logic:
            if specified_count is not None:
                buff_new.simple_start(
                    tick,
                    source_registry,
                    specified_count=specified_count,
                )
            else:
                buff_new.simple_start(tick, source_registry)
        elif not source_buff.ft.simple_start_logic:
            buff_new.logic.xstart(benifit=beneficiary)
        elif not source_buff.ft.simple_effect_logic:
            buff_new.logic.xeffect()
        return buff_new

    def enqueue_pending_buff(self, beneficiary: str, buff: "Buff") -> None:
        self._runtime_state.pending_queue_owner().enqueue(beneficiary, buff)

    def drain_pending_buffs(self, beneficiary: str) -> list["Buff"]:
        return self._runtime_state.pending_queue_owner().drain(beneficiary)

    def clear_pending_buffs(self, beneficiary: str) -> None:
        self._runtime_state.pending_queue_owner().clear(beneficiary)

    def append_active_buff(self, beneficiary: str, buff: "Buff") -> None:
        self._runtime_state.active_store_owner().append(beneficiary, buff)

    def remove_active_buff(self, beneficiary: str, buff: "Buff") -> None:
        self._runtime_state.active_store_owner().remove(beneficiary, buff)

    def end_active_buff(self, beneficiary: str, buff: "Buff", *, tick: int) -> None:
        sub_exist_buff_dict = self._runtime_state.template_registry_owner().for_owner(beneficiary)
        buff.end(tick, sub_exist_buff_dict)
        self.remove_active_buff(beneficiary, buff)
        report_to_log(
            f"[Buff END]:{tick}:{beneficiary} 的 {buff.ft.index} 结束，已从动态列表移除",
            level=4,
        )
        if buff.ft.is_debuff:
            self.remove_enemy_debuff_mirror(buff)

    def settle_individual_buff_stack(self, buff: "Buff", *, tick: int) -> None:
        expired_stack_items = [
            stack_item for stack_item in buff.dy.built_in_buff_box if stack_item[1] < tick
        ]
        for expired_stack_item in expired_stack_items:
            buff.dy.built_in_buff_box.remove(expired_stack_item)
        buff.dy.count = len(buff.dy.built_in_buff_box)

    def sweep_active_buffs(self, *, tick: int) -> dict[str, list["Buff"]]:
        from zsim.sim_progress.Update import Update_Buff

        active_store = self._runtime_state.active_store_owner()
        for beneficiary, active_buffs in active_store.items():
            buffs_to_remove: list["Buff"] = []
            for buff in active_buffs:
                Update_Buff.CheckBuff(buff, beneficiary)
                if not buff.ft.simple_exit_logic:
                    try:
                        should_exit = buff.logic.xexit(beneficiary=beneficiary)
                    except TypeError:
                        raise TypeError(f"{buff.ft.index}的xexit方法参数错误！")  # noqa: B904
                    if should_exit:
                        buffs_to_remove.append(buff)
                    else:
                        Update_Buff.report_buff_to_queue(
                            beneficiary,
                            tick,
                            buff.ft.index,
                            buff.dy.count,
                            True,
                            level=4,
                        )
                    continue

                if buff.ft.alltime:
                    Update_Buff.report_buff_to_queue(
                        beneficiary, tick, buff.ft.index, buff.dy.count, True, level=4
                    )
                    continue

                if buff.ft.individual_settled:
                    if len(buff.dy.built_in_buff_box) <= 0:
                        buffs_to_remove.append(buff)
                        continue
                    self.settle_individual_buff_stack(buff, tick=tick)
                    Update_Buff.report_buff_to_queue(
                        beneficiary, tick, buff.ft.index, buff.dy.count, True, level=4
                    )
                    continue

                if tick > buff.dy.endticks:
                    buffs_to_remove.append(buff)
                    continue

                Update_Buff.report_buff_to_queue(
                    beneficiary, tick, buff.ft.index, buff.dy.count, True, level=4
                )

            for buff in buffs_to_remove:
                self.end_active_buff(beneficiary, buff, tick=tick)

        return active_store.mutable_stores()

    def find_active_buff_by_index(self, beneficiary: str, buff_index: str) -> "Buff | None":
        return self._runtime_state.active_store_owner().find_by_index(
            beneficiary,
            buff_index,
        )

    def sync_enemy_debuff_mirror(self, buff: "Buff") -> None:
        self._runtime_state.enemy_mirror_owner().sync(buff)

    def remove_enemy_debuff_mirror(self, buff: "Buff") -> None:
        self._runtime_state.enemy_mirror_owner().remove(buff)

    def load_pending_buffs(
        self,
        *,
        time_now: int,
        load_mission_dict: dict,
        character_name_box: list[str],
        all_name_order_box: dict,
        sim_instance: "Simulator",
    ) -> dict[str, list["Buff"]]:
        from zsim.sim_progress.Buff.BuffLoad import BuffLoadLoop

        return BuffLoadLoop(
            time_now,
            load_mission_dict,
            self._runtime_state.template_registry_owner(),
            character_name_box,
            self._runtime_state.pending_queue_owner(),
            all_name_order_box,
            sim_instance=sim_instance,
            load_lifecycle_cache=self._runtime_state.load_lifecycle_cache_owner(),
        )

    def activate_pending_buffs(self, *, timenow: float) -> dict[str, list["Buff"]]:
        pending_queue = self._runtime_state.pending_queue_owner()
        activated = False
        for beneficiary in pending_queue.beneficiaries():
            for buff in pending_queue.drain(beneficiary):
                self._activate_pending_buff(beneficiary, buff)
                activated = True
        if activated:
            self._post_activation_report_tick = int(timenow) + 1
        return self._runtime_state.active_store_owner().mutable_stores()

    def update_time_related_effects(self, *, tick: int, enemy: "Enemy") -> dict[str, list["Buff"]]:
        from zsim.sim_progress.Update import Update_Buff

        return Update_Buff.update_time_related_effect(
            timetick=tick,
            enemy=enemy,
            runtime_facade=self,
        )

    def next_time_related_wakeup_tick(
        self,
        *,
        current_tick: int,
        enemy: "Enemy",
    ) -> int | None:
        from zsim.sim_progress.Update import Update_Buff

        candidates: list[int] = []
        if (
            self._post_activation_report_tick is not None
            and self._post_activation_report_tick > current_tick
        ):
            candidates.append(self._post_activation_report_tick)
        elif (
            self._post_activation_report_tick is not None
            and self._post_activation_report_tick <= current_tick
        ):
            self._post_activation_report_tick = None
        active_store = self._runtime_state.active_store_owner()
        for _, active_buffs in active_store.items():
            for buff in active_buffs:
                wakeup_tick = self._next_active_buff_lifecycle_tick(
                    buff,
                    current_tick=current_tick,
                )
                if wakeup_tick is not None:
                    candidates.append(wakeup_tick)
        dot_or_anomaly_tick = Update_Buff.next_dot_or_anomaly_wakeup_tick(
            enemy,
            current_tick,
        )
        if dot_or_anomaly_tick is not None:
            candidates.append(dot_or_anomaly_tick)
        future_candidates = [tick for tick in candidates if tick > current_tick]
        if not future_candidates:
            return None
        return min(future_candidates)

    @staticmethod
    def _next_active_buff_lifecycle_tick(
        buff: "Buff",
        *,
        current_tick: int,
    ) -> int | None:
        if not buff.ft.simple_exit_logic:
            event_settled_wakeup = DefaultBuffRuntimeFacade._event_settled_complex_exit_wakeup_tick(
                buff,
                current_tick=current_tick,
            )
            if event_settled_wakeup is not None:
                return event_settled_wakeup
            if DefaultBuffRuntimeFacade._is_event_settled_complex_exit(buff):
                return None
            return current_tick + 1
        if buff.ft.alltime:
            return None
        if buff.ft.individual_settled:
            stack_items = list(buff.dy.built_in_buff_box)
            if not stack_items:
                return current_tick + 1
            candidates = []
            for stack_item in stack_items:
                end_tick = int(stack_item[1])
                candidates.append(end_tick + 1 if end_tick >= current_tick else current_tick + 1)
            return min(candidates)
        end_tick = int(buff.dy.endticks)
        return end_tick + 1 if end_tick >= current_tick else current_tick + 1

    @staticmethod
    def _is_event_settled_complex_exit(buff: "Buff") -> bool:
        index = getattr(buff.ft, "index", None)
        if index not in DefaultBuffRuntimeFacade._EVENT_SETTLED_COMPLEX_EXIT_BUFFS:
            return False
        return True

    @staticmethod
    def _event_settled_complex_exit_wakeup_tick(
        buff: "Buff",
        *,
        current_tick: int,
    ) -> int | None:
        index = getattr(buff.ft, "index", None)
        if index == "Buff-角色-耀佳音-咏叹华彩":
            record = getattr(getattr(buff, "logic", None), "record", None)
            char = getattr(record, "char", None)
            if char is None:
                return current_tick + 1
            return None if getattr(char, "idyllic_cadenza", False) else current_tick + 1
        if index == "Buff-角色-仪玄-4画-静心":
            record = getattr(getattr(buff, "logic", None), "record", None)
            if record is None:
                return current_tick + 1
            return None if getattr(record, "c4_counter", 0) > 0 else current_tick + 1
        if index in {
            "Buff-武器-精1索魂影眸-冲击力",
            "Buff-武器-精2索魂影眸-冲击力",
            "Buff-武器-精3索魂影眸-冲击力",
            "Buff-武器-精4索魂影眸-冲击力",
            "Buff-武器-精5索魂影眸-冲击力",
        }:
            # 当前 xexit 实现不会基于时间自然退出；触发器层数变化由命中事件驱动。
            return None
        return None

    def settle_schedule_buffs(
        self,
        *,
        tick: int,
        enemy: "Enemy",
        sim_instance: "Simulator",
        skill_node: "SkillNode | LoadingMission | None" = None,
        anomaly_bar: "AnomalyBar | None" = None,
    ) -> None:
        from zsim.sim_progress.Buff import JudgeTools

        action_now, should_continue = self._resolve_schedule_action(
            tick=tick,
            sim_instance=sim_instance,
            skill_node=skill_node,
            anomaly_bar=anomaly_bar,
        )
        if not should_continue:
            return
        if action_now is None:
            print("警告！！！ScheduleBuffSettle函数没有找到 action_now！")
            return

        char_on_field = getattr(action_now, "char_name")
        all_name_order_box = JudgeTools.find_all_name_order_box(sim_instance=sim_instance)
        name_box_on_field = all_name_order_box[char_on_field]
        template_registry_owner = self._runtime_state.template_registry_owner()
        event_kwargs = self._schedule_event_kwargs(
            skill_node=skill_node,
            anomaly_bar=anomaly_bar,
        )

        for char_name in name_box_on_field:
            if char_name == "enemy":
                continue

            sub_template_registry = template_registry_owner.for_owner(char_name)
            if char_name == char_on_field:
                self._process_schedule_on_field_buffs(
                    template_buffs=sub_template_registry,
                    name_box_now=name_box_on_field,
                    tick=tick,
                    event_kwargs=event_kwargs,
                )
                continue

            self._process_schedule_backend_buffs(
                template_buffs=sub_template_registry,
                all_name_order_box=all_name_order_box,
                tick=tick,
                event_kwargs=event_kwargs,
            )

    def _get_pending_queue(self, beneficiary: str) -> list["Buff"]:
        return self._runtime_state.pending_queue_owner().queue_for_runtime(beneficiary)

    def _find_enemy_debuff_mirror(self, buff: "Buff") -> "Buff | None":
        return self._runtime_state.enemy_mirror_owner().find_by_index(self._get_buff_index(buff))

    def _activate_pending_buff(self, beneficiary: str, buff: "Buff") -> None:
        from zsim.sim_progress.Buff.buff_class import Buff

        if not isinstance(buff, Buff):
            raise ValueError(f"loading_buff_dict中的{buff}元素不是Buff类")
        if self._should_skip_pending_buff(buff):
            return

        existing_buff = self.find_active_buff_by_index(beneficiary, buff.ft.index)
        if existing_buff is not None:
            if buff.ft.alltime:
                return
            self.remove_active_buff(beneficiary, existing_buff)

        self.append_active_buff(beneficiary, buff)
        if beneficiary == "enemy":
            self.sync_enemy_debuff_mirror(buff)

    @staticmethod
    def _should_skip_pending_buff(buff: "Buff") -> bool:
        return (
            not buff.dy.active
            or (buff.dy.startticks == 0 and buff.dy.endticks == 0)
            or buff.dy.count == 0
        )

    def _process_schedule_on_field_buffs(
        self,
        *,
        template_buffs: dict[str, "Buff"],
        name_box_now: list[str],
        tick: int,
        event_kwargs: dict[str, object],
    ) -> None:
        for buff in template_buffs.values():
            self._check_schedule_buff(buff)
            if not buff.ft.schedule_judge:
                continue
            if buff.ft.passively_updating:
                continue
            if not buff.logic.xjudge(**event_kwargs):
                continue

            selected_beneficiaries = self._selected_schedule_beneficiaries(
                buff,
                name_box_now,
            )
            self._add_schedule_buff(
                selected_beneficiaries=selected_beneficiaries,
                source_buff=buff,
                tick=tick,
                source_template_registry=template_buffs,
                event_kwargs=event_kwargs,
            )

    def _process_schedule_backend_buffs(
        self,
        *,
        template_buffs: dict[str, "Buff"],
        all_name_order_box: dict[str, list[str]],
        tick: int,
        event_kwargs: dict[str, object],
    ) -> None:
        for buff in template_buffs.values():
            self._check_schedule_buff(buff)
            if not buff.ft.schedule_judge:
                continue
            if not buff.ft.backend_acitve:
                continue
            if buff.ft.passively_updating:
                continue
            if not buff.logic.xjudge(**event_kwargs):
                continue

            main_char = buff.ft.operator
            selected_beneficiaries = self._selected_schedule_beneficiaries(
                buff,
                all_name_order_box[main_char],
            )
            self._add_schedule_buff(
                selected_beneficiaries=selected_beneficiaries,
                source_buff=buff,
                tick=tick,
                source_template_registry=template_buffs,
                event_kwargs=event_kwargs,
            )

    def _add_schedule_buff(
        self,
        *,
        selected_beneficiaries: list[str],
        source_buff: "Buff",
        tick: int,
        source_template_registry: dict[str, "Buff"],
        event_kwargs: dict[str, object],
    ) -> None:
        from zsim.sim_progress.Buff.buff_class import Buff

        if not source_buff.ft.schedule_judge:
            raise ValueError(f"{source_buff.ft.index}不是schedule阶段buff！")

        for beneficiary in selected_beneficiaries:
            buff_new = Buff.create_new_from_existing(source_buff)
            buff_new.ft.operator = source_buff.ft.operator
            buff_new.ft.passively_updating = source_buff.ft.passively_updating
            if source_buff.ft.simple_effect_logic:
                buff_new.simple_start(tick, source_template_registry)
            else:
                buff_new.logic.xeffect(**event_kwargs)

            existing_buff = self.find_active_buff_by_index(
                beneficiary,
                source_buff.ft.index,
            )
            if existing_buff is not None:
                self.remove_active_buff(beneficiary, existing_buff)
            self.append_active_buff(beneficiary, buff_new)
            if beneficiary == "enemy":
                self.sync_enemy_debuff_mirror(buff_new)

    def _resolve_schedule_action(
        self,
        *,
        tick: int,
        sim_instance: "Simulator",
        skill_node: "SkillNode | LoadingMission | None",
        anomaly_bar: "AnomalyBar | None",
    ) -> tuple[object | None, bool]:
        from zsim.sim_progress.Buff import JudgeTools
        from zsim.sim_progress.Load import LoadingMission
        from zsim.sim_progress.Preload import SkillNode

        action_result = None
        if anomaly_bar is not None:
            if anomaly_bar.activated_by is not None:
                action_result = anomaly_bar.activated_by
        elif skill_node is not None:
            if isinstance(skill_node, SkillNode):
                action_result = skill_node
            elif isinstance(skill_node, LoadingMission):
                action_result = skill_node.mission_node
            else:
                print(
                    f"ScheduleBuffSettle函数接收到了无法识别的event类型{type(skill_node).__name__}"
                )
                return None, False

        if action_result is not None:
            return action_result, True

        preload_data = JudgeTools.find_preload_data(sim_instance=sim_instance)
        return preload_data.get_on_field_node(tick), True

    @staticmethod
    def _schedule_event_kwargs(
        *,
        skill_node: "SkillNode | LoadingMission | None",
        anomaly_bar: "AnomalyBar | None",
    ) -> dict[str, object]:
        event_kwargs: dict[str, object] = {}
        if skill_node is not None:
            event_kwargs["skill_node"] = skill_node
        if anomaly_bar is not None:
            event_kwargs["anomaly_bar"] = anomaly_bar
        return event_kwargs

    @staticmethod
    def _selected_schedule_beneficiaries(
        buff: "Buff",
        name_box_now: list[str],
    ) -> list[str]:
        adding_buff_code = str(int(buff.ft.add_buff_to)).zfill(4)
        return [name_box_now[i] for i in range(len(name_box_now)) if adding_buff_code[i] == "1"]

    @staticmethod
    def _check_schedule_buff(buff: "Buff") -> None:
        from zsim.sim_progress.Buff.buff_class import Buff

        if not isinstance(buff, Buff):
            raise TypeError(f"{buff}不是Buff类！")

    @staticmethod
    def _get_buff_index(buff: "Buff") -> str:
        return buff.ft.index


def create_buff_runtime_read_port(
    *,
    runtime_state: BuffRuntimeState,
) -> BuffRuntimeReadPort:
    """创建 Buff runtime 只读入口。"""
    return runtime_state.create_read_port()


LegacyBuffRuntimeFacade = DefaultBuffRuntimeFacade


def create_legacy_buff_runtime_facade(
    *,
    runtime_state: BuffRuntimeState,
) -> BuffRuntimeFacade:
    return runtime_state.create_facade()


@dataclass(frozen=True, slots=True)
class BuffTimeRelatedWakeupSource:
    """由本轮模拟 Buff runtime 门面驱动的时间相关唤醒源。"""

    runtime_facade: object
    enemy: "Enemy"
    name: str = "buff-time-related"

    def next_wakeup_tick(self, current_tick: int) -> int | None:
        next_time_related = getattr(
            self.runtime_facade,
            "next_time_related_wakeup_tick",
            None,
        )
        if not callable(next_time_related):
            return None
        return next_time_related(current_tick=current_tick, enemy=self.enemy)


__all__ = [
    "BuffRuntimeReadPort",
    "BuffRuntimeFacade",
    "BuffRuntimeState",
    "ActiveBuffStore",
    "PendingBuffQueue",
    "BuffTimeRelatedWakeupSource",
    "DefaultBuffRuntimeFacade",
    "DefaultBuffRuntimeReadAdapter",
    "LegacyBuffRuntimeFacade",
    "create_buff_runtime_read_port",
    "create_legacy_buff_runtime_facade",
]
