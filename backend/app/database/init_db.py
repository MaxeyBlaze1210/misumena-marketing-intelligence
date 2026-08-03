from app.database.database import Base, engine

# Import every model here
from app.models.release import Release


def init_db():
    Base.metadata.create_all(bind=engine)