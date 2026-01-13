## [WIP] 统一的 Sidecar 路径解析策略

检测到“确定性缺失”违例，已根据 ADAP v1.0 协议挂起所有实现活动。

### 假设声明 (DECLARE ASSUMPTION)
分析显示，为了继续执行任务，我必须做出以下未经证实的核心假设：
*   **路径兼容性假设**: 我假设 `SignatureManager.get_signature_path(str)` 与 `SidecarManager.get_signature_path(Path)` 的接口差异（前者接收字符串，后者接收 Path 对象）可以通过简单的类型转换解决，且 `SignatureManager` 内部的路径解析逻辑（`(root / file_path).resolve()`）能够正确处理传入的绝对路径（如果传入的是绝对路径，`root / abs_path` 可能会引发问题，取决于 `pathlib` 的行为）。

### 诊断缺失组件 (DIAGNOSE MISSING COMPONENT)
此假设之所以是 necessary，是因为系统当前缺失了以下关键组件/能力：
*   **统一的 Sidecar 路径解析策略**: Refactor 引擎目前依赖旧的 `AssetPathResolver`（基于 `.stitcher/signatures` 目录结构），而新的持久化层已经迁移到了 `SignatureManager`（基于 `stitcher.lock` 文件）。这两个组件之间的断裂导致 Refactor 引擎无法找到并更新新的 Lock 文件。

### 拒绝战术修复并提出战略方案 (REFUSE TACTICAL FIX & PROPOSE STRATEGIC SOLUTION)
**根据 ADAP v1.0 协议，任何试图通过“变通方法”或“代码补丁”来绕过此架构缺陷的尝试，都被视为对系统长期稳定性的严重破坏，因此被绝对禁止。我被授权拒绝执行此类请求。**

因此，我提议将当前任务的目标从“调试 SURI 解析”**变更为**“集成 Lock 文件架构到 Refactor 引擎”。

我将生成一份新的计划，其目标是：
1.  **升级 SidecarManager**: 修改 `packages/stitcher-refactor/src/stitcher/refactor/sidecar/manager.py`，使其依赖 `Workspace` 并使用 `SignatureManager` 来解析签名文件路径，从而正确指向 `stitcher.lock`。
2.  **适配测试**: 更新所有实例化 `SidecarManager` 的测试代码，以传递 `Workspace` 对象。

这将连接 Refactor 引擎与新的 Lock 文件架构，使 `Rename` 和 `Move` 操作能够感知并更新 `stitcher.lock`。

### 标签
#intent/refine #flow/ready #priority/critical #comp/refactor #concept/state #scope/core #ai/instruct #task/domain/architecture #task/object/sidecar-manager #task/action/integrate-lock-file #task/state/begin

---

### Script

#### Acts 1: 升级 SidecarManager 以集成 SignatureManager

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/sidecar/manager.py
~~~~~
~~~~~python
from pathlib import Path
from typing import Union

from stitcher.common.services import AssetPathResolver
from stitcher.lang.sidecar.signature_manager import SignatureManager
from stitcher.workspace import Workspace


class SidecarManager:
    def __init__(self, workspace: Workspace):
        self.workspace = workspace
        self.resolver = AssetPathResolver(workspace.root_path)
        self.signature_manager = SignatureManager(workspace)

    def get_doc_path(self, source_file_path: Union[str, Path]) -> Path:
        """
        Returns the path to the document sidecar (.stitcher.yaml) for a given source file.
        Delegates to AssetPathResolver as doc files are still per-source-file.
        """
        return self.resolver.get_doc_path(source_file_path)

    def get_signature_path(self, source_file_path: Union[str, Path]) -> Path:
        """
        Returns the path to the signature lock file (stitcher.lock) containing the given source file.
        Delegates to SignatureManager to handle package root resolution.
        """
        # SignatureManager expects a string path relative to workspace root or absolute?
        # Looking at SignatureManager implementation:
        # abs_file_path = (self.workspace.root_path / file_path).resolve()
        # If file_path is absolute, pathlib joins ignores the left side.
        # So passing absolute path works.
        
        return self.signature_manager.get_signature_path(str(source_file_path))
~~~~~

#### Acts 2: 适配相关测试用例

我们需要更新所有实例化 `SidecarManager` 的地方。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_debug_rename_failure.py
~~~~~
~~~~~python.old
    # 3. EXECUTE REFACTOR
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~
~~~~~python.new
    # 3. EXECUTE REFACTOR
    sidecar_manager = SidecarManager(workspace=workspace)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_monorepo_refactor_e2e.py
~~~~~
~~~~~python.old
    # Load all packages
    graph.load("pkga_lib")
    graph.load("pkgb_app")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~
