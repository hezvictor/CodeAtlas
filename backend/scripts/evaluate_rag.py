import argparse
import json
from dataclasses import asdict
from pathlib import Path

from app.evaluation import run_offline_evaluation


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Run the offline lexical RAG baseline")
    parser.add_argument("--source", type=Path, default=root / "docs" / "hzvictory模板-最终版.md")
    parser.add_argument("--evaluation", type=Path, default=root / "docs" / "rag-evaluation" / "hzvictory-template-v1.md")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    results = run_offline_evaluation(args.source, args.evaluation, args.top_k)
    print(json.dumps([asdict(result) for result in results], ensure_ascii=False, indent=2))
    hits = sum(result.top_k_hit for result in results if result.case_id not in {"R19", "R20"})
    total = sum(result.case_id not in {"R19", "R20"} for result in results)
    print(f"\nTop-{args.top_k} hit rate: {hits}/{total} ({hits / total:.1%})")


if __name__ == "__main__":
    main()
