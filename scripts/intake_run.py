import argparse
import json

from hp_motor.ingest.preprocessor import Preprocessor
from hp_motor.pipelines.run_analysis import SovereignOrchestrator


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True, help="input file path (csv/xlsx/json)")
    ap.add_argument("--kind", required=True, choices=["event", "fitness"])
    ap.add_argument("--analysis_type", default="generic")
    ap.add_argument("--match_id", default=None)
    args = ap.parse_args()

    pp = Preprocessor(data_root="data")
    res = pp.preprocess(args.path, kind=args.kind, match_id=args.match_id)

    print(f"[OK] canonical: {res.canonical_path}")
    print(f"[OK] audit:     {res.audit_path}")

    # Only run analysis on event kind (default)
    if args.kind == "event":
        orch = SovereignOrchestrator()
        out = orch.execute(res.canonical_df, analysis_type=args.analysis_type, has_event=True, has_spatial=False)
        print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()