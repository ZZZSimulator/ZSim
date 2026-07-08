# Damage Report Buffer And BuffLoad Candidate Index

## Context

The DEBUG path for `仪玄-耀嘉音-扳机试点队` at `stop_tick=10800` spends too much time in report and BuffLoad work. `damage.csv` was being rewritten from the full in-memory record list after every damage record, creating O(n^2) file output. The existing indexed BuffLoad opt-in preserved behavior but still scanned the same candidate set as the default loop.

External Behavior is unchanged: `damage.csv`, `damage_attribution.json`, and `buff_log/buff_timeline_data.json` remain the public result artifacts, and the User Golden Result Baseline remains the parity oracle.

## Decision

`damage.csv` is a Damage Report Artifact. The Report module collects records in a Damage Record Buffer and flushes the completed CSV once during report shutdown after the queue is drained. Running-time progressive readability of `damage.csv` is not part of the contract.

BuffLoad v1 uses a conservative Buff Load Candidate Index. The index may classify only static facts that do not require executing Buff behavior: owner, foreground/background eligibility, `schedule_judge`, `passively_updating`, `backend_acitve`, and simple judge fields. Complex XLogic, uncertain rows, and candidates without safe static classification stay in the Fallback Candidate Pool.

`BuffJudge` remains final authority. The index selects candidates to evaluate; it does not directly activate, skip, or mutate Buff behavior based on its own result.

## Consequences

Report shutdown now owns final `damage.csv` materialization, which removes per-record rewrite cost while preserving the final file shape.

BuffLoad metrics distinguish full-scan candidates from selected, skipped, and fallback candidates. Successfully skipped candidates are not candidate mismatches; candidate mismatch remains a correctness signal.

The CLI indexed BuffLoad flag remains a comparison and rollback entrypoint. WebUI/API default enablement is gated by Golden parity, candidate correctness metrics, and the 10800 tick benchmark target.
