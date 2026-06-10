"""Pydantic models shared between agents.

These define the data contracts that flow between agents (e.g. Navigator's
output is the Analyst's input). Keeping them in one place means every agent
agrees on the same shape, and validation happens at the boundary instead of
deep inside an agent.
"""

from typing import Literal

from pydantic import BaseModel


class NavigatorInput(BaseModel):
    question: str
    repo_name: str
    top_k: int = 5


class ChunkResult(BaseModel):
    file_path: str
    chunk_name: str
    chunk_type: str
    content: str
    similarity_score: float
    start_line: int
    end_line: int


class CommitResult(BaseModel):
    hash: str
    message: str
    author: str
    timestamp: str
    files_changed: list[str]


class NavigatorOutput(BaseModel):
    question: str
    chunks: list[ChunkResult]
    commits: list[CommitResult]
    retrieved_file_paths: list[str]


class AnalystInput(BaseModel):
    question: str
    navigator_output: NavigatorOutput
    repo_name: str


class EvidenceReference(BaseModel):
    file_path: str
    chunk_name: str
    lines: str  # e.g. "32-66"
    relevance: str  # one sentence: why this chunk supports the reasoning


class AnalystOutput(BaseModel):
    question: str
    hypothesis: str  # one clear sentence: the Analyst's best answer
    reasoning: str  # full reasoning chain, 2-5 paragraphs
    evidence: list[EvidenceReference]  # which chunks support the conclusion
    uncertainty: str  # what the Analyst is not sure about, specifically
    reasoning_gaps: list[str]  # context that was unavailable but would have helped
    confidence_hint: float  # 0.0-1.0, Analyst's self-assessed confidence before Critic review


CriticChallengeType = Literal[
    "missing_file",
    "unsupported_assumption",
    "incomplete_retrieval",
    "reasoning_gap",
    "contradicting_evidence",
]

CriticSeverity = Literal["high", "medium", "low"]


class CriticChallenge(BaseModel):
    challenge_type: CriticChallengeType
    description: str  # specific, checkable, 1-2 sentences
    severity: CriticSeverity
    checkable_by: str  # what would resolve this, e.g. "retrieve X file"


class CriticOutput(BaseModel):
    question: str
    challenges: list[CriticChallenge]
    missing_files: list[str]  # specific file paths/patterns the Analyst should have had
    unchecked_assumptions: list[str]  # claims made without direct evidence from chunks
    confidence_adjustment: float  # -0.3 to +0.1, applied to AnalystOutput.confidence_hint
    critique_summary: str  # 2-3 sentences: overall assessment of the Analyst's output


class SynthesiserInput(BaseModel):
    question: str
    navigator_output: NavigatorOutput
    analyst_output: AnalystOutput
    critic_output: CriticOutput


class CitedFile(BaseModel):
    file_path: str
    chunk_name: str
    lines: str
    contribution: str  # one sentence: what this file contributed to the answer


class SynthesiserOutput(BaseModel):
    answer: str  # final answer, 2-4 paragraphs, written for a developer audience
    cited_files: list[CitedFile]
    known_gaps: list[str]  # union of analyst.reasoning_gaps and critic.missing_files


class QueryRequest(BaseModel):
    question: str
    repo_name: str
    repo_path: str


class IndexRequest(BaseModel):
    repo_path: str
    repo_name: str


class CitedFileResponse(BaseModel):
    file_path: str
    chunk_name: str
    lines: str
    contribution: str


class QueryResponse(BaseModel):
    session_id: str
    question: str
    answer: str
    confidence: float
    confidence_label: str  # "high" >=0.75, "medium" 0.5-0.74, "low" <0.5
    cited_files: list[CitedFileResponse]
    known_gaps: list[str]
    trace_id: str
