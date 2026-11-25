from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings_singleton
settings = get_settings_singleton()

PG_URL = (settings.PG_URL or "").strip()
if not PG_URL: raise RuntimeError("DB URL is not set.")

pg_engine = create_async_engine(
    PG_URL,
    pool_pre_ping=True,
    pool_size=1,
    max_overflow=2,
    pool_recycle=1800,  # recycle before Aiven idle-times out connections
    echo=False,
)


async def get_pg_conn():
    async with pg_engine.connect() as conn, conn.begin(): # creates a connection and transaction
        yield conn  # ④ 把连接交给 endpoint
