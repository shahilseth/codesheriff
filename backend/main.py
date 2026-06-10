"""FastAPI app for CodeSheriff: indexing and question-answering endpoints."""

import logging
import os
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine

from backend.db.postgres import create_session, get_trace, init_db, log_trace
from backend.indexer.index_repo import index_repo
from backend.models.schemas import (
    CitedFileResponse,
    IndexRequest,
    QueryRequest,
    QueryResponse,
)
from backend.orchestrator.orchestrator import Orchestrator

load_dotenv()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_async_engine(os.environ["CODESHERIFF_DB_URL"])
    await init_db(engine)
    app.state.engine = engine
    yield
    await engine.dispose()


app = FastAPI(title="CodeSheriff", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}


@app.post("/api/index")
async def index(request: IndexRequest) -> dict:
    try:
        summary = index_repo(request.repo_path)
    except Exception:
        logger.error("Indexing failed for repo_path=%r", request.repo_path, exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "Indexing failed."})

    return {
        "status": "indexed",
        "chunks": summary["chunks_indexed"],
        "files": summary["files_scanned"],
    }


@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    engine = app.state.engine

    try:
        async with engine.connect() as conn:
            db_session_id = await create_session(conn, request.repo_name)

            orchestrator = Orchestrator(repo_path=request.repo_path, repo_name=request.repo_name)
            synthesiser_output, _analyst_output, _critic_output, trace = await orchestrator.run(
                request.question
            )

            trace["session_id"] = db_session_id
            trace_id = await log_trace(
                conn,
                session_id=db_session_id,
                trace_dict=trace,
                confidence=trace["confidence"],
                confidence_label=trace["confidence_label"],
            )
    except Exception:
        logger.error("Query failed for question=%r", request.question, exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "Query failed. Check server logs."})

    return QueryResponse(
        session_id=db_session_id,
        question=request.question,
        answer=synthesiser_output.answer,
        confidence=trace["confidence"],
        confidence_label=trace["confidence_label"],
        cited_files=[
            CitedFileResponse(
                file_path=cf.file_path,
                chunk_name=cf.chunk_name,
                lines=cf.lines,
                contribution=cf.contribution,
            )
            for cf in synthesiser_output.cited_files
        ],
        known_gaps=synthesiser_output.known_gaps,
        trace_id=trace_id,
    )


@app.get("/api/trace/{trace_id}")
async def get_trace_endpoint(trace_id: str) -> dict:
    try:
        trace_uuid = uuid.UUID(trace_id)
    except ValueError:
        raise HTTPException(status_code=422, detail={"error": "Invalid trace_id."})

    engine = app.state.engine
    async with engine.connect() as conn:
        trace = await get_trace(conn, trace_uuid)

    if trace is None:
        raise HTTPException(status_code=404, detail={"error": "Trace not found."})

    return trace
