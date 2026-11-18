import os
import json
import random
import argparse
import itertools
from rdkit import Chem
from rdkit.Chem import Descriptors, Crippen, rdMolDescriptors

# Monomer building blocks spanning diverse chemical spaces with [*] attachment points
MONOMERS = {
    "EG":      {"smiles": "[*]OCC[*]",                            "group": "-OH/-O-",                 "family": "Polyether"},
    "VA":      {"smiles": "[*]CC(O)[*]",                          "group": "-OH",                     "family": "Polyvinyl"},
    "AM":      {"smiles": "[*]CC(C(=O)N)[*]",                     "group": "-CONH2",                  "family": "Acrylamide"},
    "AN":      {"smiles": "[*]CC(C#N)[*]",                        "group": "-CN",                     "family": "Nitrile"},
    "AA":      {"smiles": "[*]CC(C(=O)O)[*]",                     "group": "-COOH",                   "family": "Carboxylic"},
    "DMA":     {"smiles": "[*]CC(C(=O)N(C)C)[*]",                 "group": "-CONMe2",                 "family": "Tert-Amide"},
    "VP":      {"smiles": "[*]CC(N1CCCC1=O)[*]",                  "group": "Pyrrolidone",             "family": "Heterocycle"},
    "VI":      {"smiles": "[*]CC(n1ccnc1)[*]",                    "group": "Imidazole",               "family": "Heterocycle"},
    "AMPS":    {"smiles": "[*]CC(C(=O)NCC(C)(C)S(=O)(=O)O)[*]",   "group": "-SO3H/-CONH-",            "family": "Sulfonic"},
    "VSA":     {"smiles": "[*]CC(S(=O)(=O)O)[*]",                 "group": "-SO3H",                   "family": "Sulfonic"},
    "TFEA":    {"smiles": "[*]CC(C(=O)OCC(F)(F)F)[*]",            "group": "-CF3",                    "family": "Fluorinated"},
    "HEMA":    {"smiles": "[*]CC(C)(C(=O)OCCO)[*]",               "group": "-COO-/-OH",               "family": "Ester-OH"},
    "SBMA":    {"smiles": "[*]CC(C)(C(=O)OCC[N+](C)(C)CCCS(=O)(=O)[O-])[*]", "group": "Zwitterion", "family": "Zwitterionic"},
    "MAN":     {"smiles": "[*]CC(C)(C#N)[*]",                     "group": "-CN/-CH3",                "family": "Methacrylonitrile"},
    "VSO":     {"smiles": "[*]CC(S(=O)C)[*]",                      "group": "-S(=O)Me",                "family": "Sulfoxide"},
    "TFEMA":   {"smiles": "[*]CC(C(=O)NCC(F)(F)F)[*]",             "group": "-CF3/-CONH-",             "family": "Fluorinated-Amide"},
    "VPA":     {"smiles": "[*]CC(P(=O)(O)O)[*]",                   "group": "-PO3H2",                  "family": "Phosphonate"},
    "ACMO":    {"smiles": "[*]CC(C(=O)N1CCOCC1)[*]",               "group": "Morpholine",              "family": "Heterocycle-Ether"},
    # Cycle 1 newly introduced monomers (4 species)
    "VMO":     {"smiles": "[*]CC(N1CCOC1=O)[*]",                   "group": "Oxazolidinone",           "family": "Heterocycle-Carbamate"},
    "VSO2":    {"smiles": "[*]CC(S(=O)(=O)C)[*]",                  "group": "-SO2Me",                  "family": "Sulfone"},
    "TFMSA":   {"smiles": "[*]CC(S(=O)(=O)NCC(F)(F)F)[*]",        "group": "Fluorinated-Sulfonamide", "family": "Fluorinated-Sulfonamide"},
    "DMVP":    {"smiles": "[*]CC(P(=O)(OC)OC)[*]",                 "group": "Phosphonate-Ester",       "family": "Phosphonate-Ester"},
    # Cycle 2 newly introduced monomers (3 species)
    "VIU":     {"smiles": "[*]CC(N1CCNC1=O)[*]",                   "group": "EthyleneUrea",            "family": "Heterocycle-Urea"},
    "TauMA":   {"smiles": "[*]CC(C(=O)NCCS(=O)(=O)O)[*]",          "group": "-SO3H/-CONH-",            "family": "Sulfonic-Amide"},
    "VSL":     {"smiles": "[*]CC(N1CCCCS1(=O)=O)[*]",              "group": "Sultam",                  "family": "Heterocycle-Sulfonamide"},
}

