"""Orchestrator: runs the Navigator -> Analyst -> Critic -> Synthesiser pipeline.

Pure Python async coordination -- the sequence of steps is fixed and known in
advance, so there's no decision for an LLM to make here. Each agent's
sync .run() is offloaded to a thread so the event loop isn't blocked while
waiting on Groq API calls.
"""

import asyncio
import logging
import os
import time
import traceback
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from groq import Groq

from backend.agents.analyst import AnalystAgent
from backend.agents.critic import CriticAgent
from backend.agents.navigator import Navigator
from backend.agents.synthesiser import SynthesiserAgent
from backend.models.schemas import (
    AnalystInput,
    AnalystOutput,
    CriticOutput,
    NavigatorInput,
    SynthesiserInput,
    SynthesiserOutput,
)

load_dotenv()
logger = logging.getLogger(__name__)

_FALLBACK_ANALYST_OUTPUT_FIELDS = dict(
    hypothesis="Analysis failed due to an internal error.",
    reasoning="An error occurred during analysis.",
    evidence=[],
    uncertainty="Complete",
    reasoning_gaps=["Analyst failed -- full analysis unavailable"],
    confidence_hint=0.1,
)

_FALLBACK_CRITIC_OUTPUT_FIELDS = dict(
    challenges=[],
    missing_files=[],
    unchecked_assumptions=[],
    confidence_adjustment=0.0,
    critique_summary="Critic failed -- no adversarial review available.",
)


class Orchestrator:
    """Coordinates a single end-to-end question through the agent pipeline."""

    def __init__(self, repo_path: str, repo_name: str):
        self.repo_path = repo_path
        self.repo_name = repo_name

        groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])
        self.navigator = Navigator(repo_path=repo_path)
        self.analyst = AnalystAgent(groq_client=groq_client)
        self.critic = CriticAgent(groq_client=groq_client)
        self.synthesiser = SynthesiserAgent(groq_client=groq_client)

    async def run(
        self, question: str
    ) -> tuple[SynthesiserOutput, AnalystOutput, CriticOutput, dict]:
        session_id = str(uuid.uuid4())
        latency_ms: dict[str, int] = {}
        t0 = time.monotonic()

        # TODO v2: analyst can be initialised before navigator returns.
        # Use asyncio.gather once analyst accepts a streaming navigator output.

        # Step 1: Navigator
        step_start = time.monotonic()
        navigator_input = NavigatorInput(question=question, repo_name=self.repo_name)
        navigator_output = await asyncio.to_thread(self.navigator.run, navigator_input)
        latency_ms["navigator"] = _elapsed_ms(step_start)

        if not navigator_output.chunks:
            logger.warning("Navigator returned zero chunks for question: %r", question)

        # Step 2: Analyst
        step_start = time.monotonic()
        try:
            analyst_input = AnalystInput(
                question=question, navigator_output=navigator_output, repo_name=self.repo_name
            )
            analyst_output = await asyncio.to_thread(self.analyst.run, analyst_input)
        except Exception:
            logger.error("Analyst failed for question %r:\n%s", question, traceback.format_exc())
            analyst_output = AnalystOutput(question=question, **_FALLBACK_ANALYST_OUTPUT_FIELDS)
        latency_ms["analyst"] = _elapsed_ms(step_start)

        # Step 3: Critic
        step_start = time.monotonic()
        try:
            critic_output = await asyncio.to_thread(
                self.critic.run, question, navigator_output, analyst_output
            )
        except Exception:
            logger.error("Critic failed for question %r:\n%s", question, traceback.format_exc())
            critic_output = CriticOutput(question=question, **_FALLBACK_CRITIC_OUTPUT_FIELDS)
        latency_ms["critic"] = _elapsed_ms(step_start)

        # Step 4: Synthesiser
        step_start = time.monotonic()
        synthesiser_input = SynthesiserInput(
            question=question,
            navigator_output=navigator_output,
            analyst_output=analyst_output,
            critic_output=critic_output,
        )
        synthesiser_output = await asyncio.to_thread(self.synthesiser.run, synthesiser_input)
        latency_ms["synthesiser"] = _elapsed_ms(step_start)

        latency_ms["total"] = _elapsed_ms(t0)

        confidence = max(
            0.0, min(1.0, analyst_output.confidence_hint + critic_output.confidence_adjustment)
        )
        confidence_label = (
            "high" if confidence >= 0.75 else "medium" if confidence >= 0.5 else "low"
        )

        trace = {
            "session_id": session_id,
            "question": question,
            "repo_name": self.repo_name,
            "navigator_output": navigator_output.model_dump(),
            "analyst_output": analyst_output.model_dump(),
            "critic_output": critic_output.model_dump(),
            "synthesiser_output": synthesiser_output.model_dump(),
            "confidence": confidence,
            "confidence_label": confidence_label,
            "latency_ms": latency_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return synthesiser_output, analyst_output, critic_output, trace


def _elapsed_ms(start: float) -> int:
    return int(round((time.monotonic() - start) * 1000))
