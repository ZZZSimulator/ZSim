# Event-driven advancement keeps integer tick time

Status: accepted

ZSim will pursue Event-Driven Simulation Advancement by changing how the simulator advances to the next behavior-relevant tick, not by replacing integer tick semantics with continuous time. Simulation Tick remains the global truth for ordering, Buff duration, cooldowns, response windows, DOT/anomaly timing, and golden parity; the new Simulation Clock owns advancement so systems can be decoupled without weakening tick-based behavior contracts.
