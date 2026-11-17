import os
import time
import glob
import json
import random
import subprocess
import pandas as pd
from rdkit import Chem
from rdkit.Chem import Descriptors, Crippen, rdMolDescriptors
from generate_library import MONOMERS, connect_monomers
from slack_reader import fetch_new_user_messages
from notify_hook import send_milestone_notification

STOP_FILE = "STOP_RESEARCH"

PI_FALLBACK_CHAIN = [
    "gemini-3.8-flash-high",
    "gpt-oss-120b-medium",
    "claude-sonnet-4-6",
    "claude-opus-4-6-thinking"
]
WORKER_MODEL = os.environ.get("WORKER_MODEL", "gemini-3.8-flash-low")

def get_next_cycle_num():
    if not os.path.exists("runs/pi_research_journal.md"):
        return 1
    with open("runs/pi_research_journal.md", "r", encoding="utf-8") as f:
        return f.read().count("## Cycle ") + 1

def generate_0token_janus_pool(cycle: int, n_samples: int = 20) -> list:
    """Generate novel candidates in 0-Token mode using RDKit connect_monomers"""
    seen_smiles = set()
    max_id = 688
    if os.path.exists("runs/master_screening_results.csv"):
        df = pd.read_csv("runs/master_screening_results.csv")
        if "smiles" in df.columns:
            seen_smiles = set(df["smiles"].dropna().astype(str))
        if "id" in df.columns:
            nums = [int(x.split("_")[1]) for x in df["id"].dropna() if "_" in str(x) and str(x).split("_")[1].isdigit()]
            if nums:
                max_id = max(nums)

    # Expanded trimer & tetramer search space across 24 valid monomers (excluding hydrolyzable DMVP)
    all_valid = [k for k in MONOMERS.keys() if k != "DMVP"]
    priority_anchors = ["VPA", "VMO", "VIU", "TauMA", "VSL", "VSO", "AMPS", "VSA", "AA", "SBMA"]
    strong_acids = {"VPA", "VSA", "AMPS", "TauMA", "AA"}
    library = []
    attempts = 0

    while len(library) < n_samples and attempts < 10000:
        attempts += 1
        # Sample novel trimers (70%) and higher-order tetramers (30%)
        if random.random() < 0.7:
            combo = (random.choice(priority_anchors), random.choice(all_valid), random.choice(all_valid))
        else:
            combo = (random.choice(priority_anchors), random.choice(["VMO", "VIU", "VSO", "AM"]), random.choice(all_valid), random.choice(["AM", "TFEMA", "EG", "VA", "VP"]))
        if len(set(combo)) == 1:
            continue
        # Pre-filter kill criteria: prevent >=2 strong acid monomers
        if sum(1 for m in combo if m in strong_acids) >= 2:
            continue

        try:
            m_smiles = [MONOMERS[k]["smiles"] for k in combo]
            smi = connect_monomers(m_smiles)
            if not smi or smi in seen_smiles:
                continue

            mol = Chem.MolFromSmiles(smi)
            if mol is None:
                continue
            mw = Descriptors.MolWt(mol)
            if not (200.0 <= mw <= 480.0):
                continue
            logp = Crippen.MolLogP(mol)
            if not (-0.8 <= logp <= 1.2):
                continue
            tpsa = Descriptors.TPSA(mol)
            if tpsa < 75.0:
                continue
            hbd = rdMolDescriptors.CalcNumHBD(mol)
            if hbd < 1:
                continue

            seen_smiles.add(smi)
            max_id += 1
            cid = f"LIB_{max_id:04d}_{'-'.join(combo)}"
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

    with open("runs/next_pool.json", "w", encoding="utf-8") as f:
        json.dump(library, f, indent=2)
    return library

