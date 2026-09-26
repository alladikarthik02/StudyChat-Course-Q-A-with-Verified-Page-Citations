"""Score the same cached outputs with quotes off/on, without making API calls."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from studychat.evaluation import load_bundle, require_official_evidence, score  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--quotes", choices=["off", "on"], required=True)
    parser.add_argument("--split", choices=["dev", "heldout"], default="heldout")
    parser.add_argument("--exact-only", action="store_true")
    parser.add_argument("--official", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    bundle = load_bundle(args.dataset, args.corpus, args.records, args.manifest)
    if args.official:
        if args.split != "heldout":
            parser.error("Official reports must score heldout")
        require_official_evidence(bundle)
    result = score(bundle, args.split, args.quotes, exact_only=args.exact_only)
    result["records_sha256"] = bundle.manifest.records_sha256
    output = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output)
    print(output)


if __name__ == "__main__":
    main()
