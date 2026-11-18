#!/usr/bin/env python3
"""
generate_cycle6_pool.py - Cycle 6 Targeted Cheminformatics Pool Generator

Scientific Mission for Cycle 6:
Leverage the breakthrough insights from Cycle 5:
- Cycle 5 #1: LIB_3183_VSO2-DMA-VPA (Score: 1.7111, dE_ads = -1.210 eV Zn(0001) strong adsorption)
- Cycle 5 #2: LIB_3189_DMA-VSL-VPA (Score: 1.5965, dE_hbond = -1.262 eV record H-bond network disruption)
- Optimal desolvation: LIB_3177_VMO-DMA-VPA (dE_ex = -0.850 eV matching ideal ~ -0.9 eV window)

Design Goal:
Fuse sultam (VSL: unprecedented water-structure disruption), phosphonate (VPA: strong Zn surface
adsorption), sulfone/sulfoxide (VSO2, VSO: high dipole moments), cyclic urea (VIU) and
oxazolidinone (VMO: interfacial buffering and desolvation control), with taurine-amide (TauMA),
tert-amide (DMA), and primary amide (AM) into next-generation Janus oligomers (30 candidates).

Strict Constraints (PI_DIRECTOR.md):
1. Exclude hydrolytically labile esters: DMVP, HEMA.
2. Avoid adjacent strong acid repeats: <= 1 strong acid from {VPA, VSA, AMPS, TauMA, AA}.
3. Pre-filters (RDKit):
   - 200.0 <= MW <= 450.0 Da
   - -0.8 <= LogP <= 1.2
   - TPSA >= 75.0 A^2
   - HBD >= 1
4. Novelty: No duplicate canonical SMILES with runs/master_screening_results.csv.
5. Internal novelty: No duplicates within the Cycle 6 pool.
6. Target composition: 30 candidates (LIB_3207 to LIB_3236), ~70% trimers (21), ~30% tetramers (9).
"""

import os
import json
import argparse
import pandas as pd
from rdkit import Chem
from rdkit.Chem import Descriptors, Crippen, rdMolDescriptors
from generate_library import MONOMERS, connect_monomers

# Chemical rules & filters
STRONG_ACIDS = {'VPA', 'VSA', 'AMPS', 'TauMA', 'AA'}
EXCLUDED_MONOMERS = {'DMVP', 'HEMA'}
MW_MIN, MW_MAX = 200.0, 450.0
LOGP_MIN, LOGP_MAX = -0.8, 1.2
TPSA_MIN = 75.0
HBD_MIN = 1