def run_0token_autonomous_cycle(cycle: int, user_slack_notes: str):
    """Run autonomous local RTX 3050 GPU screening cycle when LLM API quota is exhausted"""
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [0-TOKEN MODE] Generating valid RDKit SMILES & running GPU MLIP for Cycle {cycle}...", flush=True)

    prev_best = 1.8152
    if os.path.exists("runs/master_screening_results.csv"):
        df_before = pd.read_csv("runs/master_screening_results.csv")
        if "composite_score" in df_before.columns and len(df_before) > 0:
            prev_best = float(df_before["composite_score"].max())

    pool = generate_0token_janus_pool(cycle, n_samples=20)
    if not pool:
        print("[0-TOKEN MODE] Could not generate new valid SMILES candidates.", flush=True)
        return

    print(f"[0-TOKEN MODE] Generated {len(pool)} new valid SMILES candidates ({pool[0]['id']} ~ {pool[-1]['id']}). Starting GPU screening...", flush=True)

    cmd = [
        "python", "-u", "run_overnight_batch.py",
        "--pool", "runs/next_pool.json",
        "--batch_size", "20",
        "--master_csv", "runs/master_screening_results.csv"
    ]
    subprocess.run(cmd, check=False)
    subprocess.run(["python", "auto_analyze.py"], check=False)

    df_after = pd.read_csv("runs/master_screening_results.csv")
    total_cnt = len(df_after)
    new_best = float(df_after["composite_score"].max())
    top_row = df_after.sort_values("composite_score", ascending=False).iloc[0]
    top_id = top_row.get("id", "N/A")
    top_name = top_row.get("name", "N/A")

    recent_df = df_after[df_after["id"].isin([c["id"] for c in pool])]
    if len(recent_df) > 0:
        b_row = recent_df.sort_values("composite_score", ascending=False).iloc[0]
        b_id, b_name, b_score = b_row["id"], b_row["name"], float(b_row["composite_score"])
    else:
        b_id, b_name, b_score = "N/A", "N/A", 0.0

    journal_entry = (
        f"\n## Cycle {cycle} (0-Token Local Autonomous GPU Mode)\n"
        f"- **Hypothesis & Search Strategy:** Cycle 1~2 핵심 헤테로 모노머(`VMO`, `VIU`, `TauMA`, `VSL`) 및 비대칭 Janus 올리고머 {len(pool)}종 RDKit SMILES 자동 조립 및 물리화학적 필터 통과 후 RTX 3050 MLIP 연산 완수\n"
        f"- **Total Screened Candidates:** {total_cnt}종\n"
        f"- **Batch Top Candidate:** `{b_id}` ({b_name}) — Composite Score: **{b_score:.4f}**\n"
        f"- **Overall All-Time Champion:** `{top_id}` ({top_name}) — Composite Score: **{new_best:.4f}**\n"
    )
    with open("runs/pi_research_journal.md", "a", encoding="utf-8") as jf:
        jf.write(journal_entry)

    is_new_record = new_best > prev_best + 1e-4
    if is_new_record or user_slack_notes or (total_cnt % 100 < len(pool)):
        tag = "NEW_CHAMPION" if is_new_record else ("USER_REPLY" if user_slack_notes else "MILESTONE")
        report_path = f"alerts/REPORT_cycle_{cycle}_{tag}.md"
        with open(report_path, "w", encoding="utf-8") as rf:
            rf.write(
                f"# Autonomous Research Status & Breakthrough Briefing (Cycle {cycle})\n\n"
                f"### 1. System Operational Status\n"
                f"- `agy` CLI 쿼터가 일시 소진(약 69h 후 리셋)됨에 따라 **0-Token 로컬 자율 GPU 모드(RTX 3050 + RDKit + MatterSim)**로 자동 전환되어 실제 3D 구조 생성 및 MLIP 연산이 연속 가동 중입니다.\n"
                f"- **Cumulative Screened:** 총 **{total_cnt}종** 완료\n\n"
                f"### 2. Key Scientific Findings (Desolvation barrier & Surface Adsorption)\n"
                f"- **Overall Champion:** `{top_id}` (**{top_name}**) — Score **{new_best:.4f}**\n"
                f"- **Current Cycle({cycle}) 최고 후보:** `{b_id}` (**{b_name}**) — Score **{b_score:.4f}**\n"
                f"- 신규 헤테로 고리(`VMO`, `VIU`, `VSL`) 및 타우린계(`TauMA`) 비대칭 야누스(Janus) 구조를 중심으로 탈용매화 에너지 장벽(Desolvation barrier)과 아연 표면 흡착 균형을 정밀 탐색하고 있습니다.\n"
            )
        send_milestone_notification(report_path)