def connect_monomers(m_list):
    """Sequentially couple [*] dummy atoms to build oligomer SMILES with terminal H capping"""
    mol = Chem.MolFromSmiles(m_list[0])
    # Replace first terminal [*] with hydrogen ([H])
    dummy_idx = [a.GetIdx() for a in mol.GetAtoms() if a.GetSymbol() == '*']
    rw = Chem.RWMol(mol)
    rw.ReplaceAtom(dummy_idx[0], Chem.Atom(1))
    curr = Chem.RemoveHs(rw.GetMol())

    for m_smi in m_list[1:]:
        nxt = Chem.MolFromSmiles(m_smi)
        combo = Chem.CombineMols(curr, nxt)
        dummies = [a.GetIdx() for a in combo.GetAtoms() if a.GetSymbol() == '*']
        if len(dummies) < 2:
            return None
        # Connect remaining [*] of current oligomer to neighbor of first [*] in next monomer
        rw_c = Chem.RWMol(combo)
        d1, d2 = dummies[0], dummies[1]
        n1 = rw_c.GetAtomWithIdx(d1).GetNeighbors()[0].GetIdx()
        n2 = rw_c.GetAtomWithIdx(d2).GetNeighbors()[0].GetIdx()
        rw_c.AddBond(n1, n2, Chem.BondType.SINGLE)
        for idx in sorted([d1, d2], reverse=True):
            rw_c.RemoveAtom(idx)
        curr = rw_c.GetMol()

    # Cap final terminal [*] with hydrogen
    rem_dummies = [a.GetIdx() for a in curr.GetAtoms() if a.GetSymbol() == '*']
    rw_final = Chem.RWMol(curr)
    for idx in rem_dummies:
        rw_final.ReplaceAtom(idx, Chem.Atom(1))
    final_mol = Chem.RemoveHs(rw_final.GetMol())
    Chem.SanitizeMol(final_mol)
    return Chem.MolToSmiles(final_mol, canonical=True)

def generate_cycle1_pool(target_size=60, start_id=601):
    """Generate Cycle 1 candidate pool across 3 strategic categories
    (A) Exhaustive sequence isomers of top-performing combinations (24 candidates)
    (B) Promising combinations incorporating novel heterocyclic monomers (28 candidates)
    (C) Negative controls and falsification stress tests (8 candidates)
    Total 60 candidates (LIB_0601 ~ LIB_0660)
    """
    # Automated pipeline step
    base_combos = [
        ["VPA", "MAN", "AM"],
        ["TFEMA", "VP", "VSA"],
        ["VSO", "TFEMA", "AM"],
        ["VPA", "TFEMA", "AM"]
    ]
    cat_a = []
    for base in base_combos:
        for p in itertools.permutations(base):
            cat_a.append(p)

    # Automated pipeline step
    cat_c = [
        ("VPA", "VPA", "VPA"),
        ("TFEMA", "TFEMA", "TFEMA"),
        ("VSO", "VSO", "VSO"),
        ("MAN", "MAN", "MAN"),
        ("AM", "AM", "AM"),
        ("VMO", "VMO", "VMO"),
        ("VSO2", "VSO2", "VSO2"),
        ("TFMSA", "TFMSA", "TFMSA")
    ]

    # Automated pipeline step
    cat_b = [
        # Automated pipeline step
        ("VMO", "MAN", "AM"),
        ("VMO", "TFEMA", "AM"),
        ("VMO", "VPA", "AM"),
        ("VMO", "VP", "VSA"),
        ("VMO", "VSO", "AM"),
        ("VMO", "AA", "AM"),
        ("VMO", "VSA", "AM"),

        # Automated pipeline step
        ("VSO2", "MAN", "AM"),
        ("VSO2", "TFEMA", "AM"),
        ("VSO2", "VPA", "AM"),
        ("VSO2", "VP", "VSA"),
        ("VSO2", "VSO", "AM"),
        ("VSO2", "AA", "AM"),
        ("VSO2", "VSA", "AM"),

        # Automated pipeline step
        ("TFMSA", "MAN", "AM"),
        ("TFMSA", "VP", "VSA"),
        ("TFMSA", "VPA", "AM"),
        ("TFMSA", "VSO", "AM"),
        ("TFMSA", "AA", "AM"),
        ("TFMSA", "AM", "AM"),
        ("TFMSA", "TFEMA", "AM"),

        # Automated pipeline step
        ("DMVP", "MAN", "AM"),
        ("DMVP", "TFEMA", "AM"),
        ("DMVP", "VPA", "AM"),
        ("DMVP", "VP", "VSA"),
        ("DMVP", "VSO", "AM"),
        ("DMVP", "AA", "AM"),

        # Automated pipeline step
        ("VMO", "VSO2", "AM")
    ]

    all_planned = cat_a + cat_b + cat_c
    if target_size and target_size < len(all_planned):
        all_planned = all_planned[:target_size]

    library = []
    current_id = start_id

    for combo in all_planned:
        m_smiles = [MONOMERS[k]["smiles"] for k in combo]
        smi = connect_monomers(m_smiles)
        if not smi:
            continue
        mol = Chem.MolFromSmiles(smi)
        mw = Descriptors.MolWt(mol)

        cid = f"LIB_{current_id:04d}_{'-'.join(combo)}"
        current_id += 1
        families = sorted(list(set(MONOMERS[k]["family"] for k in combo)))
        groups = sorted(list(set(MONOMERS[k]["group"] for k in combo)))

        category = "A (Regioisomer)" if combo in cat_a else ("C (Stress/Control)" if combo in cat_c else "B (Hetero Synergy)")

        library.append({
            "id": cid,
            "name": f"Oligomer({'-'.join(combo)})",
            "category": category,
            "backbone": " + ".join(families),
            "functional_groups": ", ".join(groups),
            "mol_weight": round(mw, 2),
            "smiles": smi
        })

    return library

