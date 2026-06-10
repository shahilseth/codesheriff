"""Synthesiser agent: the final reasoning layer of CodeSheriff.

Takes the question, the Analyst's reasoning, and the Critic's adversarial
challenges, and produces the final answer for the user -- honestly
reflecting what is known, what is uncertain, and what is missing.

Uses a larger model than the rest of the pipeline because this is the one
output the user sees, and it must reconcile two potentially conflicting
upstream outputs (confident hypothesis vs. adversarial challenges) while
satisfying a conditional structural requirement (acknowledging high-severity
challenges explicitly).
"""

import json
import logging

from backend.models.schemas import CitedFile, SynthesiserInput, SynthesiserOutput

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are the final reasoning layer of a multi-agent code analysis \
system. You receive a question, an analyst's reasoning, and an adversarial critic's \
challenges. Your job is to produce the best possible answer given all of this -- \
honestly reflecting what is known, what is uncertain, and what is missing.

Synthesise, do not summarise. The answer must resolve or explicitly acknowledge the \
Critic's high-severity challenges. Do not ignore them, and do not repeat the \
Analyst's reasoning verbatim.

If a high-severity challenge exists, the answer must contain a sentence of the form: \
"this conclusion assumes X, which was not directly verified in the retrieved code."

"cited_files" must come only from files/chunks already in the Analyst's evidence \
list. Do not invent new file citations.

Do not include "known_gaps" in your output -- that is computed externally from the \
Analyst's and Critic's structured output, not by you.

Return only a JSON object with keys: "answer" (string), "cited_files" (list of \
objects with "file_path", "chunk_name", "lines", "contribution"). No markdown, no \
preamble, no extra keys.
"""


class SynthesiserAgent:
    """Reconciles AnalystOutput and CriticOutput into the final user-facing answer."""

    def __init__(self, groq_client, model: str = "llama-3.3-70b-versatile"):
        self.client = groq_client
        self.model = model

    def run(self, input: SynthesiserInput) -> SynthesiserOutput:
        user_prompt = _build_user_prompt(input)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        raw_content = response.choices[0].message.content or ""

        return _parse_output(raw_content, input)


def _build_user_prompt(input: SynthesiserInput) -> str:
    analyst = input.analyst_output
    critic = input.critic_output

    lines = [f"Question: {input.question}", ""]

    lines.append("Analyst output:")
    lines.append(f"Hypothesis: {analyst.hypothesis}")
    lines.append(f"Reasoning: {analyst.reasoning}")
    lines.append("Evidence:")
    for ref in analyst.evidence:
        lines.append(f"- {ref.file_path} :: {ref.chunk_name} (lines {ref.lines}) -- {ref.relevance}")
    lines.append(f"Uncertainty: {analyst.uncertainty}")
    lines.append(f"Confidence hint: {analyst.confidence_hint}")

    lines.append("\nCritic output:")
    if critic.challenges:
        for challenge in critic.challenges:
            lines.append(
                f"- [{challenge.challenge_type} / {challenge.severity}] {challenge.description}"
            )
    else:
        lines.append("(no challenges)")
    if critic.unchecked_assumptions:
        lines.append("Unchecked assumptions:")
        for assumption in critic.unchecked_assumptions:
            lines.append(f"- {assumption}")
    lines.append(f"Critique summary: {critic.critique_summary}")

    lines.append(
        "\nWrite a final answer for a developer that: resolves or acknowledges each "
        "high-severity challenge explicitly, is grounded only in the cited evidence, "
        "and is honest about what could not be verified. Do not pad with generic "
        "caveats."
    )
    return "\n".join(lines)


def _parse_output(raw_content: str, input: SynthesiserInput) -> SynthesiserOutput:
    try:
        data = json.loads(_strip_code_fence(raw_content))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Synthesiser response was not valid JSON: {exc}\n\nRaw response:\n{raw_content}"
        ) from exc

    answer = data.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError(f"Synthesiser response missing non-empty 'answer'.\n\nRaw response:\n{raw_content}")

    cited_files_raw = data.get("cited_files", [])
    if not isinstance(cited_files_raw, list):
        logger.warning("Synthesiser returned non-list cited_files=%r; defaulting to []", cited_files_raw)
        cited_files_raw = []

    cited_files = []
    for item in cited_files_raw:
        try:
            cited_files.append(CitedFile.model_validate(item))
        except Exception:
            logger.warning("Skipping malformed cited_files entry: %r", item)

    known_gaps = _dedupe(input.analyst_output.reasoning_gaps + input.critic_output.missing_files)

    return SynthesiserOutput(answer=answer, cited_files=cited_files, known_gaps=known_gaps)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _strip_code_fence(text: str) -> str:
    """Strip a ```json ... ``` or ``` ... ``` wrapper if the model added one."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]  # drop opening fence (with optional language tag)
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]  # drop closing fence
        text = "\n".join(lines).strip()
    return text
