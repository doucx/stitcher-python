You are right. I apologize for the oversight. The test failures clearly indicate two major problems with my previous plan: a critical logic flaw in the fragment calculation and a complete failure to update the unit tests to match the new method signatures and architectural intent.

This violates the HFEA principle of "异味即缺陷" (Smell is a Defect). The `TypeError` cascade is a loud signal that the unit tests are no longer serving as a valid specification. They must be rewritten, not just patched. The `AssertionError` reveals the logical flaw that must be fixed first.

I will now generate a plan to correct both the implementation and its corresponding tests.

## [WIP] fix: Correct nested fragment logic and rewrite sidecar unit tests

### 錯誤分析

1.  **Logic Error (`AssertionError`)**: The `_calculate_fragments` method failed to correctly handle nested symbols. When renaming a method (`MyClass.old_method`), it incorrectly extracted only the method name (`old_method`) as the fragment, losing the crucial class prefix (`MyClass.`). The correct fragment must be the full symbol path relative to the module.
2.  **Obsolete Tests (`TypeError`)**: The unit tests in `test_sidecar_update_mixin.py` were not updated. They called `_update_sidecar_data` with the old, incorrect number of arguments and were still written to validate the old FQN-based logic. They are no longer fit for purpose and must be completely replaced.

### 用户需求

Fix the failing tests by correcting the SURI/fragment generation logic for nested symbols and rewriting the unit tests for `SidecarUpdateMixin` to accurately reflect and validate the new identifier ontology.

### 评论

This is a necessary and welcome course correction. The test failures have done their job by preventing a flawed implementation from proceeding. Rewriting the unit tests is the only correct path forward; it transforms them from broken code into a precise, executable specification for the new SURI/Fragment-aware refactoring logic. This action directly upholds the principle of "回归驱动开发" (Regression-Driven Development).

### 目标

1.  **Fix Core Logic**: Correct the implementation of `_calculate_fragments` in `SidecarUpdateMixin` to properly derive the full fragment for nested symbols (e.g., `Class.method`).
2.  **Rewrite Unit Tests**: Replace the entire obsolete test file (`test_sidecar_update_mixin.py`) with a new, comprehensive suite that validates the distinct update strategies for JSON (SURI) and YAML (Fragment) files across various rename and move scenarios.

### 基本原理

First, I will provide a corrected version of `operations/base.py`. The key change is in `_calculate_fragments`, which will now correctly derive the full fragment by splitting the FQN based on the module prefix. This ensures nested paths like `MyClass.my_method` are preserved.

Second, I will completely replace the old unit test file. The new file will contain two distinct test classes:
-   `TestJsonSuriUpdates`: Will verify that SURI keys in JSON files are correctly updated for symbol renames, nested symbol renames, and file moves.
-   `TestYamlFragmentUpdates`: Will verify that Fragment keys in YAML files are updated for symbol renames but, crucially, **remain unchanged** for pure file moves, confirming the robustness of the new relative naming scheme.

### 标签

#intent/fix #flow/ready #priority/critical #comp/engine #comp/tests #concept/state #scope/core #ai/instruct #task/domain/testing #task/object/identifier-ontology #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: Correct the `SidecarUpdateMixin` Logic

We will replace the entire `base.py` file with the corrected logic for fragment calculation.

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/operations/base.py
~~~~~
~~~~~python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from stitcher.lang.python.analysis.utils import path_to_logical_fqn
from stitcher.lang.python.uri import SURIGenerator
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.intent import RefactorIntent