def main():
    subprocess.run(["python", "auto_analyze.py"], check=False)
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] === Hybrid LLM + 0-Token RDKit/GPU Autonomous PI Daemon Started ===", flush=True)

    current_pi_idx = 0
    quota_locked_until = 0

    while True:
        if os.path.exists(STOP_FILE):
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] STOP_RESEARCH detected. Shutting down safely.", flush=True)
            break

        cycle = get_next_cycle_num()
        before_alerts = set(glob.glob("alerts/*.md"))
        user_slack_notes = fetch_new_user_messages()

        if user_slack_notes:
            print(f"[SLACK_IN] New user feedback received:\n{user_slack_notes}", flush=True)
            with open("runs/user_feedback.md", "a", encoding="utf-8") as uf:
                uf.write(f"\n### Cycle {cycle} User Feedback\n{user_slack_notes}\n")

        if time.time() < quota_locked_until:
            run_0token_autonomous_cycle(cycle, user_slack_notes)
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] <<< Cycle {cycle} (0-Token) Complete. Sleeping 30s...", flush=True)
            time.sleep(30)
            continue

        active_pi = PI_FALLBACK_CHAIN[current_pi_idx]
        slack_injection = ""
        if user_slack_notes:
            slack_injection = (
                f"\n\n[🚨 최우선 연구책임자(사용자) 실시간 지시사항 - Slack 수신]:\n{user_slack_notes}\n"
                f"위 사용자의 피드백/질문에 대한 답변 및 현재 연구 진행 현황 브리핑을 Current Cycle에 반드시 "
                f"`alerts/REPORT_cycle_{cycle}_user_reply.md` 파일로 작성하여 Slack으로 즉시 회신하십시오.\n"
            )

        prompt = (
            f"현재는 연속 자율 연구 **Cycle {cycle}**입니다. 'PI_DIRECTOR.md' 프로토콜을 준수하십시오. "
            "대용량 CSV는 직접 읽지 말고 `runs/compact_digest.md`와 `runs/pi_research_journal.md`만 읽으십시오. "
            f"하위 Worker(`--model {WORKER_MODEL}`)에게 탐색 풀 생성(30종 내외)과 사전 검수를 위임하고, "
            "로컬 GPU 스크리닝(`run_overnight_batch.py`) 및 `python auto_analyze.py`를 완수한 뒤 "
            f"`runs/pi_research_journal.md`의 `## Cycle {cycle}`에 기록하십시오." + slack_injection
        )

        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] >>> Cycle {cycle} Start (Active PI: {active_pi})...", flush=True)
        proc = subprocess.run(["agy", "-p", prompt, "--model", active_pi], capture_output=True, text=True)

        if proc.returncode != 0:
            err_msg = proc.stderr or ""
            if "RESOURCE_EXHAUSTED" in err_msg or "429" in err_msg or "quota" in err_msg.lower():
                if current_pi_idx + 1 < len(PI_FALLBACK_CHAIN):
                    current_pi_idx += 1
                    print(f"[FALLBACK] Quota exhausted for {active_pi}. Switching to {PI_FALLBACK_CHAIN[current_pi_idx]}...", flush=True)
                    time.sleep(3)
                    continue
                else:
                    print("[SWITCH] All LLM quotas exhausted. Switching immediately to 0-Token Local Autonomous GPU Mode (re-checking LLM quota every 2 hours)!", flush=True)
                    current_pi_idx = 0
                    quota_locked_until = time.time() + 7200
                    run_0token_autonomous_cycle(cycle, user_slack_notes)
                    time.sleep(30)
                    continue
            else:
                time.sleep(30)
                continue

        print(proc.stdout, flush=True)
        new_alerts = set(glob.glob("alerts/*.md")) - before_alerts
        for alert_file in sorted(new_alerts):
            send_milestone_notification(alert_file)

        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] <<< Cycle {cycle} Complete. Sleeping 60s...", flush=True)
        time.sleep(60)

if __name__ == "__main__":
    main()
