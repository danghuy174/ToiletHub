import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Use the persistent PostgreSQL database provided by Replit (DATABASE_URL).
# This survives deploys/restarts, unlike a local SQLite file which is wiped
# every time an autoscale container is recreated.
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # SQLAlchemy needs the "postgresql://" scheme, not "postgres://".
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    # Fallback for local development without a database configured.
    engine = create_engine(
        "sqlite:///./worldcup_markets_v15.db",
        connect_args={"check_same_thread": False},
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
