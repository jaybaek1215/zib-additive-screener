# Autonomous ZIB Electrolyte Discovery — Agent Guidelines & System Context

## 1. Project Overview
This repository implements an end-to-end hierarchical autonomous research pipeline for discovering multifunctional oligomeric electrolyte additives for **Aqueous Zinc-Ion Batteries (ZIBs)**. It integrates **LLM-based Principal Investigator (PI) orchestration**, **RDKit cheminformatics**, and **MatterSim Machine-Learned Interatomic Potential (MLIP)** simulations.

## 2. Core Workflow & Architecture
- **`pi_daemon.py`**: Top-level autonomous daemon managing multi-model LLM fallback (`gemini-3.8-flash-high`, `gpt-oss-120b-medium`, `claude-sonnet-4-6`, `claude-opus-4-6-thinking`) and seamless **0-Token Local Autonomous GPU Mode** when API quotas are exhausted.
- **`PI_DIRECTOR.md`**: Scientific protocols, chemical kill criteria, and token-conservation rules.
- **`generate_library.py`**: Combinatorial oligomer assembly from 25 functional vinyl monomers using RDKit (`connect_monomers`) with physicochemical filtering (MW, LogP, TPSA, HBD).
- **`build_structures.py`**: MMFF94 conformer generation and atomistic assembly of `[Zn(H2O)5(Additive)]2+` solvation clusters and `Zn(0001)` slab adsorption interfaces.
- **`screen_mlip.py`**: MatterSim MLIP geometry relaxation and multi-objective scoring across $\Delta E_{\text{hbond}}$, $\Delta E_{\text{exchange}}$, and $\Delta E_{\text{ads}}$.
- **`run_overnight_batch.py` & `auto_analyze.py`**: Checkpointed batch execution, 3-axis Pareto front extraction, and compact digest generation (`runs/compact_digest.md`).
- **`notify_hook.py` & `slack_reader.py`**: Two-way Slack integration for real-time milestone reporting and human-in-the-loop research steering.

## 3. Strict Operational Rules
1. **Token Conservation:** Never load raw multi-thousand-line CSVs (`runs/master_screening_results.csv`) directly into LLM context. Read `runs/compact_digest.md` and `runs/pi_research_journal.md` instead.
2. **Chemical Validity:** Enforce hydrolytic stability (exclude labile esters such as `DMVP`) and avoid adjacent strong acid repeats ($\ge 2$ sulfonic/phosphonic monomers per oligomer).
3. **Security & Repository Hygiene:** Never commit `.env`, Slack tokens, raw simulation trajectories (`structures/`), or files exceeding 100 MB.
