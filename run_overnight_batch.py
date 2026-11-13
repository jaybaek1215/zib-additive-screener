import os
import json
import time
import argparse
import subprocess
import pandas as pd

def compute_pareto_front(df: pd.DataFrame) -> pd.DataFrame:
    """dE_hbond, dE_exchange(적정윈도우 근접도), dE_ads 3축 파레토 최적해 추출"""
    valid = df[df["status"] == "PASS"].copy()
    if valid.empty:
        return valid
    # 목표: dE_hbond 최소화(더 음수), |dE_exchange + 0.9| 최소화(이상적 탈용매화), dE_ads 최소화(더 음수)
    valid["ex_dist"] = (valid["dE_exchange_eV"] + 0.9).abs()
    
    is_pareto = []
    for i, row_i in valid.iterrows():
        dominated = False
        for j, row_j in valid.iterrows():
            if i == j:
                continue
            if (row_j["dE_hbond_eV"] <= row_i["dE_hbond_eV"] and
                row_j["ex_dist"] <= row_i["ex_dist"] and
                row_j["dE_ads_eV"] <= row_i["dE_ads_eV"] and
                (row_j["dE_hbond_eV"] < row_i["dE_hbond_eV"] or
                 row_j["ex_dist"] < row_i["ex_dist"] or
                 row_j["dE_ads_eV"] < row_i["dE_ads_eV"])):
                dominated = True
                break
        is_pareto.append(not dominated)
    valid["is_pareto"] = is_pareto
    return valid[valid["is_pareto"]].sort_values(by="composite_score", ascending=False)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", default="runs/library_pool.json")
    parser.add_argument("--batch_size", type=int, default=25)
    parser.add_argument("--master_csv", default="runs/master_screening_results.csv")
    args = parser.parse_args()

    with open(args.pool, "r", encoding="utf-8") as f:
        pool = json.load(f)

    done_ids = set()
    if os.path.exists(args.master_csv):
        existing_df = pd.read_csv(args.master_csv)
        done_ids = set(existing_df["id"].tolist())
        print(f"Resuming from checkpoint: {len(done_ids)} candidates already screened.")

    remaining = [c for c in pool if c["id"] not in done_ids]
    print(f"Total remaining candidates to screen: {len(remaining)}")

    start_time = time.time()
    for b_idx in range(0, len(remaining), args.batch_size):
        batch = remaining[b_idx : b_idx + args.batch_size]
        batch_num = (b_idx // args.batch_size) + 1
        batch_json = f"runs/tmp_batch_{batch_num}.json"
        batch_csv = f"runs/tmp_batch_{batch_num}.csv"

        with open(batch_json, "w", encoding="utf-8") as f:
            json.dump(batch, f, indent=2)

        print(f"\n--- Running Batch {batch_num} ({len(batch)} candidates) ---")
        subprocess.run(["python", "build_structures.py", "--candidates", batch_json, "--out_dir", "structures"], check=True)
        subprocess.run(["python", "screen_mlip.py", "--candidates", batch_json, "--struct_dir", "structures", "--out_csv", batch_csv], check=True)

        if os.path.exists(batch_csv):
            b_df = pd.read_csv(batch_csv)
            if os.path.exists(args.master_csv):
                m_df = pd.read_csv(args.master_csv)
                m_df = pd.concat([m_df, b_df], ignore_index=True)
            else:
                m_df = b_df
            m_df = m_df.sort_values(by="composite_score", ascending=False)
            m_df.to_csv(args.master_csv, index=False)

        # 임시 파일 정리
        for tmp in [batch_json, batch_csv]:
            if os.path.exists(tmp):
                os.remove(tmp)

        elapsed = (time.time() - start_time) / 60.0
        print(f"Batch {batch_num} saved to {args.master_csv} | Elapsed: {elapsed:.1f} min")

    # 전체 완료 후 파레토 최적해 저장
    if os.path.exists(args.master_csv):
        final_df = pd.read_csv(args.master_csv)
        pareto_df = compute_pareto_front(final_df)
        pareto_df.to_csv("runs/pareto_front_candidates.csv", index=False)
        print(f"\n[DONE] Total screened: {len(final_df)} | Pareto Front optimal candidates: {len(pareto_df)}")

if __name__ == "__main__":
    main()
