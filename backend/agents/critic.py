"""Critic agent: adversarial reviewer of the Analyst's output.

Receives the question, NavigatorOutput (coverage only -- file paths and chunk
names, NOT chunk content), and AnalystOutput. Its sole job is to find what's
wrong, missing, or assumed without evidence -- not to agree, summarize, or
re-do the Analyst's reasoning.

Returns a structured CriticOutput that the Synthesiser (Phase 5) uses to
calibrate the final answer's confidence.
"""

import json
import logging

from backend.models.schemas import AnalystOutput, CriticOutput, NavigatorOutput

logger = logging.getLogger(__name__)

_MIN_ADJUSTMENT = -0.3
_MAX_ADJUSTMENT = 0.1

_SYSTEM_PROMPT = """You are an adversarial code reviewer. You have been given a \
question, the files that were retrieved to answer it, and an analyst's reasoning. \
Your job is not to agree or summarize -- it is to find what is wrong, incomplete, \
or assumed without evidence.

Do not restate what the Analyst said correctly. Only surface problems.

For "challenge_type", use ONLY one of these exact values -- no other strings are \
valid:
  - "missing_file": a specific file or module that should have been retrieved but \
wasn't
  - "unsupported_assumption": a claim in the reasoning not directly backed by the \
listed chunks
  - "incomplete_retrieval": the retrieved chunks cover part of a file/module but \
miss other relevant parts
  - "reasoning_gap": a logical step in the reasoning that doesn't follow from the \
evidence
  - "contradicting_evidence": something in the retrieved chunks/commits conflicts \
with the hypothesis

For "severity":
  - "high": if resolved, this would likely CHANGE the hypothesis itself
  - "medium": if resolved, this would meaningfully strengthen or weaken confidence, \
but the hypothesis would likely stand
  - "low": worth noting, but would not change the conclusion either way

For "confidence_adjustment" (a single float applied to the Analyst's confidence_hint):
  - Most outputs should be in the -0.05 to -0.20 range -- retrieval is rarely \
perfectly complete.
  - Use -0.25 to -0.30 only when the hypothesis depends ENTIRELY on an assumption \
that was never verified in the retrieved code.
  - Use +0.05 to +0.10 ONLY if all obviously relevant files appear to have been \
retrieved and the reasoning chain is fully supported by the listed evidence.
  - Default to 0.0 only if you genuinely find nothing -- this should be rare.

If the Analyst's reasoning_gaps already correctly identified the missing context, \
acknowledge this in critique_summary -- but still list those files in \
"missing_files". The Synthesiser needs the file list regardless of whether the \
Analyst already flagged it as a gap.

Be specific. "There may be other relevant files" is not acceptable -- name a file, \
a function, or an assumption. Every challenge must be CHECKABLE: someone should be \
able to act on "checkable_by" to confirm or refute it.

If the Analyst's reasoning consists mainly of restating facts already present in \
code comments or docstrings (description), rather than inferring the tradeoffs or \
decisions behind those facts (rationale), flag this explicitly as a "reasoning_gap" \
with challenge_type "unsupported_assumption" and severity "medium".

"missing_files" must contain only valid file paths or glob patterns (e.g. \
"backend/indexer/embedder.py" or "backend/indexer/test_*.py"). Do not append \
explanations, parentheticals, or qualifiers to file paths. If you want to explain \
why a file is missing, put that in the challenge description, not in the file path \
string.

Return only a JSON object matching this exact shape. No markdown, no preamble, no \
explanation outside the JSON:

{
  "challenges": [
    {
      "challenge_type": "missing_file",
      "description": "specific, checkable, 1-2 sentences",
      "severity": "high",
      "checkable_by": "what would resolve this, e.g. 'retrieve auth_middleware.py'"
    }
  ],
  "missing_files": ["specific/path/or/pattern.py"],
  "unchecked_assumptions": ["claim made without direct evidence from retrieved chunks"],
  "confidence_adjustment": -0.1,
  "critique_summary": "2-3 sentences: overall assessment of the Analyst's output quality"
}
"""


class CriticAgent:
    """Adversarially reviews an AnalystOutput against retrieval coverage."""

    def __init__(self, groq_client, model: str = "llama-3.1-8b-instant"):
        self.client = groq_client
        self.model = model

    def run(
        self,
        question: str,
        navigator_output: NavigatorOutput,
        analyst_output: AnalystOutput,
    ) -> CriticOutput:
        user_prompt = _build_user_prompt(question, navigator_output, analyst_output)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        raw_content = response.choices[0].message.content or ""

        return _parse_output(raw_content, question)


def _build_user_prompt(
    question: str, navigator_output: NavigatorOutput, analyst_output: AnalystOutput
) -> str:
    lines = ["Section 1 -- Question:", question, ""]

    lines.append("Section 2 -- What was retrieved (file paths and chunk names only, no content):")
    if navigator_output.chunks:
        for chunk in navigator_output.chunks:
            lines.append(
                f"- {chunk.file_path} :: {chunk.chunk_name} "
                f"(lines {chunk.start_line}-{chunk.end_line})"
            )
    else:
        lines.append("(nothing retrieved)")

    if navigator_output.commits:
        lines.append("\nCommits retrieved:")
        for commit in navigator_output.commits:
            files = ", ".join(commit.files_changed) if commit.files_changed else "(unknown)"
            lines.append(f"- {commit.hash[:8]}: {commit.message} (files: {files})")

    lines.append("\nSection 3 -- Analyst output:")
    lines.append(f"Hypothesis: {analyst_output.hypothesis}")
    lines.append(f"Reasoning: {analyst_output.reasoning}")
    lines.append("Evidence cited:")
    for ref in analyst_output.evidence:
        lines.append(f"- {ref.file_path} :: {ref.chunk_name} (lines {ref.lines}) -- {ref.relevance}")
    lines.append(f"Uncertainty: {analyst_output.uncertainty}")
    lines.append("Reasoning gaps:")
    for gap in analyst_output.reasoning_gaps:
        lines.append(f"- {gap}")
    lines.append(f"Confidence hint: {analyst_output.confidence_hint}")

    lines.append(
        "\nSection 4 -- Given the above, identify: (1) files or functions that should "
        "have been retrieved but weren't, (2) claims in the reasoning that aren't "
        "directly supported by the listed chunks, (3) assumptions the Analyst made "
        "that could be wrong. Be specific. Generic uncertainty is not useful."
    )
    return "\n".join(lines)


def _parse_output(raw_content: str, question: str) -> CriticOutput:
    try:
        data = json.loads(_strip_code_fence(raw_content))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Critic response was not valid JSON: {exc}\n\nRaw response:\n{raw_content}"
        ) from exc

    adjustment = data.get("confidence_adjustment")
    if not isinstance(adjustment, (int, float)):
        logger.warning("Critic returned non-numeric confidence_adjustment=%r; defaulting to 0.0", adjustment)
        adjustment = 0.0
    elif not (_MIN_ADJUSTMENT <= adjustment <= _MAX_ADJUSTMENT):
        clamped = max(_MIN_ADJUSTMENT, min(_MAX_ADJUSTMENT, adjustment))
        logger.warning(
            "Critic returned confidence_adjustment=%r outside [%s, %s]; clamping to %s",
            adjustment, _MIN_ADJUSTMENT, _MAX_ADJUSTMENT, clamped,
        )
        adjustment = clamped
    data["confidence_adjustment"] = adjustment

    data["question"] = question

    return CriticOutput.model_validate(data)


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
