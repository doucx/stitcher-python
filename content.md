Excellent. This is a sound architectural decision that aligns perfectly with the principles of modularity and separation of concerns. Decoupling the Sidecar transformation logic from the core refactoring planner is a critical step.

I am ready to proceed. I will now generate the plan to create the new `SidecarTransformer` component within the `stitcher-lang-sidecar` package, which involves creating the new transform module, updating the package's dependencies, and exposing the new components through its `__init__.py`.

## [WIP] feat(refactor): Create SidecarTransformer to decouple transformation logic

### 用户需求

用户要求将 `SidecarUpdateMixin` 的逻辑从 `stitcher-refactor` 包中剥离，并在 `stitcher-lang-sidecar` 包中创建一个新的、独立的 `SidecarTransformer` 组件。这个新组件将专门负责处理 Sidecar 文件（`.yaml`, `.json`）内容的转换，使其与 I/O 和核心规划逻辑解耦。

### 评论

这是一个高质量的架构重构。将特定语言（Sidecar 格式）的转换策略从通用的“规划器”(`Planner`)中移出，可以：
1.  **提升内聚性**：Sidecar 的读（`Adapter`）、写（`Transformer`）逻辑将位于同一个包内。
2.  **降低耦合度**：`stitcher-refactor` 将不再关心 Sidecar 的内部语法（SURI vs Fragment），只负责提供高级别的“意图”（如 `old_fqn -> new_fqn`）。
3.  **增强可扩展性**：未来支持新的 Sidecar 格式将不再需要修改核心的 `refactor` 包。

### 目标

1.  在 `stitcher-lang-sidecar` 包中创建一个新的 `transform.py` 文件。
2.  在该文件中定义 `SidecarTransformContext` 数据类和 `SidecarTransformer` 类。
3.  将 `SidecarUpdateMixin` 中的核心转换逻辑（`_calculate_fragments`, `_update_json_data`, `_update_yaml_data`）迁移到 `SidecarTransformer` 中，并重构为无状态的方法。
4.  为 `stitcher-lang-sidecar` 添加对 `stitcher-lang-python` 的依赖，以使用 SURI 和 FQN 工具。
5.  更新 `stitcher-lang-sidecar` 的 `__init__.py` 以导出新的 `SidecarTransformer` 组件。

### 基本原理

我们将创建一个新的 `transform.py` 模块来承载 `SidecarTransformer`。这个 Transformer 的核心方法 `transform` 将接收一个包含所有重构上下文的 `SidecarTransformContext` 对象，并根据文件类型分派给内部的 JSON (SURI) 或 YAML (Fragment) 转换逻辑。为了使其能够处理 FQN 和 SURI，我们需要更新 `pyproject.toml`，为 `stitcher-lang-sidecar` 添加对 `stitcher-lang-python` 的依赖。最后，通过更新 `__init__.py`，我们将新组件暴露给系统的其他部分（主要是 `Planner`），为后续重构 `Planner` 做好准备。

### 标签
#intent/refine #flow/ready #priority/high #comp/refactor #comp/lang-sidecar #concept/transformation #scope/core #ai/instruct #task/domain/refactor #task/object/sidecar-logic #task/action/decoupling #task/state/begin

---

### Script

#### Acts 1: 创建 SidecarTransformer 模块

我们首先创建 `transform.py` 文件，其中包含 `SidecarTransformer` 类和 `SidecarTransformContext` 数据类。这是本次重构的核心，它将原本分散在 Mixin 中的逻辑集中到一个专用的、无状态的组件中。

~~~~~act
write_file
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/transform.py
~~~~~
~~~~~python
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from stitcher.lang.python.uri import SURIGenerator


@dataclass
class SidecarTransformContext:
    """
    Contextual information required to transform a sidecar file's content.
    This is provided by the Planner.
    """

    # The FQN of the module associated with the sidecar file, before the change.
    old_module_fqn: Optional[str]
    # The FQN of the module after the change (e.g., after a file move).
    new_module_fqn: Optional[str]
    # The full FQN of the symbol being changed, before the change.
    old_fqn: str
    # The full FQN of the symbol after the change.
    new_fqn: str
    # The relative path of the source file, before the change. Used for SURI updates.
    old_file_path: Optional[str] = None
    # The relative path of the source file, after the change. Used for SURI updates.
    new_file_path: Optional[str] = None


