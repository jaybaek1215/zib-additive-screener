# Autonomous AI-Driven Electrolyte Additive Discovery for Aqueous Zinc-Ion Batteries (ZIBs)

An end-to-end hierarchical autonomous research pipeline combining **Large Language Model (LLM) agents**, **RDKit cheminformatics**, and **Machine-Learned Interatomic Potentials (MatterSim MLIP)** to discover multifunctional oligomeric electrolyte additives for aqueous zinc-ion batteries.

## Key Highlights & Scientific Breakthroughs
- **Hierarchical Multi-Agent Orchestration:** Features an autonomous Principal Investigator (PI) daemon (`pi_daemon.py`) with automatic multi-model fallback and a **0-Token Local Autonomous Mode** that seamlessly transitions to RDKit combinatorial assembly + local GPU MLIP screening when API quotas are exhausted.
- **High-Throughput MLIP Screening:** Automated 3D conformer generation (`build_structures.py`) and atomistic relaxation (`screen_mlip.py`) evaluating three core interfacial descriptors:
  1. **Bulk Water Hydrogen-Bonding Energy ($\Delta E_{\text{hbond}}$):** Suppressing free-water activity and parasitic Hydrogen Evolution Reaction (HER).
  2. **$\text{Zn}^{2+}$ Desolvation Exchange Energy ($\Delta E_{\text{exchange}}$):** Facilitating $\text{Zn}^{2+}$ desolvation kinetics within an optimal thermodynamic window.
  3. **$\text{Zn}(0001)$ Surface Adsorption Energy ($\Delta E_{\text{ads}}$):** Anchoring a protective interfacial layer against dendrite growth.
- **Champion Candidate Discovered (`LIB_0663_VPA-VMO-AM`):**
  - **Architecture:** Multifunctional terpolymer oligomer combining Vinylphosphonic acid (`VPA`, surface anchor), 3-Vinyl-2-oxazolidinone (`VMO`, desolvation mediator), and Acrylamide (`AM`, water-network stabilizer).
  - **Performance:** Achieved a record **Composite Score of 1.8152** ($\Delta E_{\text{hbond}} = -1.2379\text{ eV}$, $\Delta E_{\text{exchange}} = -1.2653\text{ eV}$, $\Delta E_{\text{ads}} = -1.1218\text{ eV}$) across 700+ screened candidates and 26 Pareto-optimal solutions.
- **Two-Way Slack Integration:** Real-time milestone alerts (`notify_hook.py`) and interactive human-in-the-loop research steering (`slack_reader.py`).

## System Architecture
```text
├── pi_daemon.py              # Hierarchical PI loop (LLM Fallback + 0-Token RDKit/GPU Autonomous Mode)
├── PI_DIRECTOR.md            # System protocol, kill criteria, and token-saving guidelines for PI agents
├── generate_library.py       # RDKit SMILES oligomer assembly & physicochemical filtering (MW, LogP, TPSA, HBD)
├── build_structures.py       # MMFF94 3D conformer embedding & Zn(H2O)5 / Zn(0001) interface builder
├── screen_mlip.py            # MatterSim MLIP structural relaxation & multi-objective scoring engine
├── run_overnight_batch.py    # Checkpointed batch execution & 3-axis Pareto front extraction
├── auto_analyze.py           # Automated statistical summary & token-efficient digest generator
├── notify_hook.py            # Outbound Slack Block Kit milestone reporting
└── slack_reader.py           # Inbound Slack directive listener for human-in-the-loop steering
```

## Quick Start

### 1. Environment Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install torch ase rdkit pandas numpy mattersim
```

### 2. Configure Slack Notifications (Optional)
```bash
export RESEARCH_WEBHOOK_URL="[https://hooks.slack.com/services/](https://hooks.slack.com/services/)..."
export SLACK_BOT_TOKEN="xoxb-..."
export SLACK_CHANNEL_ID="C..."
```

### 3. Run Autonomous Screening Loop
```bash
# Single batch execution
python run_overnight_batch.py --pool runs/next_pool.json --batch_size 20 --master_csv runs/master_screening_results.csv

# Continuous autonomous PI daemon
nohup python -u pi_daemon.py >> logs/pi_daemon.log 2>&1 &
```

## Disclaimer
All structural relaxations and binding energies are computed via Machine-Learned Interatomic Potentials (MatterSim) for high-throughput virtual screening and require subsequent DFT/ab-initio MD and electrochemical experimental validation.
