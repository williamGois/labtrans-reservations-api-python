from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Location, Room


def seed_initial_data(db: Session) -> None:
    if db.scalar(select(Location).limit(1)) is not None:
        return

    matriz = Location(name="Matriz Florianopolis", address="Rodovia SC-401, Florianopolis - SC")
    sao_jose = Location(name="Filial Sao Jose", address="Avenida Presidente Kennedy, Sao Jose - SC")
    remota = Location(name="Filial Remota", address="Ambiente remoto")

    db.add_all([matriz, sao_jose, remota])
    db.flush()

    db.add_all(
        [
            Room(location_id=matriz.id, name="Sala Azul", capacity=8, active=True),
            Room(location_id=matriz.id, name="Sala Verde", capacity=12, active=True),
            Room(location_id=sao_jose.id, name="Sala Executiva", capacity=10, active=True),
            Room(location_id=remota.id, name="Auditorio", capacity=60, active=True),
        ]
    )
    db.commit()


def run_seed() -> None:
    db = SessionLocal()
    try:
        seed_initial_data(db)
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
