from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any


class PushMonitor:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def was_successful(self, mode: str, day: date) -> bool:
        state = self.load()
        return state.get(mode, {}).get(day.isoformat(), {}).get("status") == "success"

    def record_success(self, mode: str, day: date, report_path: str = "") -> None:
        self._record(mode, day, "success", report_path=report_path)

    def record_failure(self, mode: str, day: date, error: str) -> None:
        self._record(mode, day, "failure", error=error)

    def _record(self, mode: str, day: date, status: str, **extra: str) -> None:
        state = self.load()
        state.setdefault(mode, {})[day.isoformat()] = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            **extra,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
