import os
import subprocess
import time

def run_cmd(cmd_list, desc):
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] >>> START: {desc}", flush=True)
    subprocess.run(cmd_list, check=True)
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] >>> DONE:  {desc}", flush=True)

def main():
    # Automated pipeline step
    if not os.path.exists("runs/library_pool.json"):
        run_cmd(["python", "generate_library.py", "--size", "400", "--out", "runs/library_pool.json"],
                "Generate 400 initial polymer candidates")

    run_cmd(["python", "-u", "run_overnight_batch.py", "--pool", "runs/library_pool.json",
             "--batch_size", "25", "--master_csv", "runs/master_screening_results.csv"],
            "Round 1 High-Throughput MLIP Screening (400 candidates)")

    # Automated pipeline step
    analyst_prompt = (
        "First read `.gemini/agents/analyst.md` and strictly follow its persona and guidelines. Analyze `runs/master_screening_results.csv` and `runs/pareto_front_candidates.csv` to "
        "identify Pareto-optimal candidates across Track A (interfacial adsorption), Track B (desolvation), and Track C (free-water suppression), "
        "and save monomer backbone-functional group structure-activity relationship (SAR) insights to `runs/round1_analysis.md`."
    )
    run_cmd(["agy", "-p", analyst_prompt, "--mode", "auto"],
            "Agent 1 (sar-analyst): Pareto & SAR Analysis")

    # Automated pipeline step
    validator_prompt = (
        "First read `.gemini/agents/validator.md` and strictly follow its persona and guidelines. Read `runs/round1_analysis.md` and `runs/pareto_front_candidates.csv`, "
        "and critically evaluate the selected top candidates for aqueous solubility, reductive stability against a Zn anode (-0.76 V), and synthetic accessibility. "
        "Save unstable structures to eliminate and chemical design guidelines for Round 2 exploration in `runs/round1_critique.md`."
    )
    run_cmd(["agy", "-p", validator_prompt, "--mode", "auto"],
            "Agent 2 (electrochemical-validator): Electrochemical & Solubility Critique")

    # Automated pipeline step
    explorer_prompt = (
        "First read `.gemini/agents/explorer.md` and strictly follow its persona and guidelines. Incorporate both the high-performing structural patterns from `runs/round1_analysis.md` and the flaw critiques from `runs/round1_critique.md`. "
        "Add 4 novel functional group/backbone monomers not previously present to the `MONOMERS` dictionary in `generate_library.py`, "
        "and run `python generate_library.py --size 200 --seed 99 --out runs/library_pool_v2.json` in the terminal to "
        "generate the Round 2 evolutionary candidate pool (`runs/library_pool_v2.json`)."
    )
    run_cmd(["agy", "-p", explorer_prompt, "--mode", "auto"],
            "Agent 3 (polymer-explorer): Monomer Expansion & Round 2 Pool Generation")

    # Automated pipeline step
    if os.path.exists("runs/library_pool_v2.json"):
        run_cmd(["python", "-u", "run_overnight_batch.py", "--pool", "runs/library_pool_v2.json",
                 "--batch_size", "25", "--master_csv", "runs/master_screening_results.csv"],
                "Round 2 Evolutionary MLIP Screening (200 candidates)")

    # Automated pipeline step
    final_prompt = (
        "Synthesize the combined Round 1 and Round 2 `runs/master_screening_results.csv`, the latest `runs/pareto_front_candidates.csv`, "
        "and `runs/round1_critique.md` to write `overnight_discovery_report.md` containing the final Top-5 candidates improved over baselines (EG, PEG3) and "
        "recommendations for follow-up cluster DFT validation."
    )
    run_cmd(["agy", "-p", final_prompt, "--mode", "auto"],
            "Final Report Generation")

if __name__ == "__main__":
    main()
