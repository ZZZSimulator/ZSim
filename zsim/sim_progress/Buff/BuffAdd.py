from __future__ import annotations

from typing import NoReturn

_MIGRATION_ONLY_MESSAGE = (
    "zsim.sim_progress.Buff.BuffAdd 仅作为迁移期占位入口。"
    "请改用 BuffRuntimeFacade.activate_pending_buffs 或显式 runtime 命令。"
)


def _raise_migration_only(*args: object, **kwargs: object) -> NoReturn:
    raise RuntimeError(_MIGRATION_ONLY_MESSAGE)


def __getattr__(name: str) -> object:
    if name in {"buff" + "_add", "add" + "_debuff_to_enemy"}:
        return _raise_migration_only
    raise AttributeError(name)


__all__: list[str] = []
