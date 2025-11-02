from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Chunk:
    path: str
    start_line: int
    end_line: int
    content: str


def chunk_file_content(
    path: str,
    content: str,
    max_lines: int = 80,
) -> List[Chunk]:
    """
    Chunk a file's content into line-based chunks with metadata.
    """
    lines = content.splitlines()
    chunks: List[Chunk] = []

    if not lines:
        return chunks

    line_index = 0
    total_lines = len(lines)

    while line_index < total_lines:
        start = line_index
        end = min(line_index + max_lines, total_lines)
        chunk_lines = lines[start:end]
        chunks.append(
            Chunk(
                path=path,
                start_line=start + 1,
                end_line=end,
                content="\n".join(chunk_lines),
            )
        )
        line_index = end

    return chunks

