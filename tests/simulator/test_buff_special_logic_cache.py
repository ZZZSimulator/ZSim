from __future__ import annotations

from types import SimpleNamespace

from zsim.sim_progress.Buff import buff_class
from zsim.sim_progress.Buff.buff_class import Buff


def _buff_with_special_logic(index: str) -> Buff:
    buff = Buff.__new__(Buff)
    buff.ft = SimpleNamespace(index=index)
    buff.logic = SimpleNamespace()
    buff.buff_config = {
        index: {
            "module": ".BuffXLogic.DoesNotExistForCacheTest",
            "class": "DoesNotExistForCacheTest",
        }
    }
    return buff


def test_missing_special_logic_module_is_cached_and_warned_once(
    monkeypatch,
    capsys,
) -> None:
    buff_class._SPECIAL_LOGIC_CLASS_CACHE.clear()
    buff_class._MISSING_SPECIAL_LOGIC_MODULES.clear()
    buff_class._REPORTED_MISSING_SPECIAL_LOGIC_BUFFS.clear()
    import_calls: list[tuple[str, str | None]] = []

    def fake_import_module(module_name: str, package: str | None = None) -> object:
        import_calls.append((module_name, package))
        raise ModuleNotFoundError(module_name)

    monkeypatch.setattr(buff_class.importlib, "import_module", fake_import_module)
    buff = _buff_with_special_logic("Buff-测试-缺失模块")

    buff.load_special_judge_config()
    buff.load_special_judge_config()

    output = capsys.readouterr().out
    assert len(import_calls) == 1
    assert output.count("未找到 Buff-测试-缺失模块 对应模块，回退到默认逻辑。") == 1
