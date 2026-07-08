# User Yixuan Astra Trigger Old ZSim Golden

This fixture is copied from `results\原zsim数据` and is the strict external behavior oracle for the Buff hard-cutover campaign.

- Team: `仪玄-耀嘉音-扳机试点队`
- APL: `./zsim/data/APLData/仪玄-耀嘉音-扳机.toml`
- Stop tick: `10800`
- Required domains: `damage`, `damage_attribution`, `buff_timeline`

The matrix row uses `common_cfg.json` instead of the mutable registered team
fixture so weapon refinements, cinemas, drive sets, enemy config, and APL stay
bound to the external user Golden.
