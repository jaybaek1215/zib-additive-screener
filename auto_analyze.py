import os
import pandas as pd
from rdkit import Chem
from rdkit.Chem import Descriptors

def check_chem_flags(smi: str) -> str:
    mol = Chem.MolFromSmiles(smi)
    if not mol:
        return "INVALID_SMILES"
    flags = []
    # Detect carboxylic ester bonds prone to hydrolysis in locally alkaline (HER) environments (carbamate N-COO passes due to superior hydrolytic stability)
    if mol.HasSubstructMatch(Chem.MolFromSmarts("[#6][CX3](=[OX1])[OX2][#6]")):
        flags.append("Ester(HydrolysisRisk)")
    # Detect phosphonate ester P(=O)(OR) bonds
    if mol.HasSubstructMatch(Chem.MolFromSmarts("P(=O)(O[#6])")):
        flags.append("PhosphonateEster(HydrolysisRisk)")
    logp = Descriptors.MolLogP(mol)
    if logp > 1.2:
        flags.append(f"HighLogP({logp:.2f})")
    return ", ".join(flags) if flags else "CLEAN"

def main():
    master_csv = "runs/master_screening_results.csv"
    pareto_csv = "runs/pareto_front_candidates.csv"
    if not os.path.exists(master_csv):
        print("No master_screening_results.csv found yet.")
        return

    df = pd.read_csv(master_csv)
    passed = df[df["status"] == "PASS"].copy()
    warned = df[df["status"] != "PASS"]

    passed["chem_audit"] = passed["smiles"].apply(check_chem_flags)
    clean_passed = passed[
        (passed["chem_audit"] == "CLEAN") &
        (passed["dE_exchange_eV"] >= -1.6) &
        (passed["dE_exchange_eV"] <= -0.3)
    ].sort_values(by="composite_score", ascending=False)

    lines = [
        "# Compact Screening Digest (Zero-Token Auto-Generated)",
        f"- **Total Screened:** {len(df)} | **PASS:** {len(passed)} ({len(passed)/max(len(df),1)*100:.1f}%) | **WARN:** {len(warned)}",
        f"- **Kill-Criteria Clean & Qualified:** {len(clean_passed)} candidates",
        "\n## Top-10 Qualified Clean Champions",
        "| Rank | ID | Score | dE_hbond | dE_ex | dE_ads | SMILES |",
        "| :--- | :--- | :---: | :---: | :---: | :---: | :--- |"
    ]

    for idx, (_, r) in enumerate(clean_passed.head(10).iterrows(), 1):
        lines.append(
            f"| {idx} | `{r['id']}` | **{r['composite_score']:.4f}** | "
            f"{r['dE_hbond_eV']:.3f} | {r['dE_exchange_eV']:.3f} | {r['dE_ads_eV']:.3f} | `{r['smiles']}` |"
        )

    if os.path.exists(pareto_csv):
        p_df = pd.read_csv(pareto_csv)
        lines.append(f"\n## Current Global Pareto Front Count: {len(p_df)}")

    with open("runs/compact_digest.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("Generated token-saving digest: runs/compact_digest.md")

if __name__ == "__main__":
    main()
