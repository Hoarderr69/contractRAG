"""
Stress-test the RAG answers for CORRECTNESS and CONSISTENCY.

For each demo question it runs N times in two modes:
  - fresh:        no chat history (cold every time)
  - with-history: questions run sequentially in one growing conversation

Each answer is validated against expected keyword groups (ground truth), and the
route + pass/fail is checked for stability across the N runs. Temperature is 0,
so any variation comes from retrieval, not generation.

Run (with your local .env / venv):
    python -m app.scripts.stress_test_questions
    RUNS=5 python -m app.scripts.stress_test_questions
"""

import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.rag.query_service import answer_question

RUNS = int(os.getenv("RUNS", "3"))

SOLAR  = "Solar_System_Operations_and_Maintenance_Agreement_1"
NYISO  = "NYISO-NGrd-NxtEraEPCAgt-EmpireStateLn_EPC_1_1"
LFGTE  = "LFGTE_Duke_Energy_power_purchase_agrmnt_1"
EDISON = "Edison_NYPA_OandM_Contract_1"
SOCAL  = "SoCal_EPC"

# Each "must" is a list of groups; a group is alternatives (OR), all groups AND.
QUESTIONS = [
    {
        "q": "What sections are available in the SoCal EPC contract?",
        "contract_ids": [SOCAL],
        "must": [["article", "exhibit"]],
    },
    {
        "q": "What termination or default remedies are mentioned in the LFGTE Duke Energy power purchase agrmnt?",
        "contract_ids": [LFGTE],
        "must": [["termination"], ["default", "remed"]],
    },
    {
        "q": "What are the ASO estimated total cost terms in the NYISO/NextEra EPC agreement?",
        "contract_ids": [NYISO],
        "must": [["461,340", "461340"]],
    },
    {
        "q": ("within O&M contract the vendor Omnidian has billed for engineering services "
              "at the rate of $400/hr for 10 hours $4000, Is this correct?"),
        "contract_ids": [SOLAR],
        "must": [["250"], ["2,500", "2500"], ["incorrect", "exceed", "not correct"]],
    },
    {
        "q": ("NextEra has billed $580,000 for ASO Estimated Total Costs. Is this amount accurate "
              "per the EPC contract terms, or does it breach any pricing or scope clauses? "
              "If so how can I proceed"),
        "contract_ids": [NYISO],
        "must": [["566,780", "461,340", "566780", "461340"], ["exceed", "breach", "potential"]],
    },
    {
        "q": "What inspection or compliance duties are mentioned in the Solar System Operations and Maintenance agreement?",
        "contract_ids": [SOLAR],
        "must": [["inspect"], ["inverter", "array", "balance", "module"]],
    },
    {
        "q": "If Con Edison does not inspect spill areas weekly or maintain logs per the SPCC plan, is there a breach and if so what can happen?",
        "contract_ids": [EDISON],
        "must": [["breach"], ["spcc", "spill"]],
    },
]


def _failed_groups(answer: str, must) -> list:
    a = (answer or "").lower()
    return [g for g in must if not any(tok.lower() in a for tok in g)]


def _run(item, history):
    res = answer_question(
        question=item["q"],
        contract_id=None,
        contract_ids=item.get("contract_ids"),
        chat_history=list(history) if history else None,
    )
    failed = _failed_groups(res.get("answer", ""), item["must"])
    return res.get("route", "?"), ("PASS" if not failed else f"FAIL{failed}"), res.get("answer", "")


def main():
    print("=" * 78)
    print(f"RAG stress test — {RUNS} runs/question/mode")
    print("=" * 78)

    overall_fail = 0

    for mode in ("fresh", "with-history"):
        print(f"\n######## MODE: {mode} ########")
        history = []
        for item in QUESTIONS:
            routes, verdicts, last_answer = [], [], ""
            for _ in range(RUNS):
                hist = history if mode == "with-history" else None
                try:
                    route, verdict, ans = _run(item, hist)
                except Exception as exc:  # noqa: BLE001
                    route, verdict, ans = "ERROR", f"EXC:{type(exc).__name__}", ""
                    traceback.print_exc()
                routes.append(route)
                verdicts.append(verdict)
                last_answer = ans or last_answer

            if mode == "with-history" and last_answer:
                history.append({"role": "user", "content": item["q"]})
                history.append({"role": "assistant", "content": last_answer[:1500]})

            ok = all(v == "PASS" for v in verdicts)
            consistent = len(set(verdicts)) == 1
            route_stable = len(set(routes)) == 1
            overall_fail += 0 if ok else 1

            mark = "OK " if ok else "XX "
            cons = "consistent" if consistent else f"INCONSISTENT {verdicts}"
            rt = routes[0] if route_stable else f"ROUTE-VARIES {routes}"
            print(f"  {mark} {item['q'][:48]:50} | {rt:10} | {cons}")
            if not ok:
                print(f"        first-fail detail: {verdicts}")

    print("\n" + "=" * 78)
    print(f"RESULT: {'ALL GREEN' if overall_fail == 0 else f'{overall_fail} question(s) had failures'}")
    print("=" * 78)


if __name__ == "__main__":
    main()
