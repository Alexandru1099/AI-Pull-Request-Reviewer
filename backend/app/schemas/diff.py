from __future__ import annotations

from pydantic import BaseModel, HttpUrl, field_validator

from app.diff_parser import ParsedHunk, ParsedLine
from app.github.url_parser import ParsedPullRequestUrl, parse_github_pr_url


class ParseDiffRequest(BaseModel):
    pr_url: HttpUrl

    @field_validator("pr_url")
    @classmethod
    def validate_github_pr_url(cls, value: HttpUrl) -> HttpUrl:
        parse_github_pr_url(str(value))
        return value


class ParsedLineModel(BaseModel):
    type: str
    content: str

    @classmethod
    def from_parsed(cls, line: ParsedLine) -> "ParsedLineModel":
        return cls(type=line.type, content=line.content)


class ParsedHunkModel(BaseModel):
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[ParsedLineModel]

    @classmethod
    def from_parsed(cls, hunk: ParsedHunk) -> "ParsedHunkModel":
        return cls(
            old_start=hunk.old_start,
            old_count=hunk.old_count,
            new_start=hunk.new_start,
            new_count=hunk.new_count,
            lines=[ParsedLineModel.from_parsed(line) for line in hunk.lines],
        )


class ParsedFileModel(BaseModel):
    path: str
    status: str
    additions: int
    deletions: int
    patch: str | None = None
    parsed_hunks: list[ParsedHunkModel]


class ParsedDiffResponse(BaseModel):
    owner: str
    repo: str
    pull_number: int
    files: list[ParsedFileModel]

