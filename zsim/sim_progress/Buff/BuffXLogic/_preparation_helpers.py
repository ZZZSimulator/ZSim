from collections.abc import Callable
from typing import Any, TypeVar

RecordT = TypeVar("RecordT")
_PREPARED_CONTEXT_SIGNATURES_ATTR = "_zsim_prepared_context_signatures"


def _freeze_signature_value(value: Any) -> Any:
    try:
        hash(value)
    except TypeError:
        return ("id", id(value))
    return value


def _preparation_signature(logic: Any, kwargs: dict[str, Any]) -> tuple[Any, ...]:
    buff_instance = logic.buff_instance
    sim_instance = getattr(buff_instance, "sim_instance", None)
    runtime_state = getattr(sim_instance, "buff_runtime_state", None)
    kwargs_items = tuple(kwargs.items())
    try:
        hash(kwargs_items)
    except TypeError:
        kwargs_items = tuple((key, _freeze_signature_value(value)) for key, value in kwargs.items())
    return (
        id(sim_instance),
        id(runtime_state),
        id(logic.buff_0),
        kwargs_items,
    )


def _has_initialized_record(logic: Any) -> bool:
    buff_0 = getattr(logic, "buff_0", None)
    history = getattr(buff_0, "history", None)
    return getattr(history, "record", None) is not None


def _already_prepared(logic: Any, signature: tuple[Any, ...]) -> bool:
    if not _has_initialized_record(logic):
        return False
    signatures = getattr(logic, _PREPARED_CONTEXT_SIGNATURES_ATTR, None)
    return isinstance(signatures, set) and signature in signatures


def _mark_prepared(logic: Any, signature: tuple[Any, ...]) -> None:
    signatures = getattr(logic, _PREPARED_CONTEXT_SIGNATURES_ATTR, None)
    if not isinstance(signatures, set):
        signatures = set()
        try:
            setattr(logic, _PREPARED_CONTEXT_SIGNATURES_ATTR, signatures)
        except (AttributeError, TypeError):
            return
    signatures.add(signature)


def prepare_with_context(
    logic: Any,
    *,
    check_preparation_func: Callable[..., Any],
    context_builder: Callable[[Any], Any],
    **kwargs: Any,
) -> Any:
    signature = _preparation_signature(logic, kwargs)
    if _already_prepared(logic, signature):
        return None
    preparation_context = context_builder(logic.buff_instance)
    result = check_preparation_func(
        buff_instance=logic.buff_instance,
        buff_0=logic.buff_0,
        preparation_context=preparation_context,
        **kwargs,
    )
    _mark_prepared(logic, signature)
    return result


def ensure_owner_template_record(
    logic: Any,
    *,
    owner_name: str,
    record_factory: Callable[[], RecordT],
    context_builder: Callable[[Any], Any],
) -> RecordT:
    if logic.buff_0 is None:
        try:
            preparation_context = context_builder(logic.buff_instance)
            logic.buff_0 = preparation_context.find_sub_exist_buff_dict(owner_name)[
                logic.buff_instance.ft.index
            ]
        except AttributeError:
            from zsim.sim_progress.Buff import JudgeTools

            legacy_registry = JudgeTools.find_exist_buff_dict(
                sim_instance=logic.buff_instance.sim_instance
            )
            logic.buff_0 = legacy_registry[owner_name][logic.buff_instance.ft.index]
    if not hasattr(logic.buff_0.history, "record") or logic.buff_0.history.record is None:
        logic.buff_0.history.record = record_factory()
    logic.record = logic.buff_0.history.record
    return logic.record


def ensure_equipper_template_record(
    logic: Any,
    *,
    item_name: str,
    record_factory: Callable[[], RecordT],
    context_builder: Callable[[Any], Any],
) -> RecordT:
    preparation_context = None
    if logic.equipper is None:
        preparation_context = context_builder(logic.buff_instance)
        logic.equipper = preparation_context.find_equipper(item_name)
    if logic.buff_0 is None:
        if preparation_context is None:
            preparation_context = context_builder(logic.buff_instance)
        logic.buff_0 = preparation_context.find_sub_exist_buff_dict(logic.equipper)[
            logic.buff_instance.ft.index
        ]
    if not hasattr(logic.buff_0.history, "record") or logic.buff_0.history.record is None:
        logic.buff_0.history.record = record_factory()
    logic.record = logic.buff_0.history.record
    return logic.record
