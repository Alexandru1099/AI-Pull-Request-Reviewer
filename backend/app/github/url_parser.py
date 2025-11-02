from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True)
class ParsedPullRequestUrl:
    owner: str
    repo: str
    pull_number: int


class PullRequestUrlError(ValueError):
    """Raised when a PR URL is invalid or unsupported."""


def parse_github_pr_url(pr_url: str) -> ParsedPullRequestUrl:
    """
    Parse and validate a public GitHub PR URL.

    Supported formats:
      - https://github.com/{owner}/{repo}/pull/{number}
      - http://github.com/{owner}/{repo}/pull/{number}
    Trailing slashes, query strings, and fragments are tolerated.
    """
    if not pr_url:
        raise PullRequestUrlError("pr_url must not be empty.")

    parsed = urlparse(pr_url)

    if parsed.scheme not in {"http", "https"}:
        raise PullRequestUrlError("pr_url must use http or https.")

    # Only support public github.com for Phase 2
    if parsed.netloc not in {"github.com", "www.github.com"}:
        raise PullRequestUrlError("pr_url must point to github.com.")

    path_parts: list[str] = [p for p in parsed.path.split("/") if p]
    # Expect: owner / repo / pull / number
    if len(path_parts) < 4 or path_parts[2] != "pull":
        raise PullRequestUrlError(
            "pr_url must have format https://github.com/<owner>/<repo>/pull/<number>."
        )

    owner, repo, _, number_str = path_parts[:4]

    try:
        pull_number = int(number_str)
    except ValueError as exc:  # pragma: no cover - straightforward
        raise PullRequestUrlError("pull_number in pr_url must be an integer.") from exc

    if pull_number <= 0:
        raise PullRequestUrlError("pull_number in pr_url must be positive.")

    return ParsedPullRequestUrl(owner=owner, repo=repo, pull_number=pull_number)

