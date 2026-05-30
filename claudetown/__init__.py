"""ClaudeTown -- a persistent, generative town that grows across sessions.

The simulation is pure Python standard library and fully deterministic from a
seed, so the town's entire history lives in version control and can be trusted
to unfold the same way every time it is replayed.

Modules:
    data        -- static vocabulary (names, traits, buildings, calendar)
    world       -- world creation, persistence, and date helpers
    simulation  -- the monthly tick that evolves the town
    chronicle   -- prose rendering of each month's events
    render      -- export to the web viewer and README stats
    cli         -- the command-line interface
"""

__version__ = "0.1.0"
