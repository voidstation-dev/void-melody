"""Macro text planner for VieNeu TTS synthesis.

Plans macro text blocks (~1024 chars, hard max ~1280 chars) for VieNeu v3 Turbo,
preserving paragraph, sentence, and phrase boundaries while avoiding nested
over-chunking.
"""

from __future__ import annotations

import re


def plan_vieneu_macro_chunks(
    text: str,
    *,
    target_chars: int = 1024,
    hard_max_chars: int = 1280,
) -> list[str]:
    """Split input text into VieNeu macro chunks respecting natural linguistic boundaries.

    Hierarchy of splitting:
    1. Paragraphs (double/single newlines)
    2. Sentences (.!?…:;)
    3. Clauses/commas (,;-—)
    4. Words (spaces)
    5. Hard split (only when single unbreakable token exceeds hard_max_chars)
    """
    text = text.strip()
    if not text:
        return []

    if len(text) <= hard_max_chars:
        return [text]

    # Split into paragraphs first
    raw_paragraphs = re.split(r"(\n\s*\n|\n)", text)
    # Reassemble paragraphs with their separators
    paragraphs: list[str] = []
    buf = ""
    for item in raw_paragraphs:
        if re.match(r"^\n\s*\n$", item) or item == "\n":
            if buf:
                paragraphs.append(buf)
                buf = ""
            paragraphs.append(item)
        else:
            if item.strip():
                buf += item
    if buf:
        paragraphs.append(buf)

    chunks: list[str] = []
    current_chunk = ""

    def append_sub_part(part: str) -> None:
        nonlocal current_chunk, chunks
        if not part:
            return
        if not current_chunk:
            current_chunk = part
        elif len(current_chunk) + len(part) <= hard_max_chars:
            current_chunk += part
        else:
            chunks.append(current_chunk.strip())
            current_chunk = part

    for p in paragraphs:
        if len(p) <= hard_max_chars:
            if not current_chunk:
                current_chunk = p
            elif len(current_chunk) + len(p) <= target_chars:
                current_chunk += p
            elif len(current_chunk) + len(p) <= hard_max_chars:
                # Still within hard max, but check if starting a new chunk is cleaner
                if len(current_chunk) >= target_chars * 0.75:
                    chunks.append(current_chunk.strip())
                    current_chunk = p
                else:
                    current_chunk += p
            else:
                chunks.append(current_chunk.strip())
                current_chunk = p
        else:
            # Paragraph p exceeds hard_max_chars, split by sentence endings
            sentences = re.split(r"(?<=[.!?…:;])\s+", p)
            for s in sentences:
                s = s.strip()
                if not s:
                    continue
                if len(s) <= hard_max_chars:
                    if not current_chunk:
                        current_chunk = s
                    elif len(current_chunk) + len(s) + 1 <= target_chars:
                        current_chunk += (" " if not current_chunk.endswith(("\n", " ")) else "") + s
                    elif len(current_chunk) + len(s) + 1 <= hard_max_chars:
                        if len(current_chunk) >= target_chars * 0.75:
                            chunks.append(current_chunk.strip())
                            current_chunk = s
                        else:
                            current_chunk += (" " if not current_chunk.endswith(("\n", " ")) else "") + s
                    else:
                        chunks.append(current_chunk.strip())
                        current_chunk = s
                else:
                    # Sentence s exceeds hard_max_chars, split by clause boundaries (commas, dashes)
                    clauses = re.split(r"(?<=[,–—])\s+", s)
                    for c in clauses:
                        c = c.strip()
                        if not c:
                            continue
                        if len(c) <= hard_max_chars:
                            if not current_chunk:
                                current_chunk = c
                            elif len(current_chunk) + len(c) + 1 <= target_chars:
                                current_chunk += (" " if not current_chunk.endswith(("\n", " ")) else "") + c
                            elif len(current_chunk) + len(c) + 1 <= hard_max_chars:
                                current_chunk += (" " if not current_chunk.endswith(("\n", " ")) else "") + c
                            else:
                                chunks.append(current_chunk.strip())
                                current_chunk = c
                        else:
                            # Clause exceeds hard_max_chars, split by words
                            words = c.split(" ")
                            for w in words:
                                if not w:
                                    continue
                                if len(w) > hard_max_chars:
                                    if current_chunk:
                                        chunks.append(current_chunk.strip())
                                        current_chunk = ""
                                    for i in range(0, len(w), hard_max_chars):
                                        chunks.append(w[i : i + hard_max_chars])
                                else:
                                    if not current_chunk:
                                        current_chunk = w
                                    elif len(current_chunk) + len(w) + 1 <= hard_max_chars:
                                        current_chunk += " " + w
                                    else:
                                        chunks.append(current_chunk.strip())
                                        current_chunk = w

    if current_chunk and current_chunk.strip():
        chunks.append(current_chunk.strip())

    return [c for c in chunks if c.strip()]
