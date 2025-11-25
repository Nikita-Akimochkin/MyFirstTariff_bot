import os
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres_password@127.0.0.1:5432/botdb"
)

# Асинхронный движок
engine = create_async_engine(DATABASE_URL, echo=True)

# Сессии
async_session = async_sessionmaker(engine, expire_on_commit=False)
