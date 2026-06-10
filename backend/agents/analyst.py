"""Analyst agent: the reasoning layer of CodeSheriff.

Takes a question plus a fixed NavigatorOutput (already-retrieved chunks and
commits) and produces a structured hypothesis about the code's logic, design
intent, and tradeoffs -- including an honest account of what's missing.

Does not retrieve anything itself, and does not decide final confidence
(that's the Critic/Synthesiser's job in later phases).
"""

import json
import logging

from backend.models.schemas import AnalystInput, AnalystOutput

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are the Analyst agent in CodeSheriff, a system that answers \
questions about code repositories.

You will be given a question and a set of retrieved code chunks and git commits. \
Your job is to reason about the code's LOGIC, DESIGN INTENT, and DECISIONS -- not \
just describe what it does.

- Bad: "This function validates tokens."
- Good: "Token validation is split into two passes -- a fast format check, then a \
slower signature check -- likely to fail cheaply on malformed tokens before paying \
the cost of cryptographic verification."

Always explain WHY the code is structured the way it is, when the evidence supports \
a reasonable inference. If the evidence does not support a "why" claim, say so \
explicitly rather than inventing a justification.

IMPORTANT: You are receiving a PARTIAL view of the codebase -- a handful of \
retrieved chunks and commits, not the full repository. Reason only from what is \
given to you. Do not assume files, functions, or history exist beyond what is shown. \
If something would be needed to fully answer the question but was not retrieved, say \
so plainly instead of guessing or filling the gap with invented details.

For "reasoning_gaps", list SPECIFIC missing context, e.g.:
- "The test file for chunker.py was not retrieved, so it's unclear what edge cases \
are covered."
- "No commit history was available for embedder.py, so the timeline of why this \
model was chosen is unknown."
Do NOT write generic hedges like "there may be other relevant files" -- name what is \
specifically missing and why it matters to this question.

For "confidence_hint", self-assess honestly on a 0.0-1.0 scale:
- 0.9+ only if all relevant files appear to have been retrieved AND your reasoning \
is complete, with no significant gaps.
- Most answers should fall in the 0.5-0.75 range, reflecting that retrieval is based \
on similarity search and may be incomplete.
- Lower scores (below 0.5) are appropriate when key context is clearly missing or the \
evidence is ambiguous.

Return only a JSON object matching this exact shape. No markdown, no preamble, no \
explanation outside the JSON:

{
  "hypothesis": "one clear sentence: your best answer to the question",
  "reasoning": "full reasoning chain, 2-5 paragraphs",
  "evidence": [
    {
      "file_path": "path/to/file.py",
      "chunk_name": "function_or_class_name",
      "lines": "32-66",
      "relevance": "one sentence: why this chunk supports the reasoning"
    }
  ],
  "uncertainty": "what you are specifically not sure about",
  "reasoning_gaps": ["specific missing context, one item per string"],
  "confidence_hint": 0.65
}
"""


class AnalystAgent:
    """Reasons over a fixed NavigatorOutput to produce a structured hypothesis."""

    def __init__(self, groq_client, model: str = "llama-3.1-8b-instant"):
        self.client = groq_client
        self.model = model

    def run(self, input: AnalystInput) -> AnalystOutput:
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

        return _parse_output(raw_content, input.question)


def _build_user_prompt(input: AnalystInput) -> str:
    nav = input.navigator_output
    lines = [f"Question: {input.question}", "", "Retrieved code chunks:"]

    if not nav.chunks:
        lines.append("(none retrieved)")
    for chunk in nav.chunks:
        lines.append(
            f"\n--- {chunk.file_path} :: {chunk.chunk_type} '{chunk.chunk_name}' "
            f"(lines {chunk.start_line}-{chunk.end_line}) ---"
        )
        lines.append(chunk.content)

    lines.append("\nRelevant commits:")
    if nav.commits:
        for commit in nav.commits:
            files = ", ".join(commit.files_changed) if commit.files_changed else "(unknown)"
            lines.append(f"- {commit.hash[:8]}: {commit.message} (files: {files})")
    else:
        lines.append("(none retrieved)")

    lines.append(
        "\nBased only on the above context, reason about the question. Identify "
        "what is present, what is missing, and what you can and cannot conclude."
    )
    return "\n".join(lines)


def _parse_output(raw_content: str, question: str) -> AnalystOutput:
    try:
        data = json.loads(_strip_code_fence(raw_content))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Analyst response was not valid JSON: {exc}\n\nRaw response:\n{raw_content}"
        ) from exc

    confidence = data.get("confidence_hint")
    if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
        logger.warning(
            "Analyst returned invalid confidence_hint=%r; defaulting to 0.5", confidence
        )
        data["confidence_hint"] = 0.5

    data["question"] = question

    return AnalystOutput.model_validate(data)


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
