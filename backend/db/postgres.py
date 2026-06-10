"""PostgreSQL trace logging for CodeSheriff.

Uses SQLAlchemy Core (not the ORM) -- these are simple append-only tables
with no relationships to navigate, so the extra ORM layer would add
ceremony without benefit.
"""

import uuid
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    MetaData,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

metadata = MetaData()

sessions = Table(
    "sessions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("repo_name", String(255), nullable=False),
    Column("created_at", DateTime, server_default=func.now()),
)

traces = Table(
    "traces",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("session_id", UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False),
    Column("question", Text, nullable=False),
    Column("full_trace", JSONB, nullable=False),
    Column("confidence", Float, nullable=False),
    Column("confidence_label", String(10), nullable=False),
    Column("created_at", DateTime, server_default=func.now()),
)


async def init_db(engine: AsyncEngine) -> None:
    """Create the sessions and traces tables if they don't exist. Call on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)


async def create_session(conn: AsyncConnection, repo_name: str) -> str:
    """Insert a sessions row and return its id as a string."""
    session_id = uuid.uuid4()
    await conn.execute(sessions.insert().values(id=session_id, repo_name=repo_name))
    await conn.commit()
    return str(session_id)


async def get_trace(conn: AsyncConnection, trace_id: uuid.UUID) -> Optional[dict]:
    """Fetch a trace's full_trace JSON by id, or None if it doesn't exist."""
    result = await conn.execute(traces.select().where(traces.c.id == trace_id))
    row = result.fetchone()
    return row.full_trace if row else None


async def log_trace(
    conn: AsyncConnection,
    session_id: str,
    trace_dict: dict,
    confidence: float,
    confidence_label: str,
) -> str:
    """Insert a traces row and return its id as a string."""
    trace_id = uuid.uuid4()
    await conn.execute(
        traces.insert().values(
            id=trace_id,
            session_id=uuid.UUID(session_id),
            question=trace_dict["question"],
            full_trace=trace_dict,
            confidence=confidence,
            confidence_label=confidence_label,
        )
    )
    await conn.commit()
    return str(trace_id)
