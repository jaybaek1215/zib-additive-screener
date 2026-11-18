import itertools
import random
import json
import pandas as pd
from rdkit import Chem
from rdkit.Chem import Descriptors, Crippen, rdMolDescriptors
from generate_library import MONOMERS, connect_monomers

# Load existing smiles to avoid duplicates
existing_df = pd.read_csv('runs/master_screening_results.csv')
existing_smiles = set(existing_df['smiles'].dropna().tolist())
print(f"Loaded {len(existing_smiles)} existing SMILES from master_screening_results.csv")

# Excluded / Restricted monomers check:
# 1. Exclude labile esters: DMVP, HEMA
# 2. Strong acid monomers: VPA, VSA, AMPS, TauMA, AA. Max 1 per oligomer.
strong_acids = {'VPA', 'VSA', 'AMPS', 'TauMA', 'AA'}
excluded_monomers = {'DMVP', 'HEMA'}

available_monomers = {k: v for k, v in MONOMERS.items() if k not in excluded_monomers}
all_keys = list(available_monomers.keys())

candidates = []
start_id = 3147
random.seed(42)

attempts = 0
while len(candidates) < 30 and attempts < 10000:
    attempts += 1
    # Trimer 70% (3), Tetramer 30% (4)
    length = 3 if random.random() < 0.7 else 4
    
    picked = random.choices(all_keys, k=length)
    
    sa_count = sum(1 for m in picked if m in strong_acids)
    if sa_count > 1:
        continue
        
    try:
        smiles_list = [MONOMERS[m]['smiles'] for m in picked]
        canonical_smiles = connect_monomers(smiles_list)
        if not canonical_smiles:
            continue
            
        if canonical_smiles in existing_smiles:
            continue
            
        if any(c['smiles'] == canonical_smiles for c in candidates):
            continue
            
        mol = Chem.MolFromSmiles(canonical_smiles)
        if not mol:
            continue
            
        mw = Descriptors.ExactMolWt(mol)
        logp = Crippen.MolLogP(mol)
        tpsa = rdMolDescriptors.CalcTPSA(mol)
        hbd = rdMolDescriptors.CalcNumHBD(mol)
        
        # 200.0 <= MW <= 450.0
        # -0.8 <= LogP <= 1.2
        # TPSA >= 75.0
        # HBD >= 1
        if not (200.0 <= mw <= 450.0):
            continue
        if not (-0.8 <= logp <= 1.2):
            continue
        if not (tpsa >= 75.0):
            continue
        if not (hbd >= 1):
            continue
            
        cand_id = f"LIB_{start_id}"
        start_id += 1
        name = f"{cand_id}_{'-'.join(picked)}"
        backbone = "Poly(vinyl/acrylic)"
        functional_groups = ", ".join([MONOMERS[m]['group'] for m in picked])
        
        candidates.append({
            "id": cand_id,
            "name": name,
            "backbone": backbone,
            "functional_groups": functional_groups,
            "mol_weight": round(mw, 2),
            "logp": round(logp, 2),
            "tpsa": round(tpsa, 2),
            "hbd": hbd,
            "smiles": canonical_smiles,
            "monomers": picked
        })
        existing_smiles.add(canonical_smiles)
        
    except Exception as e:
        continue

print(f"Successfully generated {len(candidates)} candidates after {attempts} attempts.")

with open('runs/next_pool.json', 'w') as f:
    json.dump(candidates, f, indent=2)

print("Saved to runs/next_pool.json")
