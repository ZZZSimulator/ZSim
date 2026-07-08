from __future__ import annotations

from zsim.sim_progress.data_struct.planned_queue import PlannedEventQueue


class _ExecuteTickEvent:
    def __init__(self, execute_tick: int) -> None:
        self.execute_tick = execute_tick


class _PreloadTickEvent:
    def __init__(self, preload_tick: int) -> None:
        self.preload_tick = preload_tick


class _ImmediateEvent:
    pass


def _queue(events: list[object]) -> PlannedEventQueue:
    return PlannedEventQueue(
        get_events=lambda: events,
        set_events=lambda new_events: events.__setitem__(slice(None), new_events),
    )


def test_planned_event_queue_reports_next_future_due_tick() -> None:
    planned_queue = _queue(
        [
            _ExecuteTickEvent(30),
            _PreloadTickEvent(12),
            _ExecuteTickEvent(20),
        ]
    )

    assert planned_queue.next_due_tick(after_tick=10) == 12


def test_planned_event_queue_wakes_next_tick_for_stale_due_event() -> None:
    planned_queue = _queue([_ExecuteTickEvent(10), _ExecuteTickEvent(30)])

    assert planned_queue.next_due_tick(after_tick=10) == 11


def test_planned_event_queue_wakes_next_tick_for_immediate_event() -> None:
    planned_queue = _queue([_ImmediateEvent(), _ExecuteTickEvent(30)])

    assert planned_queue.next_due_tick(after_tick=10) == 11


def test_planned_event_queue_accepts_custom_execute_tick_resolver() -> None:
    planned_queue = _queue([{"tick": 25}, {"tick": 18}])

    assert (
        planned_queue.next_due_tick(
            after_tick=10,
            execute_tick_resolver=lambda event: event["tick"],  # type: ignore[index]
        )
        == 18
    )


def test_planned_event_queue_due_tick_tracks_owner_mutations() -> None:
    events: list[object] = [_ExecuteTickEvent(30)]
    planned_queue = _queue(events)

    planned_queue.enqueue(_ExecuteTickEvent(18))
    assert planned_queue.next_due_tick(after_tick=10) == 18

    first_due = events[1]
    planned_queue.remove(first_due)
    assert planned_queue.next_due_tick(after_tick=10) == 30

    planned_queue.replace([_ExecuteTickEvent(22), _ExecuteTickEvent(16)])
    assert planned_queue.next_due_tick(after_tick=10) == 16

    planned_queue.clear()
    assert planned_queue.next_due_tick(after_tick=10) is None
