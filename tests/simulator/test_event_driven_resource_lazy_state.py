from __future__ import annotations

from types import SimpleNamespace

from zsim.sim_progress.Character.character import Character
from zsim.sim_progress.Character.wakeup import (
    CharacterResourceThresholds,
    CharacterResourceWakeupSource,
)
from zsim.sim_progress.Character.Yixuan import Yixuan
from zsim.sim_progress.Character.Yixuan.AdrenalineEventClass import AuricArray
from zsim.sim_progress.data_struct import SPUpdateData
from zsim.sim_progress.data_struct.enemy_special_state_manager.special_classes import (
    SweetScare,
)


def _sp_update_data(char_name: str, regen: float) -> SPUpdateData:
    data = SPUpdateData.__new__(SPUpdateData)
    data.char_name = char_name
    data.get_sp_regen = lambda: regen  # type: ignore[method-assign]
    return data


def test_character_batches_skipped_tick_sp_regen() -> None:
    char = Character.__new__(Character)
    char.NAME = "alpha"
    char.sp = 0.0
    char.sp_limit = 100
    char.sim_instance = SimpleNamespace(_event_driven_elapsed_ticks=5)

    char.update_sp_overtime((_sp_update_data("alpha", 60.0),), {})

    assert char.sp == 5.0


def test_character_resource_wakeup_uses_next_integer_energy_boundary() -> None:
    char = Character.__new__(Character)
    char.sp = 40.5
    char.sp_limit = 100
    char.statement = SimpleNamespace(sp_regen=30.0)

    assert char.next_resource_wakeup_tick(10) == 12


def test_character_resource_wakeup_uses_apl_energy_threshold() -> None:
    char = Character.__new__(Character)
    char.sp = 40.5
    char.sp_limit = 100
    char.statement = SimpleNamespace(sp_regen=30.0)

    assert (
        char.next_resource_wakeup_tick(
            10,
            thresholds=CharacterResourceThresholds(energy=(60.0,)),
        )
        == 50
    )


def test_character_resource_wakeup_uses_next_preload_visible_threshold_tick() -> None:
    char = Character.__new__(Character)
    char.sp = 59.595
    char.sp_limit = 120
    char.statement = SimpleNamespace(sp_regen=1.2)

    assert (
        char.next_resource_wakeup_tick(
            637,
            thresholds=CharacterResourceThresholds(energy=(60.0,)),
        )
        == 659
    )


def test_character_resource_wakeup_keeps_recently_crossed_threshold_visible() -> None:
    char = Character.__new__(Character)
    char.sp = 60.015
    char.sp_limit = 120
    char.statement = SimpleNamespace(sp_regen=1.2)

    assert (
        char.next_resource_wakeup_tick(
            3658,
            thresholds=CharacterResourceThresholds(energy=(60.0,)),
        )
        == 3659
    )


def test_yixuan_batches_skipped_tick_adrenaline_regen() -> None:
    char = Yixuan.__new__(Yixuan)
    char.NAME = "仪玄"
    char.adrenaline = 10.0
    char.adrenaline_limit = 120
    char.sim_instance = SimpleNamespace(
        tick=20,
        _event_driven_elapsed_ticks=30,
    )
    char._Yixuan__adrenaline_recover_overtime_update_tick = 0

    char.update_sp_overtime((_sp_update_data("仪玄", 0.0),), {})

    assert char.adrenaline == 11.0


def test_yixuan_skipped_refresh_does_not_block_current_tick_refresh() -> None:
    char = Yixuan.__new__(Yixuan)
    char.NAME = "仪玄"
    char.adrenaline = 10.0
    char.adrenaline_limit = 120
    char.sim_instance = SimpleNamespace(
        tick=20,
        _event_driven_elapsed_ticks=2,
        _event_driven_skipped_refresh=True,
    )
    char._Yixuan__adrenaline_recover_overtime_update_tick = 19

    char.update_sp_overtime((_sp_update_data("仪玄", 0.0),), {})
    char.sim_instance._event_driven_elapsed_ticks = 1
    char.sim_instance._event_driven_skipped_refresh = False
    char.update_sp_overtime((_sp_update_data("仪玄", 0.0),), {})

    assert round(char.adrenaline, 6) == round(10.0 + 3 * (2 / 60), 6)


def test_yixuan_active_adrenaline_event_keeps_next_tick_wakeup() -> None:
    char = Yixuan.__new__(Yixuan)
    char.adrenaline = 10.0
    char.adrenaline_limit = 120
    char.adrenaline_manager = SimpleNamespace(
        adrenaline_recover_event_group=[SimpleNamespace(active=True)]
    )

    assert char.next_resource_wakeup_tick(100) == 101


def test_yixuan_batches_skipped_active_adrenaline_event() -> None:
    char = SimpleNamespace(
        sim_instance=SimpleNamespace(
            tick=20,
            _event_driven_elapsed_ticks=5,
            _event_driven_skipped_refresh=True,
        ),
        update_adrenaline=lambda value: setattr(
            char,
            "adrenaline",
            char.adrenaline + value,
        ),
        adrenaline=10.0,
    )
    event = AuricArray(char)
    event.active = True
    event.last_active_tick = 10

    event.check_myself()

    assert round(char.adrenaline, 6) == round(10.0 + 5 * (7 / 60), 6)
    assert event.active is True


def test_yixuan_active_adrenaline_event_uses_threshold_wakeup() -> None:
    char = Yixuan.__new__(Yixuan)
    char.adrenaline = 10.0
    char.adrenaline_limit = 120
    char.adrenaline_manager = SimpleNamespace(
        adrenaline_recover_event_group=[
            SimpleNamespace(
                active=True,
                last_active_tick=0,
                max_duration=180,
                regenerate_value=7 / 60,
            )
        ]
    )

    assert (
        char.next_resource_wakeup_tick(
            10,
            thresholds=CharacterResourceThresholds(special_resource=(20.0,)),
        )
        == 78
    )


def test_character_resource_wakeup_source_uses_earliest_character_tick() -> None:
    source = CharacterResourceWakeupSource(
        [
            SimpleNamespace(next_resource_wakeup_tick=lambda current_tick: current_tick + 30),
            SimpleNamespace(next_resource_wakeup_tick=lambda current_tick: current_tick + 5),
        ]
    )

    assert source.next_wakeup_tick(10) == 15


def test_character_resource_wakeup_source_passes_matching_cid_thresholds() -> None:
    seen = {}

    def next_resource_wakeup_tick(
        current_tick: int,
        *,
        thresholds: CharacterResourceThresholds | None = None,
    ) -> int:
        seen["thresholds"] = thresholds
        return current_tick + 7

    source = CharacterResourceWakeupSource(
        [SimpleNamespace(CID=1371, next_resource_wakeup_tick=next_resource_wakeup_tick)],
        thresholds_by_cid={
            1371: CharacterResourceThresholds(special_resource=(60.0,)),
        },
    )

    assert source.next_wakeup_tick(10) == 17
    assert seen["thresholds"] == CharacterResourceThresholds(special_resource=(60.0,))


def test_sweet_scare_wakeup_uses_next_sugarburst_tick() -> None:
    state = SweetScare.__new__(SweetScare)
    state.active = True
    state.last_update_tick = 100
    state.max_duration = 2400
    state.sugarburst_sparkless_update_tick = 284
    state.sugarburst_sparkless_cd = 60

    assert state.next_wakeup_tick(300) == 344
