from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Mapping, Sequence

if TYPE_CHECKING:
    from zsim.sim_progress.data_struct.schedule_dispatch import ScheduledEventEmitterProvider
    from zsim.sim_progress.ScheduledEvent.buff_runtime import BuffRuntimeReadPort
    from zsim.simulator.simulator_class import Simulator

    from .. import Buff


_PREPARATION_CONTEXT_CACHE_ATTR = "_zsim_preparation_context_cache"
_PREPARATION_CONTEXT_CACHE_VERSION = 1


@dataclass(frozen=True)
class CharacterLookup:
    characters: Sequence[Any]

    def by_cid(self, cid: int) -> Any:
        for character in self.characters:
            if character.CID == cid:
                return character
        raise ValueError(f"并未找到CID为{cid}的角色！")

    def by_name(self, name: str) -> Any:
        for character in self.characters:
            if character.NAME == name:
                return character
        raise ValueError(f"未找到名为{name}的角色")


@dataclass(frozen=True)
class EquipmentOwnerLookup:
    judge_list_set: Sequence[Sequence[str]]

    def owner_for(self, item_name: str) -> str | None:
        if "二件套" not in item_name:
            for sub_list in self.judge_list_set:
                for item in sub_list:
                    if item == item_name and item != sub_list[3]:
                        return sub_list[0]
        else:
            for sub_list in self.judge_list_set:
                for item in sub_list:
                    if item == item_name and item == sub_list[3]:
                        return sub_list[0]
        return None


@dataclass(frozen=True)
class BuffTemplateRegistryReadPort:
    templates_by_owner: Mapping[str, Mapping[str, Any]]

    def all_templates(self) -> Mapping[str, Mapping[str, Any]]:
        return self.templates_by_owner

    def for_owner(self, owner_name: str) -> Mapping[str, Any]:
        return self.templates_by_owner[owner_name]


@dataclass(frozen=True, eq=False)
class TriggerBuffRef:
    operator: str
    buff_index: str
    operator_kind: str = "owner"

    OWNER: ClassVar[str] = "owner"
    EQUIPPER: ClassVar[str] = "equipper"
    ENEMY_SOURCE: ClassVar[str] = "enemy"

    @classmethod
    def owner(cls, operator: str, buff_index: str) -> "TriggerBuffRef":
        return cls(operator=operator, buff_index=buff_index, operator_kind=cls.OWNER)

    @classmethod
    def equipper(cls, buff_index: str) -> "TriggerBuffRef":
        return cls(
            operator=cls.EQUIPPER,
            buff_index=buff_index,
            operator_kind=cls.EQUIPPER,
        )

    @classmethod
    def enemy(cls, buff_index: str) -> "TriggerBuffRef":
        return cls(
            operator=cls.ENEMY_SOURCE,
            buff_index=buff_index,
            operator_kind=cls.ENEMY_SOURCE,
        )

    @classmethod
    def from_legacy_tuple(cls, trigger_buff_0: tuple[Any, ...]) -> "TriggerBuffRef":
        operator = trigger_buff_0[0]
        buff_index = trigger_buff_0[1]
        if operator == cls.EQUIPPER:
            return cls.equipper(buff_index)
        if operator == cls.ENEMY_SOURCE:
            return cls.enemy(buff_index)
        return cls.owner(operator, buff_index)

    @classmethod
    def coerce(cls, trigger_buff_0: Any) -> "TriggerBuffRef":
        if isinstance(trigger_buff_0, cls):
            return trigger_buff_0
        if isinstance(trigger_buff_0, tuple):
            return cls.from_legacy_tuple(trigger_buff_0)
        raise TypeError("输入的参数必须是tuple或TriggerBuffRef！")

    @property
    def requires_character(self) -> bool:
        return self.operator_kind == self.ENEMY_SOURCE

    def with_resolved_owner(self, owner_name: str) -> "TriggerBuffRef":
        return TriggerBuffRef.owner(owner_name, self.buff_index)

    def as_legacy_tuple(self) -> tuple[str, str]:
        return (self.operator, self.buff_index)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, TriggerBuffRef):
            return (
                self.operator == other.operator
                and self.buff_index == other.buff_index
                and self.operator_kind == other.operator_kind
            )
        if isinstance(other, tuple):
            return self.as_legacy_tuple() == other
        return False

    def __hash__(self) -> int:
        return hash((self.operator, self.buff_index, self.operator_kind))