def generate_cycle2_pool(target_size=36, start_id=661):
    """Generate Cycle 2 exploration pool based on 4 categories (36 candidates total)
    (A) 12 VMO sequence isomers (LIB_0661 ~ LIB_0672)
    (B) 12 novel heterocycles and sterically unhindered sulfonic acids (LIB_0673 ~ LIB_0684)
    (C) 8 asymmetric amphiphilic Janus candidates (LIB_0685 ~ LIB_0692)
    (D) 4 falsification and control candidates (LIB_0693 ~ LIB_0696)
    Total 36 candidates (LIB_0661 ~ LIB_0696)
    """
    # Automated pipeline step
    cat_a = []
    for base in [["VMO", "VPA", "AM"], ["VMO", "TauMA", "AM"]]:
        for p in itertools.permutations(base):
            cat_a.append(tuple(p))

    # Automated pipeline step
    cat_b = [
        # Automated pipeline step
        ("VIU", "VPA", "AM"),
        ("VIU", "TauMA", "AM"),
        ("VIU", "VMO", "AM"),
        ("VIU", "VSO", "AM"),
        ("VIU", "MAN", "AM"),
        ("VIU", "TFEMA", "VSA"),
        # Automated pipeline step
        ("VSL", "VMO", "AM"),
        ("VSL", "VPA", "AM"),
        ("VSL", "TFEMA", "AM"),
        ("TauMA", "TFEMA", "AM"),
        ("TauMA", "VP", "AM"),
        ("VMO", "VSL", "AM"),
    ]

    # Automated pipeline step
    cat_c = [
        ("TFEMA", "VIU", "VPA"),
        ("TFEMA", "VIU", "TauMA"),
        ("TFEMA", "VMO", "TauMA"),
        ("TFEMA", "VMO", "VPA"),
        ("TFMSA", "VIU", "AM"),
        ("TFMSA", "VMO", "AM"),
        ("TFEMA", "VSO", "TauMA"),
        ("TFEMA", "VIU", "VSA"),
    ]

    # Automated pipeline step
    cat_d = [
        # Automated pipeline step
        ("VIU", "VIU", "VIU"),
        ("TauMA", "TauMA", "TauMA"),
        ("VSL", "VSL", "VSL"),
        # Automated pipeline step
        ("HEMA", "VMO", "AM"),
    ]

    planned_with_cat = []
    for c in cat_a:
        planned_with_cat.append((c, "A (Regioisomer)"))
    for c in cat_b:
        planned_with_cat.append((c, "B (Hetero & Non-hindered Sulfonic)"))
    for c in cat_c:
        planned_with_cat.append((c, "C (Asymmetric Janus)"))
    for c in cat_d:
        planned_with_cat.append((c, "D (Control/Stress)"))

    if target_size and target_size < len(planned_with_cat):
        planned_with_cat = planned_with_cat[:target_size]

    library = []
    current_id = start_id

    for combo, category in planned_with_cat:
        m_smiles = [MONOMERS[k]["smiles"] for k in combo]
        smi = connect_monomers(m_smiles)
        if not smi:
            print(f"Warning: Failed to connect monomers {combo}")
            continue
        mol = Chem.MolFromSmiles(smi)
        mw = Descriptors.MolWt(mol)

        cid = f"LIB_{current_id:04d}_{'-'.join(combo)}"
        current_id += 1
        families = sorted(list(set(MONOMERS[k]["family"] for k in combo)))
        groups = sorted(list(set(MONOMERS[k]["group"] for k in combo)))

        library.append({
            "id": cid,
            "name": f"Oligomer({'-'.join(combo)})",
            "category": category,
            "backbone": " + ".join(families),
            "functional_groups": ", ".join(groups),
            "mol_weight": round(mw, 2),
            "smiles": smi
        })

    return library

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=60, help="Target number of candidates to generate")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="runs/next_pool.json")
    parser.add_argument("--start_id", type=int, default=661, help="Starting ID number (e.g. 661 for LIB_0661)")
    parser.add_argument("--cycle", type=int, default=2, help="Design cycle (1 or 2, default: 2)")
    parser.add_argument("--random_pool", action="store_true", help="Generate random pool instead of structured pool")
    parser.add_argument("--legacy_filter", action="store_true", help="Use legacy MW <= 420 Da filter only")
    args = parser.parse_args()

    random.seed(args.seed)

    if not args.random_pool:
        if args.cycle == 2 or args.start_id >= 661:
            library = generate_cycle2_pool(target_size=args.size, start_id=args.start_id)
        else:
            library = generate_cycle1_pool(target_size=args.size, start_id=args.start_id)
    else:
        keys = list(MONOMERS.keys())
        all_combos = list(itertools.product(keys, repeat=2)) + list(itertools.product(keys, repeat=3))
        random.shuffle(all_combos)

        seen_smiles = set()
        library = []

        for combo in all_combos:
            if len(library) >= args.size:
                break
            m_smiles = [MONOMERS[k]["smiles"] for k in combo]
            try:
                smi = connect_monomers(m_smiles)
                if not smi or smi in seen_smiles:
                    continue
                mol = Chem.MolFromSmiles(smi)
                mw = Descriptors.MolWt(mol)

                if args.legacy_filter:
                    if mw > 420.0:
                        continue
                else:
                    if not (220.0 <= mw <= 380.0):
                        continue
                    logp = Crippen.MolLogP(mol)
                    if not (-0.6 <= logp <= 1.0):
                        continue
                    tpsa = Descriptors.TPSA(mol)
                    if tpsa < 80.0:
                        continue
                    hbd = rdMolDescriptors.CalcNumHBD(mol)
                    if hbd < 1:
                        continue

                seen_smiles.add(smi)
                cid = f"LIB_{args.start_id + len(library):04d}_{'-'.join(combo)}"
                families = sorted(list(set(MONOMERS[k]["family"] for k in combo)))
                groups = sorted(list(set(MONOMERS[k]["group"] for k in combo)))

                library.append({
                    "id": cid,
                    "name": f"Oligomer({'-'.join(combo)})",
                    "backbone": " + ".join(families),
                    "functional_groups": ", ".join(groups),
                    "mol_weight": round(mw, 2),
                    "smiles": smi
                })
            except Exception:
                continue

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(library, f, indent=2)
    print(f"Generated {len(library)} unique valid polymer oligomers in {args.out} (IDs: {library[0]['id']} ~ {library[-1]['id']})")

if __name__ == "__main__":
    main()