class SidecarTransformer:
    """
    Encapsulates the logic for transforming the content of sidecar files (.yaml, .json)
    in response to refactoring operations like symbol renames or file moves.
    This class is stateless and operates on data dictionaries, decoupling it from I/O.
    """

    def transform(
        self,
        sidecar_path: Path,
        data: Dict[str, Any],
        context: SidecarTransformContext,
    ) -> Dict[str, Any]:
        """
        Main entry point for transformation. Dispatches to the correct
        handler based on the sidecar file type.
        """
        old_fragment, new_fragment = self._calculate_fragments(
            context.old_module_fqn,
            context.new_module_fqn,
            context.old_fqn,
            context.new_fqn,
        )

        if sidecar_path.suffix == ".json":
            return self._transform_json_data(
                data,
                context.old_file_path,
                context.new_file_path,
                old_fragment,
                new_fragment,
            )
        elif sidecar_path.suffix in (".yaml", ".yml"):
            return self._transform_yaml_data(data, old_fragment, new_fragment)

        return data

    def _calculate_fragments(
        self,
        old_module_fqn: Optional[str],
        new_module_fqn: Optional[str],
        old_fqn: str,
        new_fqn: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        # --- Calculate Old Fragment ---
        old_fragment = old_fqn
        if old_module_fqn and old_fqn.startswith(old_module_fqn + "."):
            old_fragment = old_fqn.split(old_module_fqn + ".", 1)[1]
        elif old_module_fqn and old_fqn == old_module_fqn:
            old_fragment = None  # Represents the module itself

        # --- Calculate New Fragment ---
        new_fragment = new_fqn
        if new_module_fqn and new_fqn.startswith(new_module_fqn + "."):
            new_fragment = new_fqn.split(new_module_fqn + ".", 1)[1]
        elif new_module_fqn and new_fqn == new_module_fqn:
            new_fragment = None

        if old_fqn == old_module_fqn:
            new_fragment = None

        return old_fragment, new_fragment

    def _transform_json_data(
        self,
        data: Dict[str, Any],
        old_file_path: Optional[str],
        new_file_path: Optional[str],
        old_fragment: Optional[str],
        new_fragment: Optional[str],
    ) -> Dict[str, Any]:
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

            if old_fragment is not None and new_fragment is not None and fragment:
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

    def _transform_yaml_data(
        self,
        data: Dict[str, Any],
        old_fragment: Optional[str],
        new_fragment: Optional[str],
    ) -> Dict[str, Any]:
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
~~~~~

#### Acts 2: 更新包依赖和 `__init__.py`

为了让 `SidecarTransformer` 能够访问 Python 语言的特定工具（如 `SURIGenerator`），我们需要更新 `pyproject.toml` 来添加 `stitcher-lang-python` 作为依赖。同时，我们更新 `__init__.py` 文件，将新创建的 `SidecarTransformer` 和 `SidecarTransformContext` 暴露出来，使其成为包的公共 API。

~~~~~act
patch_file
packages/stitcher-lang-sidecar/pyproject.toml
~~~~~
~~~~~toml
dependencies = [
    "stitcher-spec",
    "stitcher-common",
    "ruamel.yaml>=0.17.0",
]

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]

[tool.uv.sources]
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
~~~~~
~~~~~toml
dependencies = [
    "stitcher-spec",
    "stitcher-common",
    "stitcher-lang-python",
    "ruamel.yaml>=0.17.0",
]

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]

[tool.uv.sources]
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
stitcher-lang-python = { workspace = true }
~~~~~

~~~~~act
write_file
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from .adapter import SidecarAdapter
from .parser import parse_doc_references, parse_signature_references
from .transform import SidecarTransformContext, SidecarTransformer

__all__ = [
    "SidecarAdapter",
    "parse_doc_references",
    "parse_signature_references",
    "SidecarTransformContext",
    "SidecarTransformer",
]
~~~~~

### 下一步建议

我们已经成功地在 `stitcher-lang-sidecar` 包中创建了新的 `SidecarTransformer`，并解决了其依赖问题。

接下来的关键步骤是：
1.  **重构 `Planner`**：修改 `stitcher-refactor` 中的 `Planner` 类，让它**使用**我们刚刚创建的 `SidecarTransformer`，而不是依赖于 `SidecarUpdateMixin`。
2.  **删除 `SidecarUpdateMixin`**：在 `Planner` 和所有 `Operation` 子类都完成重构后，物理删除 `stitcher-refactor/src/stitcher/refactor/operations/base.py` 文件中的 `SidecarUpdateMixin` 类。

如果您同意，我将准备执行第一步：**重构 `Planner`**。
