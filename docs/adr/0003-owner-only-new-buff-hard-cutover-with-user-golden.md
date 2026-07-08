# Owner-Only New Buff Hard Cutover With User Golden

We will finish the Buff refactor by hard-cutting production and public contracts to the Owner-Only New Buff Runtime. Old Buff Container fallback is no longer an acceptable compatibility layer: runtime behavior must flow through runtime owners, facades, read ports, write ports, and planned-event queue owners.

External Behavior remains mandatory. Instead of keeping a live old-system runtime path, parity is checked against a User Golden Result Baseline copied from `results\原zsim数据` into tracked external-golden fixtures. That fixture represents `仪玄-耀嘉音-扳机试点队` at `stop_tick=10800` and must compare exactly after normalization for damage, damage attribution, and Buff timeline outputs.

The result file shape remains stable for downstream analysis: `damage.csv`, `damage_attribution.json`, and `buff_log/buff_timeline_data.json` continue to be produced and compared. Data-analysis reports must use new Buff terminology and remove `legacy_runtime` aliases rather than describing a live old-vs-new runtime switch.
