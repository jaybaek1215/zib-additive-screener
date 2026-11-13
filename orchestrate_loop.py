import os
import subprocess
import time

def run_cmd(cmd_list, desc):
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] >>> START: {desc}", flush=True)
    subprocess.run(cmd_list, check=True)
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] >>> DONE:  {desc}", flush=True)

def main():
    # 1. 1차 대규모 조합 라이브러리 생성 (400개) 및 배치 스크리닝
    if not os.path.exists("runs/library_pool.json"):
        run_cmd(["python", "generate_library.py", "--size", "400", "--out", "runs/library_pool.json"],
                "Generate 400 initial polymer candidates")

    run_cmd(["python", "-u", "run_overnight_batch.py", "--pool", "runs/library_pool.json",
             "--batch_size", "25", "--master_csv", "runs/master_screening_results.csv"],
            "Round 1 High-Throughput MLIP Screening (400 candidates)")

    # 2. Agent 1 (sar-analyst): 400개 결과 파레토 분석 및 중간 보고서 저장
    analyst_prompt = (
        "먼저 `.gemini/agents/analyst.md` 파일을 읽고 그 페르소나와 지침을 엄격히 따르라. `runs/master_screening_results.csv`와 `runs/pareto_front_candidates.csv`를 분석하여 "
        "Track A(계면 흡착), Track B(탈용매화), Track C(자유수 억제) 파레토 최적 후보군과 "
        "모노머 백본-작용기 상관관계(SAR) 인사이트를 `runs/round1_analysis.md` 파일로 저장하라."
    )
    run_cmd(["agy", "-p", analyst_prompt, "--mode", "auto"],
            "Agent 1 (sar-analyst): Pareto & SAR Analysis")

    # 3. Agent 2 (electrochemical-validator): Analyst 결과물에 대한 비판적 검증 및 결함 지적
    validator_prompt = (
        "먼저 `.gemini/agents/validator.md` 파일을 읽고 그 페르소나와 지침을 엄격히 따르라. `runs/round1_analysis.md`와 `runs/pareto_front_candidates.csv`를 읽고, "
        "선별된 상위 후보들의 수계 용해도, 아연 음극(-0.76 V) 환원 안정성, 합성 접근성을 비판적으로 검토하라. "
        "탈락시켜야 할 불안정 구조와 2차 탐색에서 보완해야 할 화학적 설계 가이드라인을 `runs/round1_critique.md`에 저장하라."
    )
    run_cmd(["agy", "-p", validator_prompt, "--mode", "auto"],
            "Agent 2 (electrochemical-validator): Electrochemical & Solubility Critique")

    # 4. Agent 3 (polymer-explorer): 분석 + 비판 피드백을 반영해 신규 모노머 확장 및 Round 2 풀 생성
    explorer_prompt = (
        "먼저 `.gemini/agents/explorer.md` 파일을 읽고 그 페르소나와 지침을 엄격히 따르라. `runs/round1_analysis.md`의 우수 구조 패턴과 `runs/round1_critique.md`의 결함 지적을 모두 반영하라. "
        "`generate_library.py`의 `MONOMERS` 딕셔너리에 기존에 없던 신규 작용기/백본 모노머 4종을 추가한 뒤, "
        "터미널에서 `python generate_library.py --size 200 --seed 99 --out runs/library_pool_v2.json`을 실행해 "
        "2차 진화 후보 풀(`runs/library_pool_v2.json`)을 생성하라."
    )
    run_cmd(["agy", "-p", explorer_prompt, "--mode", "auto"],
            "Agent 3 (polymer-explorer): Monomer Expansion & Round 2 Pool Generation")

    # 5. Round 2 진화 풀(200개) 즉시 MLIP 배치 스크리닝 (대기 시간 0초)
    if os.path.exists("runs/library_pool_v2.json"):
        run_cmd(["python", "-u", "run_overnight_batch.py", "--pool", "runs/library_pool_v2.json",
                 "--batch_size", "25", "--master_csv", "runs/master_screening_results.csv"],
                "Round 2 Evolutionary MLIP Screening (200 candidates)")

    # 6. 최종 종합 리포트 생성
    final_prompt = (
        "Round 1과 Round 2가 모두 통합된 `runs/master_screening_results.csv`와 최신 `runs/pareto_front_candidates.csv`, "
        "그리고 `runs/round1_critique.md`를 종합하여 기준선(EG, PEG3) 대비 개선된 최종 Top-5 후보와 "
        "후속 클러스터 DFT 검증 추천안을 담은 `overnight_discovery_report.md`를 작성하라."
    )
    run_cmd(["agy", "-p", final_prompt, "--mode", "auto"],
            "Final Report Generation")

if __name__ == "__main__":
    main()
