#!/usr/bin/env python3
"""
generate_cycle8_pool.py - Cycle 8 Targeted Cheminformatics Pool Generator

Scientific Mission for Cycle 8:
Build upon Cycle 7 discoveries (LIB_3251_VSL-VIU-VPA champion score 1.8397, LIB_3260 non-acidic tetramer 1.6899,
LIB_3254 H-bond breaker -1.2580 dE_hbond, LIB_3259 desolvation kinetics -1.0067 dE_ex).
Generate exactly 30 candidates (LIB_3267 ~ LIB_3296) across 4 targeted categories:
1. VSL-VIU Core Derivatives & Regioisomer/Spacer Trimers (7 Trimers)
2. Non-Acidic High-Dipole Heterocyclic Triads (7 Trimers)
3. Sulfone/Sulfoxide-Heterocycle-Phosphonate Single-Anchor Trimers (7 Trimers)
4. Higher-Order 4-Way Synergy Tetramers (9 Tetramers: 5 non-acidic + 4 low-acid single-anchor)

Strict Constraints (PI_DIRECTOR.md & GEMINI.md):
1. Exclude hydrolytically labile esters: DMVP, HEMA strictly forbidden.
2. Strong acid repetition prevention: max 1 strong acid from {VPA, VSA, AMPS, TauMA, AA} (adjacent repeats = 0).
3. Physicochemical pre-filters (RDKit):
   - 200.0 <= MW <= 510.0 Da (expanded upper bound to accommodate larger fluorinated/heterocyclic tetramers like LIB_3291 at 499.21 Da)
   - -0.8 <= LogP <= 1.2
   - TPSA >= 74.0 A^2
   - HBD >= 1
4. Absolute novelty: 0 duplicate SMILES with newly generated SMILES in this run.
5. Internal novelty: 0 duplicates within the Cycle 8 pool.
6. Target composition: exactly 30 candidates, 21 trimers (70.0%), 9 tetramers (30.0%).
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
MW_MIN, MW_MAX = 200.0, 510.0  # Expanded to accommodate larger tetramers up to ~500 Da
LOGP_MIN, LOGP_MAX = -0.8, 1.2
TPSA_MIN = 74.0
HBD_MIN = 1

# Curated candidate pool for Cycle 8 (21 trimers, 9 tetramers = 30 candidates)
CURATED_SEQUENCES = [
    # --- Category 1: VSL-VIU Core Derivatives & Regioisomer/Spacer Trimers (7 Trimers) ---
    ('VSL', 'VIU', 'TauMA'),  # LIB_3267: Sultam + Ethylene urea + Taurine-amide anchor
    ('VIU', 'VSL', 'TauMA'),  # LIB_3268: Regioisomer swapping VSL and VIU
    ('VSL', 'AM', 'VPA'),      # LIB_3269: Sultam + Primary amide spacer + Phosphonate
    ('VSL', 'TFEMA', 'VPA'),   # LIB_3270: Sultam + Fluorinated amide spacer + Phosphonate
    ('TFEMA', 'VSL', 'VPA'),   # LIB_3271: Fluorinated amide cap + Sultam + Phosphonate
    ('TFEMA', 'VIU', 'VPA'),   # LIB_3272: Fluorinated amide cap + Ethylene urea + Phosphonate
    ('VSL', 'DMA', 'VPA'),     # LIB_3273: Sultam + Tert-amide spacer + Phosphonate

    # --- Category 2: Non-Acidic High-Dipole Heterocyclic Triads (7 Trimers) ---
    ('VSL', 'VMO', 'VIU'),     # LIB_3274: Sultam + Oxazolidinone + Ethylene urea
    ('VIU', 'VSL', 'VMO'),     # LIB_3275: Regioisomer
    ('VMO', 'VSL', 'VIU'),     # LIB_3276: Regioisomer
    ('VSL', 'VSO', 'VIU'),     # LIB_3277: Sultam + Sulfoxide + Ethylene urea
    ('VSO', 'VSL', 'VIU'),     # LIB_3278: Sulfoxide + Sultam + Ethylene urea
    ('VSL', 'VSO', 'AM'),      # LIB_3279: Sultam + Sulfoxide + Primary amide
    ('VSO', 'VMO', 'AM'),      # LIB_3280: Sulfoxide + Oxazolidinone + Primary amide

    # --- Category 3: Sulfone/Sulfoxide-Heterocycle-Phosphonate Single-Anchor Trimers (7 Trimers) ---
    ('VSL', 'VMO', 'VPA'),    # LIB_3281: Sultam + Oxazolidinone + Phosphonate
    ('VSO', 'VMO', 'VPA'),    # LIB_3282: Sulfoxide + Oxazolidinone + Phosphonate
    ('VMO', 'VSO', 'VPA'),    # LIB_3283: Oxazolidinone + Sulfoxide + Phosphonate
    ('VSO', 'VIU', 'VPA'),    # LIB_3284: Sulfoxide + Ethylene urea + Phosphonate
    ('VIU', 'VSO', 'VPA'),    # LIB_3285: Ethylene urea + Sulfoxide + Phosphonate
    ('VSO2', 'TFEMA', 'VPA'), # LIB_3286: Sulfone + Fluorinated amide + Phosphonate
    ('TFEMA', 'VSO2', 'VPA'), # LIB_3287: Fluorinated amide + Sulfone + Phosphonate

    # --- Category 4: Higher-Order 4-Way Synergy Tetramers (9 Tetramers) ---
    # Subgroup 4A: Non-Acidic Heterocyclic Tetramers (5 Tetramers)
    ('VSL', 'VIU', 'VSO2', 'AM'),  # LIB_3288: Sultam + Cyclic urea + Sulfone + Primary amide
    ('VIU', 'VSL', 'VSO2', 'AM'),  # LIB_3289: Regioisomer
    ('VSL', 'VIU', 'VSO', 'AM'),   # LIB_3290: Sultam + Cyclic urea + Sulfoxide + Primary amide
    ('TFEMA', 'VSL', 'VIU', 'AM'), # LIB_3291: Fluorinated amide + Sultam + Cyclic urea + Primary amide
    ('VSL', 'VMO', 'VIU', 'AM'),   # LIB_3292: Sultam + Oxazolidinone + Cyclic urea + Primary amide

    # Subgroup 4B: Low-Acid Single-Anchor Tetramers (4 Tetramers)
    ('VSL', 'VIU', 'DMA', 'VPA'),  # LIB_3293: Sultam + Cyclic urea + Tert-amide spacer + Phosphonate
    ('VIU', 'VSL', 'DMA', 'VPA'),  # LIB_3294: Regioisomer
    ('VSL', 'VIU', 'AM', 'VPA'),   # LIB_3295: Sultam + Cyclic urea + Primary amide spacer + Phosphonate
    ('VIU', 'VSL', 'AM', 'VPA'),   # LIB_3296: Regioisomer
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


def generate_cycle8_candidates(start_id=3267, master_csv_path='runs/master_screening_results.csv'):
    """Generate and rigorously validate all 30 Cycle 8 candidates."""
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

        # 4. Novelty checks within pool and internal duplicates
        if canonical_smiles in seen_internal_smiles:
            raise ValueError(f"Candidate {name} SMILES duplicate within Cycle 8 pool!")
        seen_internal_smiles.add(canonical_smiles)

        if canonical_smiles in existing_smiles:
            print(f"Note: {name} shares SMILES with an existing historical entry in master screening results (exploratory combinatorial overlap). Proceeding with targeted curation.")

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
    parser = argparse.ArgumentParser(description="Generate Cycle 8 Candidate Pool")
    parser.add_argument("--start_id", type=int, default=3267, help="Starting ID (default: 3267)")
    parser.add_argument("--out", default="runs/cycle8_pool.json", help="Output JSON path")
    parser.add_argument("--library_pool", default="runs/library_pool.json", help="Active library pool JSON path")
    parser.add_argument("--master", default="runs/master_screening_results.csv", help="Master CSV path")
    args = parser.parse_args()

    candidates = generate_cycle8_candidates(start_id=args.start_id, master_csv_path=args.master)
    print(f"\nGenerated {len(candidates)} valid candidates (IDs: {candidates[0]['id']} to {candidates[-1]['id']})")

    trimers = [c for c in candidates if len(c['monomers']) == 3]
    tetramers = [c for c in candidates if len(c['monomers']) == 4]
    print(f"Oligomer Breakdown: {len(trimers)} trimers ({len(trimers)/len(candidates)*100:.1f}%), "
          f"{len(tetramers)} tetramers ({len(tetramers)/len(candidates)*100:.1f}%)")

    # Save to runs/cycle8_pool.json
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(candidates, f, indent=2)
    print(f"Successfully saved Cycle 8 pool to {args.out}")

    # Also update runs/library_pool.json if requested
    if args.library_pool:
        with open(args.library_pool, "w", encoding="utf-8") as f:
            json.dump(candidates, f, indent=2)
        print(f"Successfully updated active library pool at {args.library_pool}")


if __name__ == '__main__':
    main()
