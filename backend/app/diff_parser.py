from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Literal


LineType = Literal["added", "removed", "context"]


@dataclass(frozen=True)
class ParsedLine:
  type: LineType
  content: str


@dataclass(frozen=True)
class ParsedHunk:
  old_start: int
  old_count: int
  new_start: int
  new_count: int
  lines: List[ParsedLine]


def parse_unified_diff(patch: str | None) -> List[ParsedHunk]:
  """
  Parse a unified diff patch (as returned by GitHub) into structured hunks.

  Lines starting with:
    - ' ' are treated as context
    - '+' are treated as added
    - '-' are treated as removed
    - '\\' (e.g. "\\ No newline at end of file") are ignored
  """
  if not patch:
    return []

  lines = patch.splitlines()
  hunks: List[ParsedHunk] = []
  current_hunk: ParsedHunk | None = None
  current_lines: List[ParsedLine] = []

  def flush_current_hunk() -> None:
    nonlocal current_hunk, current_lines
    if current_hunk is not None:
      hunks.append(
        ParsedHunk(
          old_start=current_hunk.old_start,
          old_count=current_hunk.old_count,
          new_start=current_hunk.new_start,
          new_count=current_hunk.new_count,
          lines=list(current_lines),
        )
      )
    current_hunk = None
    current_lines = []

  for line in lines:
    if line.startswith("@@"):
      # Start of a new hunk
      flush_current_hunk()
      # Format: @@ -old_start,old_count +new_start,new_count @@ optional heading
      try:
        header = line.split("@@")[1].strip()
        # header like: "-1,3 +1,4"
        parts = header.split(" ")
        old_part = next(p for p in parts if p.startswith("-"))
        new_part = next(p for p in parts if p.startswith("+"))
        old_start_str, old_count_str = _split_range(old_part[1:])
        new_start_str, new_count_str = _split_range(new_part[1:])
        current_hunk = ParsedHunk(
          old_start=int(old_start_str),
          old_count=int(old_count_str),
          new_start=int(new_start_str),
          new_count=int(new_count_str),
          lines=[],
        )
      except Exception:
        # If we fail to parse the header, skip this hunk but continue with others.
        current_hunk = ParsedHunk(
          old_start=0,
          old_count=0,
          new_start=0,
          new_count=0,
          lines=[],
        )
      continue

    if current_hunk is None:
      # Ignore lines before the first hunk header.
      continue

    if not line:
      current_lines.append(ParsedLine(type="context", content=""))
      continue

    prefix = line[0]
    content = line[1:] if len(line) > 1 else ""

    if prefix == " ":
      current_lines.append(ParsedLine(type="context", content=content))
    elif prefix == "+":
      current_lines.append(ParsedLine(type="added", content=content))
    elif prefix == "-":
      current_lines.append(ParsedLine(type="removed", content=content))
    elif prefix == "\\":
      # e.g. "\ No newline at end of file" -> ignore
      continue
    else:
      # Fallback: treat as context
      current_lines.append(ParsedLine(type="context", content=line))

  flush_current_hunk()
  return hunks


def _split_range(part: str) -> tuple[str, str]:
  """
  Split a range component like "1,3" into (start, count).
  If count is omitted (e.g. "1"), treat it as 1.
  """
  if "," in part:
    start, count = part.split(",", 1)
    return start, count
  return part, "1"

