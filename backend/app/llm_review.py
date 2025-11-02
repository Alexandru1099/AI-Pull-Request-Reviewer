from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
import time
from typing import Any, Dict, List

from openai import OpenAI
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.review import ReviewAnalysisResponse

logger = logging.getLogger("repo_aware.llm_review")

SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9]{20,}",  # generic API keys
    r"ghp_[A-Za-z0-9]{36,}",  # GitHub personal tokens
    r"AIza[0-9A-Za-z\-_]{35}",  # Google-style keys
]


@dataclass
class LLMCallMetadata:
    model: str
    latency_ms: int
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None


@dataclass
class LLMReviewResult:
    review: ReviewAnalysisResponse
    metadata: LLMCallMetadata


def _redact_secrets(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = re.sub(pattern, "[REDACTED]", redacted)
    return redacted


def _build_review_prompt(
    title: str,
    description: str,
    changed_files: List[Dict[str, Any]],
    retrieved_context: Dict[str, List[Dict[str, Any]]],
) -> str:
    """
    Build a deterministic review instruction and context payload.
    """
    safe_title = _redact_secrets(title)
    safe_description = _redact_secrets(description)

    safe_changed_files: List[Dict[str, Any]] = []
    for f in changed_files:
        safe_changed_files.append(
            {
                "path": f.get("path"),
                "status": f.get("status"),
                "additions": f.get("additions"),
                "deletions": f.get("deletions"),
                "patch": _redact_secrets(f.get("patch") or "")[:4000],
            }
        )

    safe_context: Dict[str, List[Dict[str, Any]]] = {}
    for path, chunks in retrieved_context.items():
        safe_chunks: List[Dict[str, Any]] = []
        for c in chunks[:3]:
            safe_chunks.append(
                {
                    "path": c.get("path"),
                    "start_line": c.get("start_line"),
                    "end_line": c.get("end_line"),
                    "content": _redact_secrets(c.get("content") or "")[:4000],
                    "score": c.get("score"),
                }
            )
        safe_context[path] = safe_chunks

    payload = {
        "pr": {
            "title": safe_title,
            "description": safe_description,
        },
        "changed_files": safe_changed_files,
        "retrieved_context": safe_context,
    }

    contract = {
        "summary": "string",
        "quality_score": "integer 0-100",
        "critical_count": "integer",
        "warning_count": "integer",
        "suggestion_count": "integer",
        "issues": [
            {
                "severity": '"critical" | "warning" | "suggestion"',
                "category": "string",
                "title": "string",
                "file": "string",
                "line": "integer or null",
                "explanation": "string",
                "suggestion": "string",
                "evidence": ["string"],
            }
        ],
    }

    return (
        "You are a senior engineering reviewer. "
        "Review the pull request diff and repository context. "
        "If the context is insufficient to make a claim, you MUST avoid guessing and instead "
        'return an empty "issues" array and a neutral summary.\n\n'
        "Return ONLY a single JSON object that matches this contract:\n"
        f"{json.dumps(contract, indent=2)}\n\n"
        "Input data:\n"
        f"{json.dumps(payload, indent=2)}\n"
    )


def _call_llm(
    prompt: str,
    retry_instruction: str | None = None,
) -> tuple[str, LLMCallMetadata]:
    settings = get_settings()
    model = settings.llm_model
    client = OpenAI()

    messages = [
        {
            "role": "system",
            "content": (
                "You are a precise code reviewer. "
                "Always answer ONLY with a single JSON object; no extra text."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    if retry_instruction:
        messages.insert(
            1,
            {
                "role": "system",
                "content": retry_instruction,
            },
        )

    start = time.monotonic()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.0,
    )
    latency_ms = int((time.monotonic() - start) * 1000)
    usage = response.usage
    logger.info(
        "LLM completion finished",
        extra={
            "model": response.model or model,
            "elapsed_ms": latency_ms,
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        },
    )

    metadata = LLMCallMetadata(
        model=response.model or model,
        latency_ms=latency_ms,
        prompt_tokens=getattr(usage, "prompt_tokens", None),
        completion_tokens=getattr(usage, "completion_tokens", None),
        total_tokens=getattr(usage, "total_tokens", None),
    )

    return response.choices[0].message.content or "{}", metadata


def run_llm_review(
    title: str,
    description: str,
    changed_files: List[Dict[str, Any]],
    retrieved_context: Dict[str, List[Dict[str, Any]]],
) -> LLMReviewResult:
    """
    Run the LLM-based review with validation and a single retry on schema errors.
    """
    prompt = _build_review_prompt(title, description, changed_files, retrieved_context)

    raw, metadata = _call_llm(prompt)

    try:
        data = json.loads(raw)
        return LLMReviewResult(
            review=ReviewAnalysisResponse.model_validate(data),
            metadata=metadata,
        )
    except (json.JSONDecodeError, ValidationError) as first_error:
        logger.warning(
            "LLM review output failed validation on first attempt",
            extra={"error": str(first_error)},
        )

        retry_instruction = (
            "Your previous response did not match the required JSON schema. "
            "You MUST respond with a single JSON object exactly matching the contract. "
            "Do not wrap it in markdown or add any commentary."
        )
        raw_retry, retry_metadata = _call_llm(
            prompt,
            retry_instruction=retry_instruction,
        )
        aggregated_metadata = LLMCallMetadata(
            model=retry_metadata.model or metadata.model,
            latency_ms=metadata.latency_ms + retry_metadata.latency_ms,
            prompt_tokens=_sum_optional_ints(
                metadata.prompt_tokens,
                retry_metadata.prompt_tokens,
            ),
            completion_tokens=_sum_optional_ints(
                metadata.completion_tokens,
                retry_metadata.completion_tokens,
            ),
            total_tokens=_sum_optional_ints(
                metadata.total_tokens,
                retry_metadata.total_tokens,
            ),
        )

        try:
            data_retry = json.loads(raw_retry)
            return LLMReviewResult(
                review=ReviewAnalysisResponse.model_validate(data_retry),
                metadata=aggregated_metadata,
            )
        except (json.JSONDecodeError, ValidationError) as second_error:
            logger.error(
                "LLM review output failed validation on second attempt; "
                "falling back to empty review.",
                extra={"error": str(second_error)},
            )
            return LLMReviewResult(
                review=ReviewAnalysisResponse(
                    summary=(
                        "The automated review engine could not produce a valid structured "
                        "response. No issues are reported."
                    ),
                    quality_score=100,
                    critical_count=0,
                    warning_count=0,
                    suggestion_count=0,
                    issues=[],
                ),
                metadata=aggregated_metadata,
            )


def _sum_optional_ints(left: int | None, right: int | None) -> int | None:
    if left is None and right is None:
        return None
    return (left or 0) + (right or 0)
