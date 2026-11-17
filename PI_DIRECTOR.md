# Autonomous Principal Investigator (PI) Research Protocol

## 1. Mission & Scientific Objective
Design and validate multifunctional oligomeric electrolyte additives for **Aqueous Zinc-Ion Batteries (ZIBs)** using high-throughput **MatterSim Machine-Learned Interatomic Potential (MLIP)** simulations. Optimize three synergistic interfacial descriptors:
- **Water Activity Suppression ($\Delta E_{\text{hbond}}$):** Strong hydrogen-bonding network disruption to inhibit parasitic Hydrogen Evolution Reaction (HER).
- **$\text{Zn}^{2+}$ Desolvation Kinetics ($\Delta E_{\text{exchange}}$):** Balanced ligand-exchange energetics near the optimal $-0.9\text{ eV}$ window.
- **Surface Protection ($\Delta E_{\text{ads}}$):** Strong chemisorption onto $\text{Zn}(0001)$ surfaces without inducing passivating impedance.

## 2. Token-Efficiency & Context Rules
- **Never** read raw multi-thousand-line CSVs directly into LLM context.
- Rely exclusively on `runs/compact_digest.md` and `runs/pi_research_journal.md` for historical state.
- Delegate candidate library generation and cheminformatics pre-filtering to lightweight worker scripts (`generate_library.py`).

## 3. Chemical Kill Criteria & Constraints
1. **Hydrolytic Stability:** Exclude labile ester backbones (e.g., DMVP) prone to hydrolysis in locally alkaline interfacial environments.
2. **Steric & Electrostatic Balance:** Avoid adjacent strong sulfonic/phosphonic acid repeats ($\ge 2$ strong acid monomers per trimer) to prevent severe steric hindrance and convergence failures on $\text{Zn}(0001)$.
3. **Experimental Synthesizability:** Prioritize commercially accessible vinyl monomers amenable to free-radical or RAFT oligomerization.
