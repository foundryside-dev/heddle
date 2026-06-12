from __future__ import annotations

import ast


def python_entity_locators(path: str, source: str) -> list[str]:
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError:
        return [f"file:{path}"]

    locators: list[str] = []

    def visit_body(body: list[ast.stmt], parents: list[str]) -> None:
        for node in body:
            if isinstance(node, ast.ClassDef):
                qualname = ".".join([*parents, node.name])
                locators.append(f"python:class:{path}::{qualname}")
                visit_body(node.body, [*parents, node.name])
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                qualname = ".".join([*parents, node.name])
                locators.append(f"python:function:{path}::{qualname}")
                visit_body(node.body, [*parents, node.name])

    visit_body(tree.body, [])
    return locators or [f"file:{path}"]
