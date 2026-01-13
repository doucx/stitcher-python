## [WIP] 健壮的 SURI 处理策略

检测到“确定性缺失”违例，已根据 ADAP v1.0 协议挂起所有实现活动。

### 假设声明 (DECLARE ASSUMPTION)
分析显示，为了继续执行任务，我必须做出以下未经证实的核心假设：
*   **SURI 解析行为假设**: 我假设 `SURIGenerator.parse` 方法（源码不可见）在处理 `py://src/app.py` 这种格式时，错误地将 `src` 识别为 URI 的 `netloc` (主机名) 并将其剥离，导致返回的路径仅为 `app.py`。这是基于测试输出 `py://app.py#NewClass` (丢失了 `src/`) 推导出的结论。

### 诊断缺失组件 (DIAGNOSE MISSING COMPONENT)
此假设之所以是 necessary，是因为系统当前缺失了以下关键组件/能力：
*   **健壮的 SURI 处理策略**: `SidecarTransformer` 当前依赖的 `SURIGenerator` 似乎使用了标准的 `urllib.parse` 逻辑，这对于 `py://relative/path` 这种非标准 URI 格式是不适用的（它会将第一层目录吞掉）。我们缺少一个在 Refactor 上下文中明确定义“如何将 SURI 字符串拆解为文件路径和符号片段”的本地逻辑，而不依赖可能不稳定的外部通用解析器。

### 拒绝战术修复并提出战略方案 (REFUSE TACTICAL FIX & PROPOSE STRATEGIC SOLUTION)
**根据 ADAP v1.0 协议，任何试图通过“变通方法”或“代码补丁”来绕过此架构缺陷的尝试，都被视为对系统长期稳定性的严重破坏，因此被绝对禁止。我被授权拒绝执行此类请求。**

因此，我提议将当前任务的目标从“修复测试失败”**变更为**“重构 SidecarTransformer 的 SURI 处理逻辑”。

我将生成一份新的计划，其目标是：
1.  **内联 SURI 逻辑**: 在 `SidecarTransformer` 内部实现确定性的 SURI 解析与生成逻辑（基于字符串分割而非 URL 解析），彻底解耦对 `SURIGenerator` 的依赖。
2.  **支持 Lock 结构**: 同时实现对 `stitcher.lock` 嵌套结构的递归支持。

这将确保无论底层的 URI 库如何变化，重构引擎对文件路径的处理都是绝对可控和正确的。

### 标签
#intent/refine #flow/ready #priority/critical #comp/runtime #concept/refactor #scope/core #ai/instruct #task/domain/refactoring #task/object/sidecar-transformer #task/action/rewrite-suri-logic #task/state/begin

---

### Script

#### Acts 1: 重构 SidecarTransformer 以内联 SURI 处理逻辑

我们将修改 `packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/transform.py`。
不再导入和使用 `SURIGenerator`，而是使用自定义的 `_parse_suri` 和 `_make_suri` 方法。

~~~~~act
write_file
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/transform.py
~~~~~
~~~~~python
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


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

    def _parse_suri(self, suri: str) -> Tuple[str, Optional[str]]:
        """
        Parses a SURI string into (path, fragment).
        Format: py://<path>#<fragment> or py://<path>
        We do NOT use standard URI parsing because it treats the first path segment
        as the network location (host) for scheme 'py://', causing data loss.
        """
        if not suri.startswith("py://"):
            raise ValueError(f"Invalid SURI scheme: {suri}")

        body = suri[5:]  # Strip 'py://'
        if "#" in body:
            path, fragment = body.split("#", 1)
            return path, fragment
        else:
            return body, None

    def _make_suri(self, path: str, fragment: Optional[str]) -> str:
        """Constructs a SURI string from path and fragment."""
        # Ensure path is normalized (no leading slash, creating 'py:///path' triple slash)
        # We want 'py://path/to/file'
        clean_path = path.lstrip("/")
        if fragment:
            return f"py://{clean_path}#{fragment}"
        return f"py://{clean_path}"

    def _transform_json_data(
        self,
        data: Dict[str, Any],
        old_file_path: Optional[str],
        new_file_path: Optional[str],
        old_fragment: Optional[str],
        new_fragment: Optional[str],
    ) -> Dict[str, Any]:
        # Handle stitcher.lock format (nested fingerprints)
        if "fingerprints" in data and isinstance(data["fingerprints"], dict):
            new_fingerprints = self._transform_json_data(
                data["fingerprints"],
                old_file_path,
                new_file_path,
                old_fragment,
                new_fragment,
            )
            if new_fingerprints is not data["fingerprints"]:
                new_data = data.copy()
                new_data["fingerprints"] = new_fingerprints
                return new_data
            return data

        new_data = {}
        modified = False

        for key, value in data.items():
            if not key.startswith("py://"):
                new_data[key] = value
                continue

            try:
                path, fragment = self._parse_suri(key)
            except ValueError:
                new_data[key] = value
                continue

            original_path, original_fragment = path, fragment
            current_path, current_fragment = path, fragment

            # Normalize paths for comparison
            # We assume old_file_path/new_file_path provided by context are relative/normalized.
            norm_current_path = current_path.lstrip("/")

            if (
                old_file_path
                and new_file_path
                and norm_current_path == old_file_path.lstrip("/")
            ):
                current_path = new_file_path

            if (
                old_fragment is not None
                and new_fragment is not None
                and current_fragment is not None
            ):
                if current_fragment == old_fragment:
                    current_fragment = new_fragment
                elif current_fragment.startswith(old_fragment + "."):
                    suffix = current_fragment[len(old_fragment) :]
                    current_fragment = new_fragment + suffix

            if current_path != original_path or current_fragment != original_fragment:
                new_key = self._make_suri(current_path, current_fragment)
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

### 下一步建议

运行测试以验证新的 SURI 处理逻辑和 stitcher.lock 支持是否有效。
`pytest packages/stitcher-lang-sidecar/tests/unit/test_transform.py packages/stitcher-refactor/tests/integration/`