@dataclass(frozen=True)
class TriggerBuffLookup:
    template_registry: BuffTemplateRegistryReadPort

    def find_by_operator_and_index(self, operator: str, buff_index: str) -> Any:
        return self.find_by_ref(TriggerBuffRef.owner(operator, buff_index))

    def find_by_ref(self, trigger_ref: TriggerBuffRef) -> Any:
        founded_list = []
        operator = trigger_ref.operator
        for buff_found in self.template_registry.for_owner(operator).values():
            if trigger_ref.buff_index in buff_found.ft.index:
                founded_list.append(buff_found)
        if len(founded_list) != 1:
            founded_buff_index_list = [founded_buff.ft.index for founded_buff in founded_list]
            if len(set(founded_buff_index_list)) != len(founded_list):
                raise ValueError(f"在{operator}的sub_exist_buff_dict中找到了2个以上的同名buff！")
            trigger_index_length = len(trigger_ref.buff_index)
            for buff_found in founded_list:
                if buff_found.ft.index[-trigger_index_length:] == trigger_ref.buff_index:
                    return buff_found
            raise ValueError(
                f"并未找到Buff名后缀为{trigger_ref.buff_index}的触发器Buff，说明提供的用于寻找trigger_buff_0的关键词无法有效筛选出触发器，请调整关键词或者数据库Buff Index"
            )
        return founded_list[0]


@dataclass(frozen=True)
class PreloadCommandPort:
    sim_instance: "Simulator"
    preload_data: Any
    scheduled_event_emitter_provider: "ScheduledEventEmitterProvider"

    @classmethod
    def from_sim_instance(cls, sim_instance: "Simulator") -> "PreloadCommandPort":
        from zsim.sim_progress.data_struct.schedule_dispatch import (
            ScheduledEventEmitterProvider,
        )

        return cls(
            sim_instance=sim_instance,
            preload_data=sim_instance.preload.preload_data,
            scheduled_event_emitter_provider=ScheduledEventEmitterProvider.from_sim_instance_getter(
                lambda: sim_instance
            ),
        )

    def schedule_preload_events(
        self,
        *,
        preload_tick_list: list[int],
        skill_tag_list: list[str],
        apl_priority_list: list[int] | None = None,
        active_generation_list: list[bool] | None = None,
    ) -> None:
        from zsim.sim_progress.data_struct.SchedulePreload import (
            schedule_preload_event_factory,
        )

        schedule_preload_event_factory(
            preload_tick_list=preload_tick_list,
            skill_tag_list=skill_tag_list,
            preload_data=self.preload_data,
            sim_instance=self.sim_instance,
            apl_priority_list=apl_priority_list,
            active_generation_list=active_generation_list,
            scheduled_event_emitter_provider=self.scheduled_event_emitter_provider,
        )