# Curated candidate pool for Cycle 6 (21 trimers, 9 tetramers)
CURATED_SEQUENCES = [
    # --- Category 1: VSL-VPA Centered Adsorption/H-Bond Trimers (6 Trimers) ---
    ('VPA', 'VSL', 'DMA'),   # Phosphonate surface anchor + Sultam (water breaker) + Tert-amide spacer
    ('DMA', 'VPA', 'VSL'),   # Tert-amide + Central phosphonate anchor + Terminal sultam
    ('VPA', 'VSL', 'AM'),    # Phosphonate anchor + Sultam + Primary amide (strong HBD)
    ('AM', 'VSL', 'VPA'),    # Primary amide + Central sultam + Terminal phosphonate
    ('VPA', 'VSL', 'VSO'),   # Phosphonate + Sultam + Sulfoxide dipole
    ('VSL', 'VPA', 'VSO2'),  # Sultam + Central phosphonate + Sulfone high dipole

    # --- Category 2: VSL-VMO / VSL-VIU Heterocyclic Fusion Trimers (5 Trimers) ---
    ('VIU', 'VSL', 'DMA'),   # Cyclic urea (VIU) + Sultam (VSL) + Tert-amide
    ('DMA', 'VSL', 'VIU'),   # Tert-amide + Central sultam + Cyclic urea
    ('AM', 'VMO', 'VSL'),    # Primary amide + Oxazolidinone (VMO) + Sultam (VSL)
    ('AM', 'VSL', 'VIU'),    # Primary amide + Central sultam + Cyclic urea
    ('VIU', 'VSL', 'VMO'),   # Dual heterocyclic fusion (VIU + VMO) bridged by Sultam

    # --- Category 3: VSO2/VSO - Heterocycle - Amide Trimers (5 Trimers) ---
    ('VSO2', 'VIU', 'DMA'),  # Sulfone dipole + Cyclic urea + Tert-amide
    ('VSO2', 'VIU', 'VPA'),  # Sulfone dipole + Cyclic urea + Phosphonate anchor
    ('VSO2', 'VSL', 'AM'),   # Sulfone dipole + Sultam + Primary amide
    ('VSO', 'AM', 'VSL'),    # Sulfoxide dipole + Primary amide spacer + Sultam
    ('VSO2', 'VMO', 'AM'),   # Sulfone dipole + Oxazolidinone + Primary amide

    # --- Category 4: TauMA-Based Sulfonamide Trimers (5 Trimers) ---
    ('DMA', 'TauMA', 'VSL'), # Tert-amide + Taurine-amide + Sultam dual-sulfonamide hybrid
    ('DMA', 'VSL', 'TauMA'), # Tert-amide + Central sultam + Taurine-amide
    ('VSO', 'VSL', 'TauMA'), # Sulfoxide dipole + Sultam + Taurine-amide
    ('DMA', 'TauMA', 'VMO'), # Tert-amide + Taurine-amide + Oxazolidinone
    ('VIU', 'TauMA', 'DMA'), # Cyclic urea + Taurine-amide + Tert-amide

    # --- Category 5: 4-Way Higher-Order Synergy Tetramers (9 Tetramers) ---
    ('VSL', 'VPA', 'DMA', 'AM'),   # Sultam + Phosphonate + DMA + AM quadruple synergy
    ('VSL', 'DMA', 'AM', 'VPA'),   # Sultam + DMA + AM + Terminal phosphonate anchor
    ('VSL', 'VSO2', 'DMA', 'AM'),  # Sultam + Sulfone dipole + DMA + AM
    ('VSO2', 'VSL', 'DMA', 'AM'),  # Sulfone + Central sultam + DMA + AM regioisomer
    ('VSL', 'VSO', 'DMA', 'AM'),   # Sultam + Sulfoxide dipole + DMA + AM
    ('VIU', 'VSL', 'DMA', 'AM'),   # Cyclic urea + Sultam + DMA + AM
    ('VMO', 'VSL', 'DMA', 'AM'),   # Oxazolidinone + Sultam + DMA + AM
    ('VSO2', 'VMO', 'DMA', 'VPA'), # Sulfone + Oxazolidinone + DMA + Phosphonate anchor
    ('VIU', 'VMO', 'DMA', 'VPA'),  # Cyclic urea + Oxazolidinone + DMA + Phosphonate anchor
]


def load_master_smiles(master_csv_path='runs/master_screening_results.csv'):
    """Load existing SMILES from master screening results to ensure novelty."""
    if not os.path.exists(master_csv_path):
        print(f"Warning: {master_csv_path} not found. Assuming empty master library.")
        return set()
    df = pd.read_csv(master_csv_path)
    existing = set(df['smiles'].dropna().tolist())
    print(f"Loaded {len(existing)} existing candidate SMILES from {master_csv_path}")
    return existing


