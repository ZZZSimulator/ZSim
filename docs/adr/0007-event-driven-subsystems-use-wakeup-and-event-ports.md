# Event-driven subsystems use wakeup and event ports

Status: accepted

Event-Driven Simulation Advancement will decouple simulator subsystems through explicit Wakeup Source contracts, subsystem owners, narrow read/write ports, and structured behavior events. The Simulation Clock may ask each subsystem for its next wakeup tick but must not understand subsystem internals, and production code must not reintroduce raw old-container discovery or rely on implicit per-tick calls as a hidden dependency.
