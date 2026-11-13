import os
import json
import argparse
import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem
from ase import Atoms
from ase.build import hcp0001, molecule, add_adsorbate
from ase.io import write

def smiles_to_ase(smiles: str, name: str) -> Atoms:
    """SMILES 문자열을 RDKit MMFF94로 1차 최적화한 뒤 ASE Atoms 객체로 변환"""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")
    mol = Chem.AddHs(mol)
    params = AllChem.ETKDGv3()
    params.randomSeed = 42
    if AllChem.EmbedMolecule(mol, params) != 0:
        raise RuntimeError(f"3D embedding failed for {name}")
    AllChem.MMFFOptimizeMolecule(mol, maxIters=500)
    
    conf = mol.GetConformer()
    symbols = [atom.GetSymbol() for atom in mol.GetAtoms()]
    positions = np.array([list(conf.GetAtomPosition(i)) for i in range(mol.GetNumAtoms())])
    
    atoms = Atoms(symbols=symbols, positions=positions)
    atoms.center(vacuum=10.0)
    return atoms

def find_coordinating_atom_idx(atoms: Atoms) -> int:
    """Zn2+ 또는 표면에 배위할 수 있는 전기음성도 높은 원자(O, N, S, F) 인덱스 탐색"""
    priority = ['O', 'N', 'S', 'F']
    for elem in priority:
        indices = [i for i, s in enumerate(atoms.get_chemical_symbols()) if s == elem]
        if indices:
            # 분자 외곽에 노출된 원자를 우선 선택 (질량중심에서 가장 먼 원자)
            com = atoms.get_center_of_mass()
            dists = [np.linalg.norm(atoms.positions[i] - com) for i in indices]
            return indices[int(np.argmax(dists))]
    return 0

def build_zn_solvation_cluster(additive: Atoms) -> Atoms:
    """[Zn(H2O)5(Additive)]2+ 클러스터 조립"""
    add_copy = additive.copy()
    coord_idx = find_coordinating_atom_idx(add_copy)
    
    # 배위 원자를 원점(0,0,0)으로 이동 후 Zn2+를 (0, 0, -2.05 A)에 배치
    shift = -add_copy.positions[coord_idx]
    add_copy.translate(shift)
    
    # 첨가제 질량중심이 +z 방향을 향하도록 회전 정렬
    com = add_copy.get_center_of_mass()
    if np.linalg.norm(com) > 1e-3:
        add_copy.rotate(com, [0, 0, 1])
        add_copy.translate(-add_copy.positions[coord_idx])

    cluster = Atoms('Zn', positions=[[0.0, 0.0, -2.05]])
    cluster += add_copy

    # 나머지 5개 배위 자리에 물 분자 배치 (팔면체 근사: -z, +x, -x, +y, -y)
    water_dirs = [
        np.array([0.0, 0.0, -1.0]),
        np.array([1.0, 0.0, 0.0]),
        np.array([-1.0, 0.0, 0.0]),
        np.array([0.0, 1.0, 0.0]),
        np.array([0.0, -1.0, 0.0]),
    ]
    zn_pos = np.array([0.0, 0.0, -2.05])
    for d in water_dirs:
        w = molecule('H2O')
        # O 원자가 Zn 쪽을 향하도록 정렬 (ASE H2O의 0번 인덱스가 O)
        w.translate(-w.positions[0])
        w_com = w.get_center_of_mass()
        if np.linalg.norm(w_com) > 1e-3:
            w.rotate(w_com, d)
            w.translate(-w.positions[0])
        w.translate(zn_pos + d * 2.10)
        cluster += w

    cluster.center(vacuum=10.0)
    return cluster

def build_water_trimer_cluster(additive: Atoms) -> Atoms:
    """Additive + 2 H2O 클러스터 조립 (질량중심 바깥 방향으로 배치하여 겹침 방지)"""
    cluster = additive.copy()
    coord_idx = find_coordinating_atom_idx(cluster)
    target_pos = cluster.positions[coord_idx]
    com = cluster.get_center_of_mass()
    
    out_dir = target_pos - com
    norm = np.linalg.norm(out_dir)
    out_dir = out_dir / norm if norm > 1e-3 else np.array([1.0, 0.0, 0.0])
    ortho = np.cross(out_dir, np.array([0.0, 0.0, 1.0]))
    if np.linalg.norm(ortho) < 1e-3:
        ortho = np.cross(out_dir, np.array([0.0, 1.0, 0.0]))
    ortho /= np.linalg.norm(ortho)
    
    offsets = [out_dir * 2.8 + ortho * 1.4, out_dir * 2.8 - ortho * 1.4]
    for off in offsets:
        w = molecule('H2O')
        w.translate(-w.positions[0] + target_pos + off)
        cluster += w
    cluster.center(vacuum=10.0)
    return cluster

