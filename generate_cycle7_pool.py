#!/usr/bin/env python3
"""
generate_cycle7_pool.py - Cycle 7 Targeted Cheminformatics Pool Generator

Scientific Mission for Cycle 7:
Build upon the paradigm-shifting discovery from Cycle 6:
- 1st place: LIB_3216_AM-VSL-VIU (Score: 1.7328, dE_hbond = -1.062 eV, dE_ads = -1.057 eV, dE_ex = -1.299 eV)
  Demonstrated that a completely non-acidic heterocyclic triad (Sultam VSL + Cyclic Urea VIU + Primary Amide AM)
  delivers outstanding Zn(0001) interfacial chemisorption and bulk water H-bond network disruption without
  generating acidic protons that accelerate parasitic Hydrogen Evolution Reaction (HER).
- 2nd place: LIB_3235_VSO2-VMO-DMA-VPA (Score: 1.6594) - 4-way synergy tetramer
- Top desolvation kinetics: LIB_3220_VSO2-VSL-AM (Score: 1.4523, dE_ex = -1.066 eV, near ideal -0.9 eV window)
  and LIB_3231_VSO2-VSL-DMA-AM (Score: 1.4788, dE_hbond = -1.070 eV).

Design Strategy:
Systematic precision exploration of non-acidic and low-acid amphiphilic oligomers across 4 synergistic categories:
1. Non-Acidic Heterocyclic Sultam-Urea-Oxazolidinone Hybrids (7 Trimers)
2. Sulfone / Sulfoxide - Heterocycle Synergy Trimers (7 Trimers)
3. Low-Acid Single-Anchor Heterocycle Hybrids (7 Trimers, <= 1 VPA or TauMA)
4. Higher-Order 4-Way Synergy Tetramers (9 Tetramers: 5 non-acidic + 4 single-anchor)

Strict Constraints (PI_DIRECTOR.md & GEMINI.md):
1. Exclude hydrolytically labile esters: DMVP, HEMA strictly forbidden.
2. Strong acid repetition prevention: max 1 strong acid from {VPA, VSA, AMPS, TauMA, AA} (adjacent repeats = 0).
3. Physicochemical pre-filters (RDKit):
   - 200.0 <= MW <= 450.0 Da
   - -0.8 <= LogP <= 1.2
   - TPSA >= 75.0 A^2
   - HBD >= 1
4. Absolute novelty: 0 duplicate SMILES with runs/master_screening_results.csv.
5. Internal novelty: 0 duplicates within the Cycle 7 pool.
6. Target composition: exactly 30 candidates (LIB_3237 ~ LIB_3266), 21 trimers (70.0%), 9 tetramers (30.0%).
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

# Curated candidate pool for Cycle 7 (21 trimers, 9 tetramers = 30 candidates)
CURATED_SEQUENCES = [
    # --- Category 1: Non-Acidic Heterocyclic Sultam-Urea-Oxazolidinone Triads (7 Trimers) ---
    # Expanding on the champion AM-VSL-VIU (1.7328) non-acidic coordination and H-bond breaker motif
    ('TFEMA', 'VSL', 'VIU'),   # LIB_3237: Fluorinated amide + Sultam + Ethylene urea (amphiphilic shield)
    ('VIU', 'TFEMA', 'VSL'),   # LIB_3238: Regioisomer with terminal cyclic urea and central fluorinated amide
    ('VSL', 'DMA', 'VIU'),     # LIB_3239: Sultam + Tert-amide spacer + Ethylene urea (spacing bulky heterocycles)
    ('AM', 'VIU', 'VMO'),      # LIB_3240: Primary amide + Ethylene urea + Oxazolidinone (carbamate-urea-amide triad)
    ('TFEMA', 'VIU', 'VMO'),   # LIB_3241: Fluorinated amide + Ethylene urea + Oxazolidinone
    ('TFEMA', 'VMO', 'VIU'),   # LIB_3242: Regioisomer swapping oxazolidinone and cyclic urea
    ('VIU', 'TFEMA', 'VMO'),   # LIB_3243: Cyclic urea + Fluorinated amide spacer + Oxazolidinone

    # --- Category 2: Sulfone / Sulfoxide - Heterocycle Synergy Trimers (7 Trimers) ---
    # Exploiting high-dipole desolvation kinetics of VSO2/VSO (inspired by LIB_3220 dE_ex = -1.066 eV)
    ('VSO2', 'VIU', 'AM'),     # LIB_3244: Sulfone dipole + Ethylene urea + Primary amide
    ('VSO2', 'VSL', 'VIU'),    # LIB_3245: Sulfone dipole + Sultam + Ethylene urea (super-dipolar triad)
    ('VSO2', 'VIU', 'VSL'),    # LIB_3246: Regioisomer of above with central cyclic urea
    ('VSO2', 'VIU', 'VMO'),    # LIB_3247: Sulfone dipole + Ethylene urea + Oxazolidinone
    ('VSO2', 'VMO', 'VIU'),    # LIB_3248: Regioisomer of above (swapping carbamate and urea)
    ('TFEMA', 'VSO2', 'VIU'),  # LIB_3249: Fluorinated amide + Sulfone + Ethylene urea
    ('TFEMA', 'VSO', 'VIU'),   # LIB_3250: Fluorinated amide + Sulfoxide + Ethylene urea

    # --- Category 3: Low-Acid Single-Anchor Heterocycle Hybrids (7 Trimers) ---
    # Single phosphonate (VPA) or taurine-amide (TauMA) anchor on Zn(0001) with non-acidic heterocycles
    ('VSL', 'VIU', 'VPA'),     # LIB_3251: Sultam + Ethylene urea + Terminal phosphonate anchor
    ('VIU', 'VSL', 'VPA'),     # LIB_3252: Ethylene urea + Sultam + Terminal phosphonate anchor
    ('VIU', 'VMO', 'VPA'),     # LIB_3253: Ethylene urea + Oxazolidinone + Terminal phosphonate anchor
    ('VIU', 'TFEMA', 'VPA'),   # LIB_3254: Ethylene urea + Fluorinated amide + Phosphonate anchor
    ('VMO', 'VSL', 'VPA'),     # LIB_3255: Oxazolidinone + Sultam + Phosphonate anchor
    ('VIU', 'TauMA', 'TFEMA'), # LIB_3256: Ethylene urea + Taurine-amide anchor + Fluorinated amide
    ('VSO2', 'VMO', 'TauMA'),  # LIB_3257: Sulfone + Oxazolidinone + Taurine-amide anchor

    # --- Category 4: Higher-Order 4-Way Synergy Tetramers (9 Tetramers) ---
    # Building on tetramer breakthrough LIB_3235 (1.6594) and LIB_3231 (1.4788)
    # Subgroup 4A: Non-acidic 4-way heterocyclic-dipole tetramers (5 tetramers)
    ('VSL', 'VIU', 'DMA', 'AM'),   # LIB_3258: Sultam + Ethylene urea + Tert-amide + Primary amide
    ('VSO2', 'VIU', 'DMA', 'AM'),  # LIB_3259: Sulfone + Ethylene urea + Tert-amide + Primary amide
    ('VIU', 'VSO2', 'DMA', 'AM'),  # LIB_3260: Regioisomer swapping terminal VIU and VSO2
    ('VSO', 'VSL', 'DMA', 'AM'),   # LIB_3261: Sulfoxide + Sultam + Tert-amide + Primary amide (regioisomer of LIB_3232)
    ('TFEMA', 'VSO2', 'DMA', 'AM'),# LIB_3262: Fluorinated amide + Sulfone + Tert-amide + Primary amide

    # Subgroup 4B: Low-acid single-anchor tetramers (4 tetramers)
    ('VSO2', 'VIU', 'DMA', 'VPA'), # LIB_3263: Sulfone + Ethylene urea + Tert-amide + Phosphonate anchor
    ('VIU', 'VSO2', 'DMA', 'VPA'), # LIB_3264: Regioisomer of above with terminal cyclic urea
    ('VSO', 'VMO', 'DMA', 'VPA'),  # LIB_3265: Sulfoxide + Oxazolidinone + Tert-amide + Phosphonate anchor
    ('VMO', 'VIU', 'DMA', 'VPA'),  # LIB_3266: Oxazolidinone + Ethylene urea + Tert-amide + Phosphonate anchor
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


def generate_cycle7_candidates(start_id=3237, master_csv_path='runs/master_screening_results.csv'):
    """Generate and rigorously validate all 30 Cycle 7 candidates."""
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
            raise ValueError(f"Candidate {name} SMILES duplicate within Cycle 7 pool!")
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
    parser = argparse.ArgumentParser(description="Generate Cycle 7 Candidate Pool")
    parser.add_argument("--start_id", type=int, default=3237, help="Starting ID (default: 3237)")
    parser.add_argument("--out", default="runs/cycle7_pool.json", help="Output JSON path")
    parser.add_argument("--library_pool", default="runs/library_pool.json", help="Active library pool JSON path")
    parser.add_argument("--master", default="runs/master_screening_results.csv", help="Master CSV path")
    args = parser.parse_args()

    candidates = generate_cycle7_candidates(start_id=args.start_id, master_csv_path=args.master)
    print(f"\nGenerated {len(candidates)} valid candidates (IDs: {candidates[0]['id']} to {candidates[-1]['id']})")

    trimers = [c for c in candidates if len(c['monomers']) == 3]
    tetramers = [c for c in candidates if len(c['monomers']) == 4]
    print(f"Oligomer Breakdown: {len(trimers)} trimers ({len(trimers)/len(candidates)*100:.1f}%), "
          f"{len(tetramers)} tetramers ({len(tetramers)/len(candidates)*100:.1f}%)")

    # Save to runs/cycle7_pool.json
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(candidates, f, indent=2)
    print(f"Successfully saved {len(candidates)} candidates to {args.out}")

    # Save to runs/library_pool.json (active pipeline pool)
    if args.library_pool:
        os.makedirs(os.path.dirname(args.library_pool), exist_ok=True)
        with open(args.library_pool, "w", encoding="utf-8") as f:
            json.dump(candidates, f, indent=2)
        print(f"Successfully updated active library pool: {args.library_pool}")


if __name__ == "__main__":
    main()
