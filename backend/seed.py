"""
Seed script: ingests the sample HR/IT documents into the database.
Run with: python seed.py
"""
import asyncio
import glob
import os

from app.db.database import SessionLocal, init_db
from app.services.document_service import ingest_document
from app.repositories import document_repo
from app.services.admin_bootstrap import seed_admin_from_environment

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "data", "sample_docs")

CATEGORY_BY_FILE = {
    "leave_policy.txt": "HR",
    "expense_reimbursement.txt": "Finance",
    "it_password_reset.txt": "IT",
    "remote_work_policy.md": "HR",
}


async def main():
    init_db()
    db = SessionLocal()
    try:
        seed_admin_from_environment(db)
        existing = {d.filename for d in document_repo.list_documents(db)}
        for path in sorted(glob.glob(os.path.join(SAMPLE_DIR, "*"))):
            filename = os.path.basename(path)
            if filename in existing:
                print(f"skip (already ingested): {filename}")
                continue
            with open(path, "rb") as f:
                raw = f.read()
            category = CATEGORY_BY_FILE.get(filename, "General")
            doc = await ingest_document(db, filename, raw, category)
            print(f"ingested: {filename} -> {doc.chunk_count} chunks ({doc.status})")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
