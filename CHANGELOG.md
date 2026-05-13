# Changelog

## 2.0.0

**Breaking (packaging):** The library is split into three installable distributions while keeping import paths stable:

- **`axiompy`** — core (`axiompy.io`, `axiompy.servers`, `axiompy.secrets`, validators, logging, `axiompy-skills`, …).
- **`axiompy-data`** — `axiompy.data` (big-data / data-engineering); depends on `axiompy`.
- **`axiompy-agents`** — `axiompy.reasoning` and `axiompy.agents`; depends on `axiompy` with HTTP/server extras.

`pip install axiompy` alone no longer installs data or agents; add `axiompy-data` and/or `axiompy-agents`, or use extras `pip install "axiompy[data]"`, `"axiompy[agents]"`, or `"axiompy[all]"` when installing from an index that hosts all three wheels.

Repository layout: **`axiompy`**, **`axiompy-data`**, and **`axiompy-agents`** are maintained as **separate Git repositories** (same `axiompy.*` import paths; install the wheels you need from your index).
