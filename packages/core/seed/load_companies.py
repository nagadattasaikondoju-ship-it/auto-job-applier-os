"""Load the company registry from infra/seed/companies_india.csv (idempotent).

Usage: uv run python -m packages.core.seed.load_companies [path/to/companies.csv]
CSV columns: name, domain, careers_url, ats_type, ats_board_token
"""

import asyncio
import csv
import sys
from pathlib import Path

from sqlalchemy import select

from packages.core.database import async_session_maker
from packages.core.models.jobs import Company

DEFAULT_CSV = Path(__file__).resolve().parents[3] / "infra" / "seed" / "companies_india.csv"


async def load(path: Path) -> tuple[int, int]:
    created = updated = 0
    async with async_session_maker() as session:
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                name = (row.get("name") or "").strip()
                if not name:
                    continue
                normalized = name.lower()
                company = (
                    await session.execute(select(Company).where(Company.normalized_name == normalized))
                ).scalar_one_or_none()
                if company is None:
                    company = Company(name=name, normalized_name=normalized)
                    session.add(company)
                    created += 1
                else:
                    updated += 1
                company.domain = (row.get("domain") or "").strip()
                company.careers_url = (row.get("careers_url") or "").strip()
                company.ats_type = (row.get("ats_type") or "unknown").strip() or "unknown"
                company.ats_board_token = (row.get("ats_board_token") or "").strip() or None
                company.is_active = True
        await session.commit()
    return created, updated


if __name__ == "__main__":
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    c, u = asyncio.run(load(csv_path))
    print(f"Companies created: {c}, updated: {u}")
