from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from macro_market_intelligence_engine import (
    MacroIndicatorReading,
    MacroMarketIntelligenceEngine,
    MacroSnapshot,
    default_registry,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run macro market intelligence engine")
    parser.add_argument("--input", type=Path, required=True, help="Path to macro snapshot JSON")
    parser.add_argument("--format", choices=["json", "wechat"], default="wechat")
    return parser.parse_args()


def load_snapshot(path: Path) -> MacroSnapshot:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return MacroSnapshot(
        as_of=payload["as_of"],
        indicators=[MacroIndicatorReading(**item) for item in payload.get("indicators", [])],
        metadata=payload.get("metadata", {}),
    )


def main() -> None:
    args = parse_args()
    report = MacroMarketIntelligenceEngine(default_registry()).analyze(load_snapshot(args.input))
    if args.format == "json":
        print(json.dumps(report.to_json_dict(), ensure_ascii=False, indent=2))
    else:
        print(report.to_wechat_text())


if __name__ == "__main__":
    main()
