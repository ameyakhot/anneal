"""Tree-sitter based source code parser.

Detects language from file extension, parses source files, and extracts
function/class definitions and import statements. Supports Python, JavaScript,
TypeScript, Go, Rust, Java, Ruby, C, and C++.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from tree_sitter_language_pack import get_parser

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Definition:
    name: str
    kind: str  # "function" or "class"
    line_start: int  # 1-indexed
    line_end: int  # 1-indexed
    parent: Optional[str] = None


@dataclass
class Import:
    module: str


# ---------------------------------------------------------------------------
# Extension -> language mapping
# ---------------------------------------------------------------------------

_EXT_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".rb": "ruby",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".cs": "c_sharp",
}

# ---------------------------------------------------------------------------
# Node types that represent definitions, keyed by language
# ---------------------------------------------------------------------------

# Maps (language, node_type) -> kind
_DEFINITION_NODE_TYPES: dict[str, dict[str, str]] = {
    "python": {
        "function_definition": "function",
        "class_definition": "class",
    },
    "javascript": {
        "function_declaration": "function",
        "class_declaration": "class",
    },
    "typescript": {
        "function_declaration": "function",
        "class_declaration": "class",
    },
    "go": {
        "function_declaration": "function",
        "method_declaration": "function",
        "type_declaration": "class",
    },
    "rust": {
        "function_item": "function",
        "struct_item": "class",
        "impl_item": "class",
        "enum_item": "class",
        "trait_item": "class",
    },
    "java": {
        "method_declaration": "function",
        "class_declaration": "class",
        "interface_declaration": "class",
    },
    "ruby": {
        "method": "function",
        "class": "class",
        "module": "class",
    },
    "c": {
        "function_definition": "function",
    },
    "cpp": {
        "function_definition": "function",
        "class_specifier": "class",
        "struct_specifier": "class",
    },
    "c_sharp": {
        "method_declaration": "function",
        "class_declaration": "class",
        "interface_declaration": "class",
    },
}

# Node types that represent imports, keyed by language
_IMPORT_NODE_TYPES: dict[str, set[str]] = {
    "python": {"import_statement", "import_from_statement"},
    "javascript": {"import_statement"},
    "typescript": {"import_statement"},
    "go": {"import_declaration"},
    "rust": {"use_declaration"},
    "java": {"import_declaration"},
    "ruby": set(),
    "c": {"preproc_include"},
    "cpp": {"preproc_include"},
    "c_sharp": {"using_directive"},
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_language(filename: str) -> Optional[str]:
    """Map a filename (or path) to a tree-sitter language name.

    Returns None if the extension is not recognised.
    """
    ext = os.path.splitext(filename)[1].lower()
    return _EXT_MAP.get(ext)


def parse_file(file_path: str | Path) -> tuple[list[Definition], list[Import]]:
    """Parse a source file and return extracted definitions and imports.

    Returns ``([], [])`` for unsupported file types.
    """
    file_path = Path(file_path)
    language = detect_language(file_path.name)
    if language is None:
        return [], []

    try:
        parser = get_parser(language)
    except Exception:
        return [], []

    source = file_path.read_bytes()
    tree = parser.parse(source)

    definitions: list[Definition] = []
    imports: list[Import] = []

    def_types = _DEFINITION_NODE_TYPES.get(language, {})
    imp_types = _IMPORT_NODE_TYPES.get(language, set())

    _walk(tree.root_node, def_types, imp_types, language, definitions, imports)

    return definitions, imports


# ---------------------------------------------------------------------------
# Tree walking helpers
# ---------------------------------------------------------------------------


def _walk(
    node,
    def_types: dict[str, str],
    imp_types: set[str],
    language: str,
    definitions: list[Definition],
    imports: list[Import],
    parent_name: Optional[str] = None,
) -> None:
    """Recursively walk tree-sitter nodes to extract definitions and imports."""
    node_type = node.type

    # --- Definitions -------------------------------------------------------
    if node_type in def_types:
        kind = def_types[node_type]
        name = _extract_name(node, language, node_type)
        if name:
            definitions.append(
                Definition(
                    name=name,
                    kind=kind,
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1,
                    parent=parent_name,
                )
            )
            # Recurse into children with this node as parent
            for child in node.children:
                _walk(child, def_types, imp_types, language, definitions, imports, parent_name=name)
            return

    # --- Imports -----------------------------------------------------------
    if node_type in imp_types:
        module = _extract_import_module(node, language)
        if module:
            imports.append(Import(module=module))
        # Don't recurse into import nodes
        return

    # --- Recurse -----------------------------------------------------------
    for child in node.children:
        _walk(child, def_types, imp_types, language, definitions, imports, parent_name=parent_name)


def _extract_name(node, language: str, node_type: str) -> Optional[str]:
    """Extract the name from a definition node."""
    # Most languages use the 'name' field
    name_node = node.child_by_field_name("name")
    if name_node:
        return name_node.text.decode("utf-8")

    # Go type_declaration wraps a type_spec which has the name
    if language == "go" and node_type == "type_declaration":
        for child in node.children:
            if child.type == "type_spec":
                inner_name = child.child_by_field_name("name")
                if inner_name:
                    return inner_name.text.decode("utf-8")

    # Fallback: first named child that is an identifier
    for child in node.children:
        if child.type == "identifier":
            return child.text.decode("utf-8")

    return None


def _extract_import_module(node, language: str) -> Optional[str]:
    """Extract the module name from an import node."""
    if language == "python":
        if node.type == "import_from_statement":
            # 'from X import Y' — module is the dotted_name after 'from'
            module_node = node.child_by_field_name("module_name")
            if module_node:
                return module_node.text.decode("utf-8")
            # Fallback: find first dotted_name child
            for child in node.children:
                if child.type == "dotted_name":
                    return child.text.decode("utf-8")
        elif node.type == "import_statement":
            # 'import X' — module is the dotted_name
            for child in node.children:
                if child.type == "dotted_name":
                    return child.text.decode("utf-8")

    elif language in ("javascript", "typescript"):
        # import ... from 'module'
        source_node = node.child_by_field_name("source")
        if source_node:
            text = source_node.text.decode("utf-8")
            return text.strip("'\"")

    elif language == "go":
        # import "fmt" or import ( "fmt" )
        for child in node.children:
            if child.type == "import_spec":
                path_node = child.child_by_field_name("path")
                if path_node:
                    return path_node.text.decode("utf-8").strip('"')
            elif child.type == "import_spec_list":
                for spec in child.children:
                    if spec.type == "import_spec":
                        path_node = spec.child_by_field_name("path")
                        if path_node:
                            return path_node.text.decode("utf-8").strip('"')
            elif child.type == "interpreted_string_literal":
                return child.text.decode("utf-8").strip('"')

    elif language == "java":
        # import com.example.Foo;
        for child in node.children:
            if child.type == "scoped_identifier":
                return child.text.decode("utf-8")

    elif language == "rust":
        # use std::io;
        for child in node.children:
            if child.type in ("scoped_identifier", "use_as_clause", "scoped_use_list", "identifier"):
                return child.text.decode("utf-8")

    elif language in ("c", "cpp"):
        # #include <stdio.h> or #include "foo.h"
        for child in node.children:
            if child.type in ("system_lib_string", "string_literal"):
                text = child.text.decode("utf-8")
                return text.strip('<>"')

    elif language == "c_sharp":
        for child in node.children:
            if child.type in ("qualified_name", "identifier"):
                return child.text.decode("utf-8")

    return None
