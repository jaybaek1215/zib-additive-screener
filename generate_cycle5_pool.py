#!/usr/bin/env python3
"""
generate_cycle5_pool.py - Cycle 5 Targeted Cheminformatics Pool Generator

Scientific Mission for Cycle 5:
Enhance water-structure disruption (driving dE_hbond < -1.1 eV) while retaining strong
Zn(0001) surface adsorption (dE_ads < -1.2 eV) and optimal desolvation kinetics
(dE_ex ~ -0.9 eV) by optimizing heterocyclic oxazolidinone (VMO), sulfoxide/sulfone
(VSO, VSO2), ethylene urea (VIU), sultam (VSL), and taurine (TauMA) hybrid sequences
with DMA, AM, VPA, and TFEMA.

Strict Constraints:
1. Exclude hydrolytically labile esters: DMVP, HEMA.
2. Avoid adjacent strong acid repeats: <= 1 strong acid from {VPA, VSA, AMPS, TauMA, AA}.
3. Pre-filters:
   - 200.0 <= MW <= 450.0 Da
   - -0.8 <= LogP <= 1.2
   - TPSA >= 75.0 A^2
   - HBD >= 1
4. Novelty: No duplicate SMILES with runs/master_screening_results.csv.
5. Exactly 30 candidates (LIB_3177 to LIB_3206).
6. Composition: ~70% trimers (21), ~30% tetramers (9).
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

# Curated candidate pool for Cycle 5 (21 trimers, 9 tetramers)
CURATED_SEQUENCES = [
    # --- Category 1: Oxazolidinone (VMO) Hybrids (4 Trimers) ---
    ('VMO', 'DMA', 'VPA'),      # Oxazolidinone + Tert-amide + Phosphonate anchor
    ('VMO', 'DMA', 'VIU'),      # Oxazolidinone + Tert-amide + Ethylene Urea
    ('VMO', 'VPA', 'VSO'),      # Oxazolidinone + Phosphonate + Sulfoxide dipole
    ('VMO', 'VPA', 'VSO2'),     # Oxazolidinone + Phosphonate + Sulfone dipole

    # --- Category 2: Sulfoxide & Sulfone (VSO, VSO2) Hybrids (4 Trimers) ---
    ('VSO', 'VPA', 'DMA'),      # Sulfoxide + Phosphonate anchor + Tert-amide
    ('VSO', 'VSO2', 'VPA'),     # Sulfoxide + Sulfone dual S-oxide + Phosphonate
    ('VSO2', 'DMA', 'VPA'),     # Sulfone + Tert-amide + Phosphonate
    ('VSO2', 'DMA', 'VIU'),     # Sulfone + Tert-amide + Ethylene Urea

    # --- Category 3: Ethylene Urea (VIU) Hybrids (4 Trimers) ---
    ('DMA', 'VIU', 'VPA'),      # Tert-amide spacer + Cyclic Urea + Phosphonate
    ('VIU', 'AM', 'DMA'),       # Cyclic Urea + Primary Amide + Tert-amide
    ('VIU', 'VSO2', 'DMA'),     # Cyclic Urea + Sulfone + Tert-amide
    ('VIU', 'TFEMA', 'AM'),     # Cyclic Urea + Fluorinated barrier + Primary Amide

    # --- Category 4: Sultam (VSL) Hybrids (4 Trimers) ---
    ('DMA', 'VSL', 'VPA'),      # Tert-amide + Sultam heterocycle + Phosphonate
    ('VSL', 'DMA', 'AM'),       # Sultam + Tert-amide + Primary Amide
    ('AM', 'VSL', 'VMO'),       # Primary Amide + Sultam + Oxazolidinone
    ('TFEMA', 'VSL', 'AM'),     # Fluorinated barrier + Sultam + Primary Amide

    # --- Category 5: Taurine (TauMA) Hybrids (5 Trimers) ---
    ('TauMA', 'DMA', 'VMO'),    # Taurine sulfonic-amide + Tert-amide + Oxazolidinone
    ('TauMA', 'TFEMA', 'VSO'),  # Taurine + Fluorinated barrier + Sulfoxide
    ('TauMA', 'TFEMA', 'VIU'),  # Taurine + Fluorinated barrier + Ethylene Urea
    ('VSO', 'DMA', 'TauMA'),    # Sulfoxide + Tert-amide + Taurine
    ('DMA', 'VIU', 'TauMA'),    # Tert-amide + Ethylene Urea + Taurine

    # --- Category 6: Higher-Order Multi-Objective Tetramers (9 Tetramers) ---
    ('VMO', 'DMA', 'AM', 'VPA'),   # Quadruple synergy: VMO + Tert-amide + AM + Phosphonate
    ('VSO', 'VMO', 'DMA', 'AM'),   # Sulfoxide + Oxazolidinone + Tert-amide + Primary Amide
    ('VSO2', 'VMO', 'DMA', 'AM'),  # Sulfone + Oxazolidinone + Tert-amide + Primary Amide
    ('VIU', 'VMO', 'DMA', 'AM'),   # Ethylene Urea + Oxazolidinone + Tert-amide + Primary Amide
    ('VSL', 'VMO', 'DMA', 'AM'),   # Sultam + Oxazolidinone + Tert-amide + Primary Amide
    ('TFEMA', 'VMO', 'DMA', 'AM'), # Hydrophobic fluorinated barrier + VMO + DMA + AM
    ('TFEMA', 'VIU', 'DMA', 'AM'), # Hydrophobic fluorinated barrier + VIU + DMA + AM
    ('TFEMA', 'VSO', 'DMA', 'AM'), # Hydrophobic fluorinated barrier + VSO + DMA + AM
    ('VPA', 'VSL', 'DMA', 'AM'),   # Phosphonate surface anchor + Sultam + DMA + AM
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


def generate_cycle5_candidates(start_id=3177, master_csv_path='runs/master_screening_results.csv'):
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
            raise ValueError(f"Candidate {name} SMILES duplicate within Cycle 5 pool!")
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
    parser = argparse.ArgumentParser(description="Generate Cycle 5 Candidate Pool")
    parser.add_argument("--start_id", type=int, default=3177, help="Starting ID (default: 3177)")
    parser.add_argument("--out", default="runs/next_pool.json", help="Output JSON path")
    parser.add_argument("--master", default="runs/master_screening_results.csv", help="Master CSV path")
    args = parser.parse_args()

    candidates = generate_cycle5_candidates(start_id=args.start_id, master_csv_path=args.master)
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
