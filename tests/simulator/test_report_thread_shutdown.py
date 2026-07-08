import queue
from csv import DictReader
from pathlib import Path

import zsim.sim_progress.Report as Report
import zsim.sim_progress.Report.result_handler as result_handler
from zsim.sim_progress.Report.log_handler import log_queue
from zsim.sim_progress.Report.result_handler import result_queue


def _drain_queue(target_queue: queue.Queue) -> None:
    while True:
        try:
            target_queue.get_nowait()
        except queue.Empty:
            return
        target_queue.task_done()


def _assert_report_loop_stopped() -> None:
    loop = Report.__dict__.get("__event_loop")
    loop_thread = Report.__dict__.get("__loop_thread")

    assert loop is None
    assert loop_thread is None or not loop_thread.is_alive()


def test_damage_record_buffer_preserves_base_order_and_appends_extras(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "damage.csv"
    buffer = result_handler.DamageRecordBuffer()

    buffer.add(
        {
            "tick": 1,
            "skill_tag": "alpha",
            "first_extra": "a",
            "UUID": "uuid-1",
        }
    )
    buffer.add(
        {
            "tick": 2,
            "skill_tag": "beta",
            "second_extra": "b",
            "first_extra": "c",
        }
    )

    buffer.flush(str(csv_path))

    with csv_path.open(newline="", encoding="utf-8-sig") as file:
        reader = DictReader(file)
        assert reader.fieldnames == [
            *result_handler._BASE_FIELDNAMES,
            "first_extra",
            "second_extra",
        ]


def test_report_dmg_result_flushes_damage_csv_once_on_stop(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(result_handler, "DEBUG", True)
    _drain_queue(log_queue)
    _drain_queue(result_queue)
    Report._stop_async_tasks()

    writes: list[tuple[str, list[dict], list[str]]] = []
    original_write_damage_csv = result_handler._write_damage_csv

    def spy_write_damage_csv(
        report_file_path: str, records: list[dict], fieldnames: list[str]
    ) -> None:
        writes.append((report_file_path, list(records), list(fieldnames)))
        original_write_damage_csv(report_file_path, records, fieldnames)

    monkeypatch.setattr(result_handler, "_write_damage_csv", spy_write_damage_csv)

    try:
        Report.start_report_threads(None, session_id="session-buffer")
        Report.report_dmg_result(tick=1, skill_tag="alpha", UUID="uuid-1")
        Report.report_dmg_result(tick=2, skill_tag="beta", UUID="uuid-2")

        result_queue.join()

        csv_path = tmp_path / "results" / "session-buffer" / "damage.csv"
        assert writes == []
        assert not csv_path.exists()

        Report.stop_report_threads()

        assert len(writes) == 1
        assert [record["tick"] for record in writes[0][1]] == [1, 2]
        assert csv_path.exists()
    finally:
        Report._stop_async_tasks()
        _drain_queue(log_queue)
        _drain_queue(result_queue)


def test_report_dmg_result_debug_false_enqueues_nothing(monkeypatch) -> None:
    _drain_queue(result_queue)
    monkeypatch.setattr(result_handler, "DEBUG", False)

    Report.report_dmg_result(tick=1, skill_tag="alpha", UUID="uuid-1")

    assert result_queue.empty()


def test_report_dmg_result_preserves_legacy_disorder_skill_tag(monkeypatch) -> None:
    _drain_queue(result_queue)
    monkeypatch.setattr(result_handler, "DEBUG", True)

    Report.report_dmg_result(
        tick=1,
        element_type=3,
        is_anomaly=True,
        is_disorder=True,
        UUID="uuid-1",
    )

    record = result_queue.get_nowait()
    try:
        assert record["skill_tag"] == "感电紊乱"
        assert record["UUID"] == "uuid-1"
        assert "dmg_crit" in record
    finally:
        result_queue.task_done()


def test_stop_report_threads_drains_async_writers_and_allows_restart(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(result_handler, "DEBUG", True)
    _drain_queue(log_queue)
    _drain_queue(result_queue)
    Report._stop_async_tasks()

    try:
        Report.start_report_threads(None, session_id="session-a")
        log_queue.put("first log line")
        Report.report_dmg_result(tick=1, skill_tag="alpha", UUID="uuid-1")

        Report.stop_report_threads()

        session_a_log = (tmp_path / "logs" / "session-a.log").read_text(encoding="utf-8").strip()
        assert session_a_log == "first log line"
        assert (tmp_path / "results" / "session-a" / "damage.csv").exists()
        _assert_report_loop_stopped()

        Report.start_report_threads(None, session_id="session-b")
        log_queue.put("second log line")

        Report.stop_report_threads()

        session_b_log = (tmp_path / "logs" / "session-b.log").read_text(encoding="utf-8").strip()
        assert session_b_log == "second log line"
        assert not (tmp_path / "results" / "session-b" / "damage.csv").exists()
        _assert_report_loop_stopped()
    finally:
        Report._stop_async_tasks()
        _drain_queue(log_queue)
        _drain_queue(result_queue)
