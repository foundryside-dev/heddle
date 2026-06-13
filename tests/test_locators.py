from __future__ import annotations

from warpline.locators import python_entity_locators


def test_python_entity_locators_include_path_and_qualname() -> None:
    source = """
class Service:
    def handle(self):
        return 1

def helper():
    return 2
"""
    assert python_entity_locators("pkg/app.py", source) == [
        "python:class:pkg/app.py::Service",
        "python:function:pkg/app.py::Service.handle",
        "python:function:pkg/app.py::helper",
    ]


def test_python_entity_locators_fall_back_to_file_for_syntax_error() -> None:
    assert python_entity_locators("pkg/bad.py", "def nope(:\n") == ["file:pkg/bad.py"]
