import os
import json
import random
import argparse
from itertools import product
from rdkit import Chem
from rdkit.Chem import Descriptors, QED, Crippen, rdMolDescriptors

# 다양한 화학 공간을 포괄하는 모노머 빌딩 블록 (연결점 [*] 포함)
MONOMERS = {
    "EG":      {"smiles": "[*]OCC[*]",                  "group": "-OH/-O-",       "family": "Polyether"},
    "VA":      {"smiles": "[*]CC(O)[*]",                "group": "-OH",           "family": "Polyvinyl"},
    "AM":      {"smiles": "[*]CC(C(=O)N)[*]",           "group": "-CONH2",        "family": "Acrylamide"},
    "AN":      {"smiles": "[*]CC(C#N)[*]",              "group": "-CN",           "family": "Nitrile"},
    "AA":      {"smiles": "[*]CC(C(=O)O)[*]",           "group": "-COOH",         "family": "Carboxylic"},
    "DMA":     {"smiles": "[*]CC(C(=O)N(C)C)[*]",       "group": "-CONMe2",       "family": "Tert-Amide"},
    "VP":      {"smiles": "[*]CC(N1CCCC1=O)[*]",        "group": "Pyrrolidone",   "family": "Heterocycle"},
    "VI":      {"smiles": "[*]CC(n1ccnc1)[*]",          "group": "Imidazole",     "family": "Heterocycle"},
    "AMPS":    {"smiles": "[*]CC(C(=O)NCC(C)(C)S(=O)(=O)O)[*]", "group": "-SO3H/-CONH-", "family": "Sulfonic"},
    "VSA":     {"smiles": "[*]CC(S(=O)(=O)O)[*]",       "group": "-SO3H",         "family": "Sulfonic"},
    "TFEA":    {"smiles": "[*]CC(C(=O)OCC(F)(F)F)[*]",  "group": "-CF3",          "family": "Fluorinated"},
    "HEMA":    {"smiles": "[*]CC(C)(C(=O)OCCO)[*]",     "group": "-COO-/-OH",     "family": "Ester-OH"},
    "SBMA":    {"smiles": "[*]CC(C)(C(=O)OCC[N+](C)(C)CCCS(=O)(=O)[O-])[*]", "group": "Zwitterion", "family": "Zwitterionic"},
    "MAN":     {"smiles": "[*]CC(C)(C#N)[*]",           "group": "-CN/-CH3",      "family": "Methacrylonitrile"},
    # Round 2 신규 도입 단량체 4종 (SAR 우수 패턴 및 전기화학 비판 결함 보완)
    "VSO":     {"smiles": "[*]CC(S(=O)C)[*]",            "group": "-S(=O)Me",      "family": "Sulfoxide"},
    "TFEMA":   {"smiles": "[*]CC(C(=O)NCC(F)(F)F)[*]",   "group": "-CF3/-CONH-",   "family": "Fluorinated-Amide"},
    "VPA":     {"smiles": "[*]CC(P(=O)(O)O)[*]",         "group": "-PO3H2",        "family": "Phosphonate"},
    "ACMO":    {"smiles": "[*]CC(C(=O)N1CCOCC1)[*]",     "group": "Morpholine",    "family": "Heterocycle-Ether"},
}

def connect_monomers(m_list):
    """[*] 더미 원자를 순차 결합하여 올리고머 SMILES 생성 및 말단 H 캡핑"""
    mol = Chem.MolFromSmiles(m_list[0])
    # 첫 번째 말단 [*] 하나를 수소([H])로 치환
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
        # curr의 남은 [*]와 nxt의 첫 번째 [*]의 이웃 원자를 직접 연결
        rw_c = Chem.RWMol(combo)
        d1, d2 = dummies[0], dummies[1]
        n1 = rw_c.GetAtomWithIdx(d1).GetNeighbors()[0].GetIdx()
        n2 = rw_c.GetAtomWithIdx(d2).GetNeighbors()[0].GetIdx()
        rw_c.AddBond(n1, n2, Chem.BondType.SINGLE)
        for idx in sorted([d1, d2], reverse=True):
            rw_c.RemoveAtom(idx)
        curr = rw_c.GetMol()

    # 마지막 남은 [*] 말단을 수소로 캡핑
    rem_dummies = [a.GetIdx() for a in curr.GetAtoms() if a.GetSymbol() == '*']
    rw_final = Chem.RWMol(curr)
    for idx in rem_dummies:
        rw_final.ReplaceAtom(idx, Chem.Atom(1))
    final_mol = Chem.RemoveHs(rw_final.GetMol())
    Chem.SanitizeMol(final_mol)
    return Chem.MolToSmiles(final_mol, canonical=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=300, help="Target number of candidates to generate")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="runs/library_pool.json")
    parser.add_argument("--legacy_filter", action="store_true", help="Use legacy MW <= 420 Da filter only")
    args = parser.parse_args()

    random.seed(args.seed)
    keys = list(MONOMERS.keys())
    
    # 2량체(18^2 = 324) + 3량체(18^3 = 5832) 전체 조합 공간 = 6,156종
    all_combos = list(product(keys, repeat=2)) + list(product(keys, repeat=3))
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
                # 레거시 단순 분자량 필터 (420 Da 이하)
                if mw > 420.0:
                    continue
            else:
                # Round 1 critique & SAR QA/QC 물리화학적 윈도우 규칙 (round1_critique.md Section 6.4)
                # 1. 분자량(MW): 220 ~ 380 g/mol (3량체 올리고머 크기 제어, 전해액 내 고확산성 보장)
                if not (220.0 <= mw <= 380.0):
                    continue
                # 2. 분배계수(LogP): -0.6 <= LogP <= 1.0 (2M ZnSO4 전해액 내 염석 및 상분리 원천 차단)
                logp = Crippen.MolLogP(mol)
                if not (-0.6 <= logp <= 1.0):
                    continue
                # 3. 극성 표면적(TPSA): >= 80.0 Å² (물 분자와의 친화력 및 자유수 포집을 위한 최소 극성 표면적)
                tpsa = Descriptors.TPSA(mol)
                if tpsa < 80.0:
                    continue
                # 4. 수소결합 공여체(HBD): >= 1 (자유수 수소결합 네트워크 형성을 위한 필수 주개)
                hbd = rdMolDescriptors.CalcNumHBD(mol)
                if hbd < 1:
                    continue

            seen_smiles.add(smi)
            
            cid = f"LIB_{len(library)+1:04d}_{'-'.join(combo)}"
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
    print(f"Generated {len(library)} unique valid polymer oligomers in {args.out}")

if __name__ == "__main__":
    main()
