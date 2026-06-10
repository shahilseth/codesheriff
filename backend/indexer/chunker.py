"""Code-aware chunking of Python source files using tree-sitter.

Splits a file into one chunk per top-level function or class (decorators
included), plus a single "module" chunk for any remaining top-level code
(imports, constants, etc). This keeps each chunk meaningful on its own,
instead of arbitrary fixed-size text windows.
"""

from dataclasses import dataclass

from tree_sitter import Language, Parser
import tree_sitter_python as tspython

_PY_LANGUAGE = Language(tspython.language())
_PARSER = Parser(_PY_LANGUAGE)

_DEF_TYPES = {
    "function_definition": "function",
    "class_definition": "class",
}


@dataclass
class Chunk:
    text: str
    chunk_type: str  # "function" | "class" | "module"
    name: str
    start_line: int  # 1-indexed, inclusive
    end_line: int  # 1-indexed, inclusive


def chunk_python_file(source: str, file_name: str) -> list[Chunk]:
    """Split Python source into function/class/module-level chunks."""
    source_bytes = source.encode("utf-8")
    tree = _PARSER.parse(source_bytes)
    root = tree.root_node

    chunks: list[Chunk] = []
    leftover_ranges: list[tuple[int, int]] = []

    for node in root.children:
        target = node
        if node.type == "decorated_definition":
            for child in node.children:
                if child.type in _DEF_TYPES:
                    target = child
                    break

        chunk_type = _DEF_TYPES.get(target.type)
        if chunk_type is None:
            leftover_ranges.append((node.start_byte, node.end_byte))
            continue

        chunks.append(Chunk(
            text=source_bytes[node.start_byte:node.end_byte].decode("utf-8"),
            chunk_type=chunk_type,
            name=_node_name(target) or "<anonymous>",
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
        ))

    module_chunk = _build_module_chunk(source_bytes, leftover_ranges, file_name)
    if module_chunk is not None:
        chunks.append(module_chunk)

    return chunks


def _node_name(node) -> str | None:
    """Find the identifier directly under a function/class definition node."""
    for child in node.children:
        if child.type == "identifier":
            return child.text.decode("utf-8")
    return None


def _build_module_chunk(source_bytes: bytes, ranges: list[tuple[int, int]], file_name: str) -> Chunk | None:
    """Bundle leftover top-level code (imports, constants, etc) into one chunk."""
    pieces = [source_bytes[start:end].decode("utf-8") for start, end in ranges]
    text = "\n".join(piece for piece in pieces if piece.strip())
    if not text.strip():
        return None

    first_start = ranges[0][0]
    last_end = ranges[-1][1]
    return Chunk(
        text=text,
        chunk_type="module",
        name=file_name,
        start_line=source_bytes[:first_start].count(b"\n") + 1,
        end_line=source_bytes[:last_end].count(b"\n") + 1,
    )