@dataclass(frozen=True)
class ResourceRefreshCommandPort:
    scheduled_event_emitter_provider: "ScheduledEventEmitterProvider"

    @classmethod
    def from_sim_instance(cls, sim_instance: "Simulator") -> "ResourceRefreshCommandPort":
        from zsim.sim_progress.data_struct.schedule_dispatch import (
            ScheduledEventEmitterProvider,
        )

        return cls(
            scheduled_event_emitter_provider=ScheduledEventEmitterProvider.from_sim_instance_getter(
                lambda: sim_instance
            ),
        )

    def publish_refresh(
        self,
        *,
        sp_target: tuple[str, ...] | None = None,
        sp_value: float | int = 0,
        decibel_target: tuple[str, ...] | None = None,
        decibel_value: float | int = 0,
    ) -> None:
        from zsim.sim_progress.data_struct.sp_update_data import ScheduleRefreshData

        refresh_data = ScheduleRefreshData(
            sp_target=sp_target,
            sp_value=sp_value,
            decibel_target=decibel_target,
            decibel_value=decibel_value,
        )
        self.scheduled_event_emitter_provider.create_emitter().emit_scheduled(refresh_data)


@dataclass(frozen=True)
class PreparationContext:
    character_lookup: CharacterLookup
    equipment_owner_lookup: EquipmentOwnerLookup
    template_registry: BuffTemplateRegistryReadPort
    trigger_buff_lookup: TriggerBuffLookup
    buff_runtime_read_port: "BuffRuntimeReadPort"
    enemy: Any
    action_stack: Any
    preload_data: Any
    preload_commands: PreloadCommandPort
    resource_refresh_commands: ResourceRefreshCommandPort
    char_obj_list: Sequence[Any]

    @property
    def active_buff_view(self) -> Mapping[str, Sequence[Any]]:
        return self.buff_runtime_read_port.get_active_buff_view()

    def find_equipper(self, item_name: str) -> str | None:
        return self.equipment_owner_lookup.owner_for(item_name)

    def find_char_from_cid(self, cid: int) -> Any:
        return self.character_lookup.by_cid(cid)

    def find_char_from_name(self, name: str) -> Any:
        return self.character_lookup.by_name(name)

    def find_sub_exist_buff_dict(self, owner_name: str) -> Mapping[str, Any]:
        return self.template_registry.for_owner(owner_name)

    def find_trigger_buff(self, operator: str, buff_index: str) -> Any:
        return self.trigger_buff_lookup.find_by_operator_and_index(operator, buff_index)

    def find_trigger_buff_ref(self, trigger_ref: TriggerBuffRef) -> Any:
        return self.trigger_buff_lookup.find_by_ref(trigger_ref)

    def find_active_buffs(self, owner_name: Any) -> Sequence[Any]:
        return self.active_buff_view[owner_name]


def _create_buff_runtime_read_port_from_sim_instance(
    sim_instance: "Simulator",
) -> "BuffRuntimeReadPort":
    runtime_state = getattr(sim_instance, "buff_runtime_state", None)
    if runtime_state is not None:
        return runtime_state.create_read_port()
    from zsim.sim_progress.ScheduledEvent.buff_runtime import (
        create_buff_runtime_read_port,
    )

    return create_buff_runtime_read_port(
        dynamic_buff=sim_instance.global_stats.DYNAMIC_BUFF_DICT,
        exist_buff_dict=sim_instance.load_data.exist_buff_dict,
    )


def _create_template_registry_read_port_from_sim_instance(
    sim_instance: "Simulator",
) -> BuffTemplateRegistryReadPort:
    runtime_state = getattr(sim_instance, "buff_runtime_state", None)
    if runtime_state is not None:
        template_registry_owner = getattr(runtime_state, "template_registry_owner", None)
        if template_registry_owner is not None:
            registry_owner = template_registry_owner()
            registry_getter = getattr(registry_owner, "mutable_registry", None)
            if registry_getter is None:
                registry_getter = getattr(registry_owner, "as_compat_dict")
            return BuffTemplateRegistryReadPort(templates_by_owner=registry_getter())
    return BuffTemplateRegistryReadPort(templates_by_owner={})


