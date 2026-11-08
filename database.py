import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# DATABASE_URL = "postgresql://postgres:root@localhost/wishlist"

# docker run -d \
#   --name postgres \
#   -e POSTGRES_USER=postgres\
#   -e POSTGRES_PASSWORD=root \
#   -e POSTGRES_DB=wishlist \
#   -p 5432:5432 \
#   postgres:15-alpine


load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME")

# sslmode береться із середовища: хмарному Postgres потрібен require, а локальний контейнер
# і сервіс у CI працюють без SSL. Раніше тут був жорстко заданий require — підключитися можна
# було лише до бази із SSL. DATABASE_URL, якщо заданий, має пріоритет (його задає docker-compose).
DB_SSLMODE = os.getenv("DB_SSLMODE", "prefer")
DATABASE_URL = os.getenv("DATABASE_URL") or (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}?sslmode={DB_SSLMODE}"
)

print(f"DB_USER: {DB_USER}")
print(f"DB_HOST: {DB_HOST}")
print(f"DB_NAME: {DB_NAME}")
print(f"DB_PASSWORD: {'SET' if DB_PASSWORD else 'NOT SET'}")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