def generate_cycle6_candidates(start_id=3207, master_csv_path='runs/master_screening_results.csv'):
    existing_smiles = load_master_smiles(master_csv_path)
    candidates = []
    seen_internal_smiles = set()

    for idx, combo in enumerate(CURATED_SEQUENCES):
        cand_id = f"LIB_{start_id + idx}"
        name = f"{cand_id}_{'-'.join(combo)}"

        # 1. Kill Criteria: Labile esters
        for m in combo:
            if m in EXCLUDED_MONOMERS:
                raise ValueError(f"Candidate {name} contains prohibited monomer {m}")

        # 2. Kill Criteria: Strong acid repeats
        sa_count = sum(1 for m in combo if m in STRONG_ACIDS)
        if sa_count > 1:
            raise ValueError(f"Candidate {name} contains {sa_count} strong acids (max allowed: 1)")

        # 3. Sequential RDKit assembly
        smiles_list = [MONOMERS[m]['smiles'] for m in combo]
        canonical_smiles = connect_monomers(smiles_list)
        if not canonical_smiles:
            raise RuntimeError(f"Candidate {name} failed RDKit dummy-atom coupling")

        # 4. Novelty checks
        if canonical_smiles in existing_smiles:
            raise ValueError(f"Candidate {name} SMILES already exists in master screening results!")
        if canonical_smiles in seen_internal_smiles:
            raise ValueError(f"Candidate {name} SMILES duplicate within Cycle 6 pool!")
        seen_internal_smiles.add(canonical_smiles)

        # 5. Physicochemical property checks
        mol = Chem.MolFromSmiles(canonical_smiles)
        if not mol:
            raise RuntimeError(f"Failed to parse SMILES for {name}")

        mw = Descriptors.ExactMolWt(mol)
        logp = Crippen.MolLogP(mol)
        tpsa = rdMolDescriptors.CalcTPSA(mol)
        hbd = rdMolDescriptors.CalcNumHBD(mol)

        if not (MW_MIN <= mw <= MW_MAX):
            raise ValueError(f"{name} MW {mw:.2f} out of bounds [{MW_MIN}, {MW_MAX}]")
        if not (LOGP_MIN <= logp <= LOGP_MAX):
            raise ValueError(f"{name} LogP {logp:.2f} out of bounds [{LOGP_MIN}, {LOGP_MAX}]")
        if not (tpsa >= TPSA_MIN):
            raise ValueError(f"{name} TPSA {tpsa:.2f} below threshold {TPSA_MIN}")
        if not (hbd >= HBD_MIN):
            raise ValueError(f"{name} HBD {hbd} below threshold {HBD_MIN}")

        functional_groups = ", ".join([MONOMERS[m]['group'] for m in combo])

        candidates.append({
            "id": cand_id,
            "name": name,
            "backbone": "Poly(vinyl/acrylic)",
            "functional_groups": functional_groups,
            "mol_weight": round(mw, 2),
            "logp": round(logp, 2),
            "tpsa": round(tpsa, 2),
            "hbd": int(hbd),
            "smiles": canonical_smiles,
            "monomers": list(combo)
        })

    return candidates


def main():
    parser = argparse.ArgumentParser(description="Generate Cycle 6 Candidate Pool")
    parser.add_argument("--start_id", type=int, default=3207, help="Starting ID (default: 3207)")
    parser.add_argument("--out", default="runs/cycle6_pool.json", help="Output JSON path")
    parser.add_argument("--master", default="runs/master_screening_results.csv", help="Master CSV path")
    args = parser.parse_args()

    candidates = generate_cycle6_candidates(start_id=args.start_id, master_csv_path=args.master)
    print(f"Generated {len(candidates)} valid candidates (IDs: {candidates[0]['id']} to {candidates[-1]['id']})")

    trimers = [c for c in candidates if len(c['monomers']) == 3]
    tetramers = [c for c in candidates if len(c['monomers']) == 4]
    print(f"Oligomer Breakdown: {len(trimers)} trimers ({len(trimers)/len(candidates)*100:.1f}%), "
          f"{len(tetramers)} tetramers ({len(tetramers)/len(candidates)*100:.1f}%)")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(candidates, f, indent=2)

    print(f"Successfully saved {len(candidates)} candidates to {args.out}")


if __name__ == "__main__":
    main()
