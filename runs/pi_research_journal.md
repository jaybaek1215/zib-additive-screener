# Autonomous Principal Investigator (PI) Research Journal

## Cycle 1 (LLM-Guided Hierarchical Exploration)
- **Hypothesis & Strategy:** Explore heterocyclic carbamate (`VMO`), sulfone (`VSO2`), and fluorinated sulfonamide (`TFMSA`) monomers alongside exhaustive sequence isomers of top-performing phosphonate/acrylamide oligomers (`LIB_0601` ~ `LIB_0660`).
- **Key Findings:**
  - **Champion Breakthrough:** `LIB_0663_VPA-VMO-AM` (`Oligomer(VPA-VMO-AM)`) achieved an all-time record **Composite Score of 1.8152** ($\Delta E_{\text{hbond}} = -1.2379\text{ eV}$, $\Delta E_{\text{exchange}} = -1.2653\text{ eV}$, $\Delta E_{\text{ads}} = -1.1218\text{ eV}$, `PASS`).
  - **Homopolymer Falsification:** Single-monomer trimers (`VPA-VPA-VPA`: 1.3567, `VMO-VMO-VMO`: 1.3348, `TFMSA-TFMSA-TFMSA`: 1.1530) confirmed that synergistic multifunctional triads are essential for high performance.
  - **Kill Criteria Validation:** Excluded hydrolytically labile phosphonate esters (`DMVP`) and sterically hindered bulky sulfonamides (`TFMSA`).

## Cycle 2+ (Hybrid 0-Token RDKit + RTX 3050 MLIP Autonomous Expansion)
- **Hypothesis & Strategy:** Expand combinatorial chemical space across 24 valid vinyl monomers (both trimers and higher-order tetramers) incorporating `VMO`, `VIU` (ethylene urea), `TauMA` (taurine-amide), and `VSL` (sultam) with automated RDKit SMILES assembly and physicochemical pre-filtering.
