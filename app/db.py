from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from settings import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