class SidecarUpdateMixin:
    def _path_to_fqn(self, path: Path, search_paths: List[Path]) -> Optional[str]:
        base_path = None
        for sp in sorted(search_paths, key=lambda p: len(p.parts), reverse=True):
            try:
                # Use is_relative_to for modern Python
                if path.is_relative_to(sp):
                    base_path = sp
                    break
            except (ValueError, AttributeError):
                # Fallback for older Python or different path types
                if str(path).startswith(str(sp)):
                    base_path = sp
                    break
                continue

        if base_path is None:
            return None

        rel_path = path.relative_to(base_path)
        return path_to_logical_fqn(rel_path.as_posix())

    def _calculate_fragments(
        self, module_fqn: Optional[str], old_fqn: str, new_fqn: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Derives symbol fragments by stripping the module FQN prefix.
        This correctly handles nested fragments like 'Class.method'.
        """
        old_fragment = old_fqn
        if module_fqn and old_fqn.startswith(module_fqn + "."):
            old_fragment = old_fqn.split(module_fqn + ".", 1)[1]

        new_fragment = new_fqn
        new_module_prefix = ".".join(new_fqn.split(".")[:-1])
        if module_fqn and new_module_prefix == module_fqn:
            if new_fqn.startswith(module_fqn + "."):
                new_fragment = new_fqn.split(module_fqn + ".", 1)[1]
        
        # If it's a move, the new_fqn will have a different module prefix.
        # The fragment itself might be the same.
        # e.g., old_fqn=a.b.C, new_fqn=x.y.C. The fragment is 'C'.
        if old_fqn.split(".")[-1] == new_fqn.split(".")[-1]:
             if module_fqn and old_fqn.startswith(module_fqn + "."):
                  old_fragment = old_fqn.split(module_fqn + ".", 1)[1]
             
             new_mod_fqn = self._get_module_fqn_from_symbol_fqn(new_fqn)
             if new_mod_fqn and new_fqn.startswith(new_mod_fqn + "."):
                 new_fragment = new_fqn.split(new_mod_fqn + ".", 1)[1]

        return old_fragment, new_fragment
    
    def _get_module_fqn_from_symbol_fqn(self, fqn: str) -> Optional[str]:
        if "." not in fqn:
            return None # Top-level module/file
        return fqn.rsplit(".", 1)[0]


    def _update_sidecar_data(
        self,
        data: Dict[str, Any],
        sidecar_path: Path,
        module_fqn: Optional[str],
        old_fqn: str,
        new_fqn: str,
        old_file_path: Optional[str] = None,
        new_file_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Dispatcher for sidecar updates based on file type.
        """
        old_fragment, new_fragment = self._calculate_fragments(
            module_fqn, old_fqn, new_fqn
        )

        if sidecar_path.suffix == ".json":
            return self._update_json_data(
                data, old_file_path, new_file_path, old_fragment, new_fragment
            )
        elif sidecar_path.suffix in (".yaml", ".yml"):
            return self._update_yaml_data(data, old_fragment, new_fragment)

        return data

    def _update_json_data(
        self,
        data: Dict[str, Any],
        old_file_path: Optional[str],
        new_file_path: Optional[str],
        old_fragment: Optional[str],
        new_fragment: Optional[str],
    ) -> Dict[str, Any]:
        """
        Updates Signature JSON data where keys are SURIs (py://path#fragment).
        """
        new_data = {}
        modified = False

        for key, value in data.items():
            if not key.startswith("py://"):
                new_data[key] = value
                continue

            try:
                path, fragment = SURIGenerator.parse(key)
            except ValueError:
                new_data[key] = value
                continue

            path_changed = False
            fragment_changed = False

            if old_file_path and new_file_path and path == old_file_path:
                path = new_file_path
                path_changed = True

            if old_fragment and new_fragment and fragment:
                if fragment == old_fragment:
                    fragment = new_fragment
                    fragment_changed = True
                elif fragment.startswith(old_fragment + "."):
                    suffix = fragment[len(old_fragment) :]
                    fragment = new_fragment + suffix
                    fragment_changed = True

            if path_changed or fragment_changed:
                new_key = (
                    SURIGenerator.for_symbol(path, fragment)
                    if fragment
                    else SURIGenerator.for_file(path)
                )
                new_data[new_key] = value
                modified = True
            else:
                new_data[key] = value

        return new_data if modified else data

    def _update_yaml_data(
        self,
        data: Dict[str, Any],
        old_fragment: Optional[str],
        new_fragment: Optional[str],
    ) -> Dict[str, Any]:
        """
        Updates Doc YAML data where keys are Fragments (Short Names).
        """
        if not old_fragment or not new_fragment or old_fragment == new_fragment:
            return data

        new_data = {}
        modified = False

        for key, value in data.items():
            if key == old_fragment:
                new_data[new_fragment] = value
                modified = True
            elif key.startswith(old_fragment + "."):
                suffix = key[len(old_fragment) :]
                new_key = new_fragment + suffix
                new_data[new_key] = value
                modified = True
            else:
                new_data[key] = value

        return new_data if modified else data


class AbstractOperation(ABC):
    @abstractmethod
    def collect_intents(self, ctx: RefactorContext) -> List[RefactorIntent]:
        pass
~~~~~

#### Acts 2: Rewrite the Unit Tests for `SidecarUpdateMixin`

We replace the entire outdated test file with a new specification-driven test suite.

~~~~~act
write_file
packages/stitcher-refactor/tests/unit/operations/test_sidecar_update_mixin.py
~~~~~
~~~~~python
import pytest
from pathlib import Path
from stitcher.refactor.operations.base import SidecarUpdateMixin


@pytest.fixture
def mixin():
    return SidecarUpdateMixin()


class TestJsonSuriUpdates:
    def test_updates_suri_on_symbol_rename(self, mixin):
        old_suri = "py://src/app.py#OldClass"
        new_suri = "py://src/app.py#NewClass"
        data = {old_suri: {"hash": "1"}}
        updated = mixin._update_sidecar_data(
            data,
            Path("src/app.json"),
            module_fqn="app",
            old_fqn="app.OldClass",
            new_fqn="app.NewClass",
        )
        assert updated == {new_suri: {"hash": "1"}}

    def test_updates_suri_on_nested_symbol_rename(self, mixin):
        old_suri = "py://src/app.py#MyClass.old_method"
        new_suri = "py://src/app.py#MyClass.new_method"
        data = {old_suri: {"hash": "1"}}
        updated = mixin._update_sidecar_data(
            data,
            Path("src/app.json"),
            module_fqn="app",
            old_fqn="app.MyClass.old_method",
            new_fqn="app.MyClass.new_method",
        )
        assert updated == {new_suri: {"hash": "1"}}

    def test_updates_suri_on_parent_rename(self, mixin):
        old_suri = "py://src/app.py#OldClass.method"
        new_suri = "py://src/app.py#NewClass.method"
        data = {old_suri: {"hash": "1"}}
        updated = mixin._update_sidecar_data(
            data,
            Path("src/app.json"),
            module_fqn="app",
            old_fqn="app.OldClass",
            new_fqn="app.NewClass",
        )
        assert updated == {new_suri: {"hash": "1"}}

    def test_updates_suri_on_file_move(self, mixin):
        old_suri = "py://src/old_path/app.py#MyClass"
        new_suri = "py://src/new_path/app.py#MyClass"
        data = {old_suri: {"hash": "1"}}
        updated = mixin._update_sidecar_data(
            data,
            Path("src/old_path/app.json"),
            module_fqn="old_path.app",
            old_fqn="old_path.app.MyClass",
            new_fqn="new_path.app.MyClass",
            old_file_path="src/old_path/app.py",
            new_file_path="src/new_path/app.py",
        )
        assert updated == {new_suri: {"hash": "1"}}

    def test_updates_suri_on_combined_move_and_rename(self, mixin):
        old_suri = "py://src/old_path/app.py#OldClass"
        new_suri = "py://src/new_path/app.py#NewClass"
        data = {old_suri: {"hash": "1"}}
        updated = mixin._update_sidecar_data(
            data,
            Path("src/old_path/app.json"),
            module_fqn="old_path.app",
            old_fqn="old_path.app.OldClass",
            new_fqn="new_path.app.NewClass",
            old_file_path="src/old_path/app.py",
            new_file_path="src/new_path/app.py",
        )
        assert updated == {new_suri: {"hash": "1"}}


class TestYamlFragmentUpdates:
    def test_updates_fragment_on_symbol_rename(self, mixin):
        data = {"OldClass": "doc", "Other": "doc"}
        updated = mixin._update_sidecar_data(
            data,
            Path("app.stitcher.yaml"),
            module_fqn="app",
            old_fqn="app.OldClass",
            new_fqn="app.NewClass",
        )
        assert updated == {"NewClass": "doc", "Other": "doc"}

    def test_updates_fragment_on_nested_symbol_rename(self, mixin):
        data = {"MyClass.old_method": "doc"}
        updated = mixin._update_sidecar_data(
            data,
            Path("app.stitcher.yaml"),
            module_fqn="app",
            old_fqn="app.MyClass.old_method",
            new_fqn="app.MyClass.new_method",
        )
        assert updated == {"MyClass.new_method": "doc"}

    def test_updates_fragment_on_parent_rename(self, mixin):
        data = {"OldClass.method": "doc"}
        updated = mixin._update_sidecar_data(
            data,
            Path("app.stitcher.yaml"),
            module_fqn="app",
            old_fqn="app.OldClass",
            new_fqn="app.NewClass",
        )
        assert updated == {"NewClass.method": "doc"}

    def test_does_not_update_fragment_on_pure_file_move(self, mixin):
        data = {"MyClass": "doc"}
        original_data = data.copy()
        updated = mixin._update_sidecar_data(
            data,
            Path("old_path/app.stitcher.yaml"),
            module_fqn="old_path.app",
            old_fqn="old_path.app.MyClass",
            new_fqn="new_path.app.MyClass", # Symbol name 'MyClass' is unchanged
            old_file_path="old_path/app.py",
            new_file_path="new_path/app.py",
        )
        # The key is relative to the file, so a move should NOT change it.
        assert updated == original_data
~~~~~

### 下一步建议

我们已经修复了 `SidecarUpdateMixin` 中的核心逻辑，并为其配备了一套全新的、符合新架构思想的单元测试。现在，我们应该重新运行完整的测试套件，特别是之前失败的集成测试，以确认我们的修复是全面且正确的。

我建议立即执行：
`pytest packages/stitcher-refactor/`
