# No global mutable event bus for the simulation engine

Status: accepted

The event-driven simulation engine will use explicit SimulationEvent contracts, subsystem ports, and a controlled dispatcher rather than a global mutable EventBus that any module can publish to or subscribe from. This keeps cross-system dependencies enumerable and testable, preserves SOLID boundaries, and prevents the hard cutover from replacing per-tick coupling with hidden event coupling.
