
from app.db.database import Base, engine, SessionLocal
from app.models.parking import ParkingLocation


def initialize_database():

    # Create database tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        existing = db.query(ParkingLocation).count()

        if existing == 0:

            locations = [
                ParkingLocation(
                    name="MG Road",
                    latitude=12.9758,
                    longitude=77.6060,
                    total_spaces=120
                ),
                ParkingLocation(
                    name="Mall",
                    latitude=12.9716,
                    longitude=77.5946,
                    total_spaces=100
                )
            ]

            db.add_all(locations)
            db.commit()

            print("Parking locations inserted successfully!")

        else:
            print("Parking locations already exist!")

    finally:
        db.close()


if __name__ == "__main__":
    initialize_database()
