#!/usr/bin/env python3
"""Add a staff user for Azure login (email must match Microsoft sign-in).

Usage:
  DATABASE_URL='postgresql+psycopg2://...' python scripts/add_production_user.py \\
    --email you@company.com --name "Your Name" --role admin

Roles: admin, manager, estimator, engineer
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.security import UserRole
from app.db.session import SessionLocal
from app.services.user_service import create_user


def main() -> int:
    parser = argparse.ArgumentParser(description="Add a staff user to the database")
    parser.add_argument("--email", required=True, help="Microsoft sign-in email")
    parser.add_argument("--name", required=True, help="Display name")
    parser.add_argument(
        "--role",
        required=True,
        choices=[r.value for r in UserRole if r != UserRole.CLIENT],
        help="Staff role",
    )
    args = parser.parse_args()

    if not os.environ.get("DATABASE_URL"):
        print("DATABASE_URL must be set", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        user = create_user(
            db,
            email=args.email,
            name=args.name,
            role=UserRole(args.role),
            is_active=True,
        )
        db.commit()
        print(f"Created user: {user.email} ({user.role})")
        return 0
    except ValueError as exc:
        db.rollback()
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
