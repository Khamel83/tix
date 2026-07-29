import asyncio
from typing import Callable, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from ticket_sniper.config import settings

engine = create_engine(
    f"sqlite:///{settings.DATABASE_PATH}",
    connect_args={"timeout": 5.0, "check_same_thread": False},
    pool_pre_ping=True
)

with engine.connect() as conn:
    conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
    conn.exec_driver_sql("PRAGMA foreign_keys=ON;")
    conn.exec_driver_sql("PRAGMA busy_timeout=5000;")

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
_db_lock = asyncio.Lock()

async def run_db_transaction(func: Callable[[Session], Any]) -> Any:
    async with _db_lock:
        def _execute():
            session = SessionLocal()
            try:
                result = func(session)
                session.commit()
                return result
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
        return await asyncio.to_thread(_execute)

def get_db_session() -> Session:
    return SessionLocal()
