"""Load the 10 sample parking spaces into the database.

They match the drawings in ``parking_images/`` (run ``python -m scripts.generate_samples``
first if those images are missing).

Run from the project root:
    python -m scripts.seed_sample_spaces            # only if the table is empty
    python -m scripts.seed_sample_spaces --reset    # delete existing spaces first
"""

import argparse

from app import crud
from app.database import SessionLocal, init_db
from app.models import ParkingSpace
from app.schemas import ParkingSpaceCreate
from scripts.generate_samples import SAMPLE_SPACES


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reset", action="store_true", help="delete existing spaces first")
    args = parser.parse_args()

    init_db()
    with SessionLocal() as db:
        existing = crud.get_spaces(db)
        if existing and not args.reset:
            print(f"{len(existing)} spaces already exist. Use --reset to replace them.")
            return
        db.query(ParkingSpace).delete()
        db.commit()
        for space in SAMPLE_SPACES:
            crud.create_space(db, ParkingSpaceCreate(**space))
        print(f"Added {len(SAMPLE_SPACES)} sample parking spaces.")


if __name__ == "__main__":
    main()