def _preparation_context_cache_key(
    sim_instance: "Simulator",
) -> tuple[int, int, int, int, int, int, int, int]:
    runtime_state = getattr(sim_instance, "buff_runtime_state", None)
    if runtime_state is not None:
        template_registry_identity = id(runtime_state)
    else:
        template_registry_identity = id(None)
    return (
        _PREPARATION_CONTEXT_CACHE_VERSION,
        id(runtime_state),
        template_registry_identity,
        id(sim_instance.char_data.char_obj_list),
        id(sim_instance.init_data.Judge_list_set),
        id(sim_instance.schedule_data.enemy),
        id(sim_instance.load_data.action_stack),
        id(sim_instance.preload.preload_data),
    )


def _read_cached_preparation_context(
    sim_instance: "Simulator",
    cache_key: tuple[int, int, int, int, int, int, int, int],
) -> PreparationContext | None:
    cache_entry = getattr(sim_instance, _PREPARATION_CONTEXT_CACHE_ATTR, None)
    if not isinstance(cache_entry, tuple) or len(cache_entry) != 2:
        return None
    cached_key, cached_context = cache_entry
    if cached_key != cache_key or not isinstance(cached_context, PreparationContext):
        return None
    return cached_context


def _store_cached_preparation_context(
    sim_instance: "Simulator",
    cache_key: tuple[int, int, int, int, int, int, int, int],
    context: PreparationContext,
) -> None:
    try:
        setattr(sim_instance, _PREPARATION_CONTEXT_CACHE_ATTR, (cache_key, context))
    except (AttributeError, TypeError):
        pass


def build_preparation_context_from_sim_instance(
    sim_instance: "Simulator",
) -> PreparationContext:
    cache_key = _preparation_context_cache_key(sim_instance)
    cached_context = _read_cached_preparation_context(sim_instance, cache_key)
    if cached_context is not None:
        return cached_context
    template_registry = _create_template_registry_read_port_from_sim_instance(sim_instance)
    context = PreparationContext(
        character_lookup=CharacterLookup(sim_instance.char_data.char_obj_list),
        equipment_owner_lookup=EquipmentOwnerLookup(sim_instance.init_data.Judge_list_set),
        template_registry=template_registry,
        trigger_buff_lookup=TriggerBuffLookup(template_registry),
        buff_runtime_read_port=_create_buff_runtime_read_port_from_sim_instance(sim_instance),
        enemy=sim_instance.schedule_data.enemy,
        action_stack=sim_instance.load_data.action_stack,
        preload_data=sim_instance.preload.preload_data,
        preload_commands=PreloadCommandPort.from_sim_instance(sim_instance),
        resource_refresh_commands=ResourceRefreshCommandPort.from_sim_instance(sim_instance),
        char_obj_list=sim_instance.char_data.char_obj_list,
    )
    _store_cached_preparation_context(sim_instance, cache_key, context)
    return context


def build_preparation_context_from_buff(buff_instance: "Buff") -> PreparationContext:
    return build_preparation_context_from_sim_instance(buff_instance.sim_instance)


def create_calculator_runtime_read_context_from_sim_instance(
    *,
    sim_instance: Any,
    enemy: Any,
    character: Any | None = None,
    query_node: Any | None = None,
    beneficiary: str | None = None,
) -> Any:
    from zsim.sim_progress.calculation.calculator import (
        create_anomaly_attribute_read_context,
    )
    from zsim.sim_progress.calculation.calculator import (
        create_calculator_runtime_read_context_from_sim_instance as _create_calculator_runtime_read_context_from_sim_instance,
    )

    try:
        return _create_calculator_runtime_read_context_from_sim_instance(
            sim_instance=sim_instance,
            enemy=enemy,
            character=character,
            query_node=query_node,
            beneficiary=beneficiary,
        )
    except AttributeError as exc:
        if str(exc) != "sim_instance must expose buff_runtime_state":
            raise
        if hasattr(sim_instance, "global_stats"):
            raise
        return create_anomaly_attribute_read_context(
            enemy=enemy,
            active_buff_view={},
            character=character,
            query_node=query_node,
            sim_instance=sim_instance,
            char_name=beneficiary,
        )
