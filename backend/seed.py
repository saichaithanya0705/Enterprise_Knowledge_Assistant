"""
Seed script: ingests the sample HR/IT documents into the database.
Run with: python seed.py
"""
import asyncio
import glob
import os

from app.db.database import SessionLocal, init_db
from app.services.document_service import ingest_document
from app.repositories import document_repo, user_repo
from app.core.security import hash_password, is_password_strong

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "data", "sample_docs")

CATEGORY_BY_FILE = {
    "leave_policy.txt": "HR",
    "expense_reimbursement.txt": "Finance",
    "it_password_reset.txt": "IT",
    "remote_work_policy.md": "HR",
}


def seed_admin_from_environment(db):
    """Create an initial admin only when explicit credentials are supplied."""
    email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
    name = os.getenv("BOOTSTRAP_ADMIN_NAME", "Administrator").strip() or "Administrator"
    if not email and not password:
        return
    if not email or not password:
        raise RuntimeError("Set both BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD.")
    if not is_password_strong(password):
        raise RuntimeError("BOOTSTRAP_ADMIN_PASSWORD does not meet the password policy.")
    if user_repo.get_by_email(db, email):
        print(f"skip (admin already exists): {email}")
        return
    user_repo.create_user(db, name, email, hash_password(password), role="ADMIN")
    print(f"created bootstrap admin: {email}")


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
