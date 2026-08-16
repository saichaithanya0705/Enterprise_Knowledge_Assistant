"""Create the first production administrator without ingesting sample data."""

from app.db.database import SessionLocal, init_db
from seed import seed_admin_from_environment


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        seed_admin_from_environment(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
