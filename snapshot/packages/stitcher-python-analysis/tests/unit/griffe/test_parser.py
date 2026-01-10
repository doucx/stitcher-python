import pytest
from stitcher.python.analysis.griffe.parser import GriffePythonParser


@pytest.fixture
def parser():
    return GriffePythonParser()


class TestGriffeParserAliases:
    def test_parse_import_from(self, parser: GriffePythonParser):
        code = "from os.path import join, splitext"
        module = parser.parse(code)

        assert len(module.attributes) == 2

        join_attr = next(a for a in module.attributes if a.name == "join")
        assert join_attr.alias_target == "os.path.join"
        assert join_attr.value is None

        splitext_attr = next(a for a in module.attributes if a.name == "splitext")
        assert splitext_attr.alias_target == "os.path.splitext"

    def test_parse_import_from_with_alias(self, parser: GriffePythonParser):
        code = "from pathlib import Path as P"
        module = parser.parse(code)

        assert len(module.attributes) == 1

        path_attr = module.attributes[0]
        assert path_attr.name == "P"
        assert path_attr.alias_target == "pathlib.Path"

    def test_parse_import_module(self, parser: GriffePythonParser):
        code = "import json"
        module = parser.parse(code)

        assert len(module.attributes) == 1

        json_attr = module.attributes[0]
        assert json_attr.name == "json"
        assert json_attr.alias_target == "json"

    def test_parse_import_module_with_alias(self, parser: GriffePythonParser):
        code = "import sys as system"
        module = parser.parse(code)

        assert len(module.attributes) == 1

        sys_attr = module.attributes[0]
        assert sys_attr.name == "system"
        assert sys_attr.alias_target == "sys"

    def test_attributes_and_aliases_coexist(self, parser: GriffePythonParser):
        code = """
import os
from pathlib import Path

MY_CONSTANT = "hello"
"""
        module = parser.parse(code)

        assert len(module.attributes) == 3

        os_attr = next(a for a in module.attributes if a.name == "os")
        assert os_attr.alias_target == "os"

        path_attr = next(a for a in module.attributes if a.name == "Path")
        assert path_attr.alias_target == "pathlib.Path"

        const_attr = next(a for a in module.attributes if a.name == "MY_CONSTANT")
        assert const_attr.value == "'hello'"
        assert const_attr.alias_target is None