def build_zn_slab_adsorption(additive: Atoms) -> Atoms:
    """Zn(0001) 4x4x3 슬래브 위에 첨가제 흡착 구조 조립"""
    slab = hcp0001('Zn', size=(4, 4, 3), a=2.665, c=4.947, vacuum=12.0)
    add_copy = additive.copy()
    # 분자의 가장 낮은 z좌표를 0으로 맞춘 뒤 슬래브 위 2.3 A 높이에 배치
    add_copy.translate(-add_copy.get_center_of_mass())
    min_z = np.min(add_copy.positions[:, 2])
    add_copy.positions[:, 2] -= min_z
    
    slab_top_z = np.max(slab.positions[:, 2])
    center_xy = slab.cell.diagonal()[:2] / 2.0
    add_copy.translate([center_xy[0], center_xy[1], slab_top_z + 2.3])
    
    combined = slab + add_copy
    combined.pbc = [True, True, True]
    return combined

def build_references(out_dir: str):
    """기준 에너지 계산용 참조 구조(H2O, [Zn(H2O)6]2+, Zn(0001) slab) 생성"""
    ref_dir = os.path.join(out_dir, "references")
    os.makedirs(ref_dir, exist_ok=True)
    
    # 1. H2O
    w = molecule('H2O')
    w.center(vacuum=10.0)
    write(os.path.join(ref_dir, "H2O.extxyz"), w)
    
    # 2. [Zn(H2O)6]2+
    zn_hex = Atoms('Zn', positions=[[0.0, 0.0, 0.0]])
    dirs = [[1,0,0], [-1,0,0], [0,1,0], [0,-1,0], [0,0,1], [0,0,-1]]
    for d in dirs:
        d_arr = np.array(d, dtype=float)
        wi = molecule('H2O')
        wi.translate(-wi.positions[0])
        w_com = wi.get_center_of_mass()
        wi.rotate(w_com, d_arr)
        wi.translate(-wi.positions[0] + d_arr * 2.10)
        zn_hex += wi
    zn_hex.center(vacuum=10.0)
    write(os.path.join(ref_dir, "Zn_H2O_6.extxyz"), zn_hex)
    
    # 3. Zn(0001) slab
    slab = hcp0001('Zn', size=(4, 4, 3), a=2.665, c=4.947, vacuum=12.0)
    slab.pbc = [True, True, True]
    write(os.path.join(ref_dir, "Zn_slab.extxyz"), slab)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", required=True, help="Path to candidates JSON")
    parser.add_argument("--out_dir", default="structures", help="Output directory")
    args = parser.parse_args()

    build_references(args.out_dir)

    with open(args.candidates, "r", encoding="utf-8") as f:
        candidates = json.load(f)

    for item in candidates:
        cid = item["id"]
        smiles = item["smiles"]
        c_dir = os.path.join(args.out_dir, cid)
        os.makedirs(c_dir, exist_ok=True)
        try:
            iso = smiles_to_ase(smiles, cid)
            h2o_clus = build_water_trimer_cluster(iso)
            zn_clus = build_zn_solvation_cluster(iso)
            ads_sys = build_zn_slab_adsorption(iso)

            write(os.path.join(c_dir, "isolated.extxyz"), iso)
            write(os.path.join(c_dir, "h2o_cluster.extxyz"), h2o_clus)
            write(os.path.join(c_dir, "zn_cluster.extxyz"), zn_clus)
            write(os.path.join(c_dir, "zn_ads.extxyz"), ads_sys)
            print(f"[OK] Built structures for {cid} ({item['name']})")
        except Exception as e:
            print(f"[FAIL] {cid}: {e}")

if __name__ == "__main__":
    main()