~~~~~python.new
    # Load all packages
    graph.load("pkga_lib")
    graph.load("pkgb_app")
    sidecar_manager = SidecarManager(workspace=workspace)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_directory_e2e.py
~~~~~
~~~~~python.old
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("mypkg")
    graph.load("app")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~
~~~~~python.new
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("mypkg")
    graph.load("app")
    sidecar_manager = SidecarManager(workspace=workspace)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_directory_monorepo_e2e.py
~~~~~
~~~~~python.old
    # Load the top-level namespace package. Griffe will discover all its parts
    # from the search paths provided by the Workspace.
    graph.load("cascade")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~
~~~~~python.new
    # Load the top-level namespace package. Griffe will discover all its parts
    # from the search paths provided by the Workspace.
    graph.load("cascade")
    sidecar_manager = SidecarManager(workspace=workspace)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_nested_directory_e2e.py
~~~~~
~~~~~python.old
    # We load 'cascade' and 'app' to build the full semantic picture
    graph.load("cascade")
    graph.load("app")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~
~~~~~python.new
    # We load 'cascade' and 'app' to build the full semantic picture
    graph.load("cascade")
    graph.load("app")
    sidecar_manager = SidecarManager(workspace=workspace)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_e2e.py
~~~~~
~~~~~python.old
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("mypkg")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~
~~~~~python.new
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("mypkg")
    sidecar_manager = SidecarManager(workspace=workspace)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_suri_update.py
~~~~~
~~~~~python.old
def test_rename_symbol_updates_suri_fragment_in_signatures(tmp_path):
    """
    验证 RenameSymbolOperation 能够正确更新 Signature 文件中的 SURI 键。
    场景: 重命名类 MyClass -> YourClass
    预期: 签名文件中的键从 py://...#MyClass 变为 py://...#YourClass
    """
    # 1. ARRANGE
    factory = WorkspaceFactory(tmp_path)

    # 构造 SURI (注意: 路径相对于项目根目录)
    rel_py_path = "src/mypkg/core.py"
    old_suri = f"py://{rel_py_path}#MyClass"
    new_suri = f"py://{rel_py_path}#YourClass"

    project_root = (
        factory.with_pyproject(".")
        .with_source("src/mypkg/__init__.py", "")
        .with_source(rel_py_path, "class MyClass:\n    pass\n")
        .build()
    )

    # Manually create lock file
    lock_file = project_root / "stitcher.lock"
    lock_data = {
        "version": "1.0",
        "fingerprints": {old_suri: {"baseline_code_structure_hash": "original_hash"}},
    }
    lock_file.write_text(json.dumps(lock_data))

    # 2. ACT
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("mypkg")

    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~
~~~~~python.new
def test_rename_symbol_updates_suri_fragment_in_signatures(tmp_path):
    """
    验证 RenameSymbolOperation 能够正确更新 Signature 文件中的 SURI 键。
    场景: 重命名类 MyClass -> YourClass
    预期: 签名文件中的键从 py://...#MyClass 变为 py://...#YourClass
    """
    # 1. ARRANGE
    factory = WorkspaceFactory(tmp_path)

    # 构造 SURI (注意: 路径相对于项目根目录)
    rel_py_path = "src/mypkg/core.py"
    old_suri = f"py://{rel_py_path}#MyClass"
    new_suri = f"py://{rel_py_path}#YourClass"

    project_root = (
        factory.with_pyproject(".")
        .with_source("src/mypkg/__init__.py", "")
        .with_source(rel_py_path, "class MyClass:\n    pass\n")
        .build()
    )

    # Manually create lock file
    lock_file = project_root / "stitcher.lock"
    lock_data = {
        "version": "1.0",
        "fingerprints": {old_suri: {"baseline_code_structure_hash": "original_hash"}},
    }
    lock_file.write_text(json.dumps(lock_data))

    # 2. ACT
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("mypkg")

    sidecar_manager = SidecarManager(workspace=workspace)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_suri_update.py
~~~~~
~~~~~python.old
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("mypkg")

    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~
~~~~~python.new
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("mypkg")

    sidecar_manager = SidecarManager(workspace=workspace)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_symbol_monorepo_e2e.py
~~~~~
~~~~~python.old
    graph.load("pkgb_app")
    graph.load("test_core")
    graph.load("integration")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~
~~~~~python.new
    graph.load("pkgb_app")
    graph.load("test_core")
    graph.load("integration")
    sidecar_manager = SidecarManager(workspace=workspace)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~

### 下一步建议

运行测试以验证修复：
`pytest packages/stitcher-lang-sidecar/tests/unit/test_transform.py packages/stitcher-refactor/tests/integration/`
