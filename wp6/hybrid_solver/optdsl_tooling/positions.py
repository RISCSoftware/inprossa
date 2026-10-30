"""Conversion between ``ast`` coordinates and LSP positions.

Two encodings disagree and the mismatch is a classic source of off-by-N bugs:

* ``ast`` reports ``col_offset``/``end_col_offset`` as **UTF-8 byte** offsets
  into the line.
* LSP ``Position.character`` is a **UTF-16 code unit** offset.

For pure-ASCII source the two coincide, which is why the bug hides until
somebody writes a non-ASCII character (a ``°`` in a comment, a ``≤`` in a
docstring, an emoji in a string literal). This module is the single place that
converts, so no handler has to think about it.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass


@dataclass(frozen=True)
class Span:
    """A zero-based, half-open range in LSP coordinates."""

    start_line: int
    start_character: int
    end_line: int
    end_character: int


class PositionMapper:
    """Maps ``ast`` byte offsets to LSP UTF-16 positions for one document."""

    def __init__(self, source: str) -> None:
        self._source = source
        # ``splitlines`` would drop the information needed to rebuild offsets,
        # so split on "\n" only and keep the trailing "\r" out of the columns.
        self._lines = source.split("\n")
        self._byte_to_char: list[list[int]] = [self._build_line_map(line) for line in self._lines]

    @staticmethod
    def _build_line_map(line: str) -> list[int]:
        """Return ``byte_offset -> utf16_offset`` for a single line.

        The list is indexed by UTF-8 byte offset and is one element longer than
        the byte length so that an offset pointing just past the last character
        (which ``ast`` does emit for ``end_col_offset``) is representable.
        """
        mapping: list[int] = []
        utf16_offset = 0
        for char in line:
            encoded_length = len(char.encode("utf-8"))
            mapping.extend([utf16_offset] * encoded_length)
            utf16_offset += 2 if ord(char) > 0xFFFF else 1
        mapping.append(utf16_offset)
        return mapping

    def _to_character(self, line: int, byte_offset: int) -> int:
        if line < 0 or line >= len(self._byte_to_char):
            return 0
        mapping = self._byte_to_char[line]
        if byte_offset <= 0:
            return 0
        if byte_offset >= len(mapping):
            return mapping[-1]
        return mapping[byte_offset]

    def span(self, node: ast.AST) -> Span:
        """Return the LSP span of ``node``.

        Nodes synthesised without location information (``lineno`` is ``None``)
        collapse to the start of the document rather than raising.
        """
        start_line = getattr(node, "lineno", None)
        end_line = getattr(node, "end_lineno", None)
        if start_line is None:
            return Span(0, 0, 0, 0)
        if end_line is None:
            end_line = start_line

        start_byte = getattr(node, "col_offset", 0) or 0
        end_byte = getattr(node, "end_col_offset", None)
        if end_byte is None:
            end_byte = len(self._lines[end_line - 1].encode("utf-8")) if end_line - 1 < len(self._lines) else 0

        return Span(
            start_line=start_line - 1,
            start_character=self._to_character(start_line - 1, start_byte),
            end_line=end_line - 1,
            end_character=self._to_character(end_line - 1, end_byte),
        )

    def line_text(self, line: int) -> str:
        """Return the text of a zero-based line, without the line terminator."""
        if line < 0 or line >= len(self._lines):
            return ""
        return self._lines[line].rstrip("\r")

    def offset_to_position(self, offset: int) -> tuple[int, int]:
        """Convert a character offset into the document to ``(line, character)``."""
        if offset <= 0:
            return (0, 0)
        consumed = 0
        for line_index, line in enumerate(self._lines):
            line_length = len(line) + 1  # account for the "\n"
            if consumed + line_length > offset:
                character = offset - consumed
                return (line_index, self._to_character(line_index, len(line[:character].encode("utf-8"))))
            consumed += line_length
        last = len(self._lines) - 1
        return (last, self._to_character(last, len(self._lines[last].encode("utf-8"))))
