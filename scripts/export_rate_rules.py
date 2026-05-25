#!/usr/bin/env python3
"""Export rate_rules table to JSON for pre-import backup / rollback."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.rate_rule import RateRule


def _json_default(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Unsupported type: {type(value)!r}")


def export_rate_rules(output_path: Path) -> int:
    db = SessionLocal()
    try:
        rules = db.scalars(select(RateRule).order_by(RateRule.created_at)).all()
        payload = {
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "table": "rate_rules",
            "row_count": len(rules),
            "rows": [
                {column.name: getattr(rule, column.name) for column in RateRule.__table__.columns}
                for rule in rules
            ],
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, default=_json_default), encoding="utf-8")
        return len(rules)
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default=str(ROOT / "backups" / f"rate_rules_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"),
        help="Path for JSON export (default: backups/rate_rules_<timestamp>.json)",
    )
    args = parser.parse_args()
    count = export_rate_rules(Path(args.output))
    print(f"Exported {count} rate_rules rows to {args.output}")


if __name__ == "__main__":
    main()
