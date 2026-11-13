import os
import json
import argparse
import numpy as np
import pandas as pd
import torch
from ase.io import read, write
from ase.optimize import BFGS
from ase.constraints import FixAtoms
from ase.geometry import get_distances
from mattersim.forcefield import MatterSimCalculator

def get_calculator():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return MatterSimCalculator(load_path="MatterSim-v1.0.0-5M.pth", device=device)

def check_physical_validity(atoms, fmax_limit=0.10):
    """비물리적 구조 붕괴 및 원자 겹침 필터링 (Pathological minima 방지)"""
    # 1. 최소 원자 간 거리 확인 (O-H 결합 약 0.96 A 감안하여 0.75 A 미만 시 겹침 판정)
    _, dist_matrix = get_distances(atoms.positions, cell=atoms.cell, pbc=atoms.pbc)
    np.fill_diagonal(dist_matrix, 999.0)
    min_dist = float(np.min(dist_matrix))
    if min_dist < 0.75:
        return False, f"Atom overlap (min_dist={min_dist:.2f} A)"
    
    # 2. 잔류 힘 수렴 확인
    forces = atoms.get_forces()
    max_f = float(np.max(np.linalg.norm(forces, axis=1)))
    if max_f > fmax_limit:
        return False, f"Did not converge (fmax={max_f:.3f} eV/A)"
        
    return True, "Valid"

def relax_structure(filepath: str, calc, fix_bottom_layers=False, steps=120, fmax=0.05):
    atoms = read(filepath)
    if fix_bottom_layers:
        # Zn 슬래브 하단 2개 층 고정 (z < 6.0 A)
        mask = [atom.symbol == 'Zn' and atom.position[2] < 6.0 for atom in atoms]
        atoms.set_constraint(FixAtoms(mask=mask))
        
    atoms.calc = calc
    opt = BFGS(atoms, logfile=None)
    opt.run(fmax=fmax, steps=steps)
    
    valid, reason = check_physical_validity(atoms)
    energy = float(atoms.get_potential_energy())
    out_path = filepath.replace(".extxyz", "_relaxed.extxyz")
    write(out_path, atoms)
    return energy, valid, reason

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--struct_dir", default="structures")
    parser.add_argument("--out_csv", required=True)
    args = parser.parse_args()

    calc = get_calculator()
    ref_dir = os.path.join(args.struct_dir, "references")
    
    # 1. 참조 구조(Reference) 에너지 계산 (이미 계산된 파일이 있으면 재사용)
    ref_cache = os.path.join(ref_dir, "ref_energies.json")
    if os.path.exists(ref_cache):
        with open(ref_cache, "r") as f:
            refs = json.load(f)
    else:
        e_h2o, _, _ = relax_structure(os.path.join(ref_dir, "H2O.extxyz"), calc, steps=100)
        e_zn_hex, _, _ = relax_structure(os.path.join(ref_dir, "Zn_H2O_6.extxyz"), calc, steps=150)
        e_slab, _, _ = relax_structure(os.path.join(ref_dir, "Zn_slab.extxyz"), calc, fix_bottom_layers=True, steps=100)
        refs = {"E_H2O": e_h2o, "E_Zn_H2O_6": e_zn_hex, "E_Zn_slab": e_slab}
        with open(ref_cache, "w") as f:
            json.dump(refs, f, indent=2)

    with open(args.candidates, "r", encoding="utf-8") as f:
        candidates = json.load(f)

    records = []
    for item in candidates:
        cid = item["id"]
        c_dir = os.path.join(args.struct_dir, cid)
        if not os.path.exists(os.path.join(c_dir, "isolated.extxyz")):
            continue
            
        try:
            e_iso, v1, r1 = relax_structure(os.path.join(c_dir, "isolated.extxyz"), calc, steps=120)
            e_h2o_c, v2, r2 = relax_structure(os.path.join(c_dir, "h2o_cluster.extxyz"), calc, steps=150)
            e_zn_c, v3, r3 = relax_structure(os.path.join(c_dir, "zn_cluster.extxyz"), calc, steps=180)
            e_ads_s, v4, r4 = relax_structure(os.path.join(c_dir, "zn_ads.extxyz"), calc, fix_bottom_layers=True, steps=150)
            
            all_valid = v1 and v2 and v3 and v4
            status = "PASS" if all_valid else f"WARN: {r1} | {r2} | {r3} | {r4}"
            
            # 3대 핵심 스크리닝 지표 계산 (eV)
            dE_hbond = e_h2o_c - e_iso - 2.0 * refs["E_H2O"]
            dE_exchange = (e_zn_c + refs["E_H2O"]) - (refs["E_Zn_H2O_6"] + e_iso)
            dE_ads = e_ads_s - refs["E_Zn_slab"] - e_iso
            
            # 종합 스코어 (자유수 포집 + 적정 용매화 치환 + 강한 계면 우선 흡착)
            # 참고: 너무 극단적인 결합(-4.0 eV 이하)은 탈용매화/탈착 방해 가능성으로 페널티 부여
            solv_penalty = max(0.0, abs(dE_exchange + 0.8) - 0.8) * 1.5
            score = (-0.4 * dE_hbond) + (-0.6 * dE_exchange) + (-0.5 * dE_ads) - solv_penalty
            if not all_valid:
                score -= 99.0

            records.append({
                "id": cid,
                "name": item["name"],
                "backbone": item.get("backbone", ""),
                "functional_groups": item.get("functional_groups", ""),
                "smiles": item["smiles"],
                "dE_hbond_eV": round(dE_hbond, 4),
                "dE_exchange_eV": round(dE_exchange, 4),
                "dE_ads_eV": round(dE_ads, 4),
                "composite_score": round(score, 4),
                "status": status
            })
            print(f"[{cid}] dE_hbond={dE_hbond:.3f} | dE_ex={dE_exchange:.3f} | dE_ads={dE_ads:.3f} | Score={score:.3f} ({status})")
        except Exception as e:
            print(f"[ERROR] {cid}: {e}")

    df = pd.DataFrame(records).sort_values(by="composite_score", ascending=False)
    df.to_csv(args.out_csv, index=False)
    print(f"\nSaved screening results to {args.out_csv}")

if __name__ == "__main__":
    main()
