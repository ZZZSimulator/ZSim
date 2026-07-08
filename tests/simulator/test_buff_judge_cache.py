from types import SimpleNamespace

from zsim.sim_progress.Buff.BuffLoad import _buff_judge_mission_cache_key


def _mission(tag: str, preload_tick: int, end_tick: int, tick_list: list[int]):
    skill = SimpleNamespace(tick_list=tick_list)
    mission_node = SimpleNamespace(skill=skill)
    return SimpleNamespace(
        mission_node=mission_node,
        mission_tag=tag,
        preload_tick=preload_tick,
        mission_start_tick=preload_tick,
        mission_end_tick=end_tick,
    )


def test_buff_judge_mission_cache_key_uses_stable_mission_identity():
    first = _mission("skill-a", 10, 30, [4, 8])
    equivalent = _mission("skill-a", 10, 30, [4, 8])
    other_skill = _mission("skill-b", 10, 30, [4, 8])
    other_timing = _mission("skill-a", 11, 31, [4, 8])

    assert _buff_judge_mission_cache_key(first) == _buff_judge_mission_cache_key(equivalent)
    assert _buff_judge_mission_cache_key(first) != _buff_judge_mission_cache_key(other_skill)
    assert _buff_judge_mission_cache_key(first) != _buff_judge_mission_cache_key(other_timing)
