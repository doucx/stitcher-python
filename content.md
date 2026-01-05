好的，我将增强 `stitcher-refactor` 的测试套件，使其能够正确处理 monorepo 结构的项目。

当前的实现对代码库的结构做了一些简单的假设（例如，所有源码都在一个顶层 `src` 目录或项目根目录下），这在 monorepo 场景下会失效。monorepo 通常在 `packages/` 目录下包含多个独立的包，每个包都有自己的 `src` 目录。

为了支持这一点，我将执行一个计划，主要包含以下三个步骤：

1.  **增强 `SemanticGraph`**: 修改其初始化逻辑，使其能自动扫描并识别 `packages/*/src` 这样的 monorepo 结构，并将它们全部添加到 `griffe` 的搜索路径中。
2.  **改进 FQN 解析**: 更新 `MoveFileOperation` 中的 `_path_to_fqn` 方法，使其能够根据增强后的多搜索路径，从文件路径正确地推断出模块的 FQN。
3.  **新增端到端测试**: 创建一个新的集成测试用例，专门模拟在 monorepo 结构下，跨包引用时进行文件移动的重构操作，并验证其正确性。

这将确保重构引擎在更复杂的、真实世界的项目布局中依然稳健可靠。

## [WIP] feat(refactor): 增强重构引擎以支持 Monorepo 结构

### 用户需求

增强 `packages/stitcher-refactor` 的测试套件和核心逻辑，使其能够正确地发现、解析和重构采用 monorepo 布局（即在 `packages/` 目录下包含多个子包）的项目。

### 评论

这是一个至关重要的改进。现实世界中的许多大型项目都采用 monorepo 结构来管理代码。让 `stitcher-refactor` 支持这种结构，意味着它从一个只能处理简单项目的工具，演变为一个能够应对复杂、多包架构的健壮的工程工具。这极大地扩展了其适用范围和实用价值。

### 目标

1.  **修改 `SemanticGraph`**: 更新其构造函数，使其能够自动探测并添加 monorepo 风格的 `packages/*/src` 目录到 `griffe` 的搜索路径中。
2.  **更新 `MoveFileOperation`**: 调整其内部的 `_path_to_fqn` 辅助函数，使其能够基于多个搜索路径正确地将文件路径解析为 FQN。
3.  **创建新的 E2E 测试**: 编写一个名为 `test_monorepo_refactor_e2e.py` 的新测试，该测试将：
    *   使用 `WorkspaceFactory` 构建一个包含两个子包 (`pkg_a`, `pkg_b`) 的 monorepo 结构。
    *   在 `pkg_b` 中引用 `pkg_a` 的代码。
    *   执行一个 `MoveFileOperation` 来移动 `pkg_a` 中的一个模块。
    *   断言 `pkg_b` 中的导入语句被正确更新。

### 基本原理

问题的核心在于 `griffe` 需要知道所有可能的源码根目录（`search_paths`）才能正确解析导入和符号。

1.  **搜索路径发现**: 当前 `SemanticGraph` 只检查顶层的 `src` 目录或项目根。新的实现将扩展这个逻辑，在初始化时扫描 `packages/` 目录。对于找到的每个子目录，如果它包含一个 `src` 目录，那么 `packages/<sub-package>/src` 将被添加为一个有效的源码根。这将允许 `griffe` 正确地“看到”所有包。

2.  **FQN 推断**: `_path_to_fqn` 函数之前简单地从路径中移除顶层的 `src`。在 monorepo 中，路径可能是 `packages/pkg_a/src/pkga_lib/core.py`，其 FQN 应该是 `pkga_lib.core`。新的逻辑将迭代所有已发现的 `search_paths`，找到与当前文件路径最匹配（最长）的前缀，并基于该前缀计算相对路径，从而正确推断出 FQN。

3.  **端到端验证**: 新的测试用例将是这个重构的最终防线。通过创建一个跨包依赖的场景，我们可以确保当一个包的内部结构发生变化时，依赖它的其他包也能被 `stitcher-refactor` 自动、正确地更新，从而证明整个 monorepo 支持是完整且有效的。

### 标签

#intent/refine #intent/tooling #flow/ready #priority/high #comp/tests #comp/engine #concept/state #scope/core #scope/dx #ai/instruct #task/domain/testing #task/object/monorepo-support #task/action/implementation #task/state/begin

---

### Script

#### Acts 1: 更新 SemanticGraph 以自动发现 Monorepo 搜索路径

我将修改 `SemanticGraph` 的 `__init__` 方法，使其能够智能地发现并包含 monorepo 的 `packages/*/src` 目录。同时，我会将发现的搜索路径存储在实例上，以便后续使用。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py
~~~~~
~~~~~python.old
class SemanticGraph:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        search_paths = [self.root_path]
        src_path = self.root_path / "src"
        if src_path.is_dir():
            search_paths.insert(0, src_path)

        self._griffe_loader = griffe.GriffeLoader(search_paths=search_paths)
        self._modules: Dict[str, griffe.Module] = {}
        self.registry = UsageRegistry()
~~~~~
~~~~~python.new
class SemanticGraph:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        search_paths = []

        # 1. Add top-level src if it exists
        top_level_src = self.root_path / "src"
        if top_level_src.is_dir():
            search_paths.append(top_level_src)

        # 2. Add packages from monorepo structure
        packages_dir = self.root_path / "packages"
        if packages_dir.is_dir():
            for package_path in packages_dir.iterdir():
                if package_path.is_dir():
                    package_src_path = package_path / "src"
                    if package_src_path.is_dir():
                        search_paths.append(package_src_path)

        # 3. Fallback to root if no specific source directories were found
        if not search_paths:
            search_paths.append(self.root_path)

        # Store unique, sorted paths for deterministic behavior
        self.search_paths = sorted(list(set(search_paths)))

        self._griffe_loader = griffe.GriffeLoader(search_paths=self.search_paths)
        self._modules: Dict[str, griffe.Module] = {}
        self.registry = UsageRegistry()
~~~~~

#### Acts 2: 更新 MoveFileOperation 以正确解析 FQN

现在 `SemanticGraph` 知道了所有的搜索路径，我需要更新 `MoveFileOperation._path_to_fqn` 来利用这些信息。它将不再硬编码地剥离 `src`，而是根据 `search_paths` 列表动态地计算模块的根。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_file.py
~~~~~
~~~~~python.old
    def _path_to_fqn(self, path: Path, root_path: Path) -> Optional[str]:
        try:
            rel_path = path.relative_to(root_path)
        except ValueError:
            # Path is not inside root
            return None

        parts = list(rel_path.parts)

        # Heuristic: if 'src' is the first part, strip it (common layout)
        if parts and parts[0] == "src":
            parts = parts[1:]

        if not parts:
            return None
~~~~~
~~~~~python.new
    def _path_to_fqn(self, path: Path, search_paths: List[Path]) -> Optional[str]:
        # Find the source root that is a prefix of the given path.
        # We sort by length descending to find the most specific root first.
        # e.g., given /proj/packages/a/src and /proj, for a file in the former,
        # we want to match the former.
        base_path = None
        for sp in sorted(search_paths, key=lambda p: len(p.parts), reverse=True):
            try:
                path.relative_to(sp)
                base_path = sp
                break
            except ValueError:
                continue

        if base_path is None:
            # Fallback for files not in a designated src root (e.g., top-level scripts)
            # This logic might need refinement based on project structure.
            # For now, let's assume it must be in a search path.
            return None

        rel_path = path.relative_to(base_path)
        parts = list(rel_path.parts)
~~~~~
~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_file.py
~~~~~
~~~~~python.old
    def analyze(self, ctx: RefactorContext) -> List[FileOp]:
        rename_ops: List[FileOp] = []
        move_ops: List[FileOp] = []
        content_update_ops: List[FileOp] = []

        old_module_fqn = self._path_to_fqn(self.src_path, ctx.graph.root_path)
        new_module_fqn = self._path_to_fqn(self.dest_path, ctx.graph.root_path)

        if old_module_fqn and new_module_fqn and old_module_fqn != new_module_fqn:
            # 1. Update external references to the moved symbols
~~~~~
~~~~~python.new
    def analyze(self, ctx: RefactorContext) -> List[FileOp]:
        rename_ops: List[FileOp] = []
        move_ops: List[FileOp] = []
        content_update_ops: List[FileOp] = []

        old_module_fqn = self._path_to_fqn(self.src_path, ctx.graph.search_paths)
        new_module_fqn = self._path_to_fqn(self.dest_path, ctx.graph.search_paths)

        if old_module_fqn and new_module_fqn and old_module_fqn != new_module_fqn:
            # 1. Update external references to the moved symbols
~~~~~

#### Acts 3: 创建 Monorepo 端到端测试用例

最后，我将创建一个新的测试文件，它将构建一个 monorepo 结构并验证重构操作的正确性。

~~~~~act
write_file
packages/stitcher-refactor/tests/integration/test_monorepo_refactor_e2e.py
~~~~~
~~~~~python
import json
import yaml
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.transaction import TransactionManager, MoveFileOp
from stitcher.refactor.operations.move_file import MoveFileOperation
from stitcher.test_utils import WorkspaceFactory


def test_move_file_in_monorepo_updates_cross_package_imports(tmp_path):
    # 1. ARRANGE: Build a monorepo workspace
    # packages/
    #   pkg_a/
    #     src/
    #       pkga_lib/
    #         __init__.py
    #         core.py  (defines SharedClass)
    #   pkg_b/
    #     src/
    #       pkgb_app/
    #         __init__.py
    #         main.py (imports SharedClass from pkga_lib.core)
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_source("packages/pkg_a/src/pkga_lib/__init__.py", "")
        .with_source(
            "packages/pkg_a/src/pkga_lib/core.py", "class SharedClass: pass"
        )
        .with_docs(
            "packages/pkg_a/src/pkga_lib/core.stitcher.yaml",
            {"pkga_lib.core.SharedClass": "A shared class."},
        )
        .with_raw_file(
            ".stitcher/signatures/packages/pkg_a/src/pkga_lib/core.json",
            json.dumps({"pkga_lib.core.SharedClass": {"hash": "abc"}}),
        )
        .with_source("packages/pkg_b/src/pkgb_app/__init__.py", "")
        .with_source(
            "packages/pkg_b/src/pkgb_app/main.py",
            "from pkga_lib.core import SharedClass\n\ninstance = SharedClass()",
        )
        .build()
    )

    # Define paths for the operation
    src_path = project_root / "packages/pkg_a/src/pkga_lib/core.py"
    dest_path = project_root / "packages/pkg_a/src/pkga_lib/utils/tools.py"
    consumer_path = project_root / "packages/pkg_b/src/pkgb_app/main.py"

    # 2. ACT
    # The new SemanticGraph should automatically find both 'src' dirs
    graph = SemanticGraph(root_path=project_root)
    assert project_root / "packages/pkg_a/src" in graph.search_paths
    assert project_root / "packages/pkg_b/src" in graph.search_paths

    # Load all packages
    graph.load("pkga_lib")
    graph.load("pkgb_app")
    ctx = RefactorContext(graph=graph)

    op = MoveFileOperation(src_path, dest_path)
    file_ops = op.analyze(ctx)

    tm = TransactionManager(project_root)
    for fop in file_ops:
        if isinstance(fop, MoveFileOp):
            tm.add_move(fop.path, fop.dest)
        else:
            tm.add_write(fop.path, fop.content)
    tm.commit()

    # 3. ASSERT
    # A. File system verification
    assert not src_path.exists()
    assert dest_path.exists()
    dest_yaml = dest_path.with_suffix(".stitcher.yaml")
    assert dest_yaml.exists()
    dest_sig_path = (
        project_root
        / ".stitcher/signatures/packages/pkg_a/src/pkga_lib/utils/tools.json"
    )
    assert dest_sig_path.exists()

    # B. Cross-package import verification
    updated_consumer_code = consumer_path.read_text()
    expected_import = "from pkga_lib.utils.tools import SharedClass"
    assert expected_import in updated_consumer_code

    # C. Sidecar FQN verification
    new_yaml_data = yaml.safe_load(dest_yaml.read_text())
    expected_fqn = "pkga_lib.utils.tools.SharedClass"
    assert expected_fqn in new_yaml_data
    assert new_yaml_data[expected_fqn] == "A shared class."

    new_sig_data = json.loads(dest_sig_path.read_text())
    assert expected_fqn in new_sig_data
    assert new_sig_data[expected_fqn] == {"hash": "abc"}

~~~~~

### 下一步建议

我们已经为 monorepo 结构的核心重构路径（文件移动）提供了支持和验证。下一步可以考虑：

*   **符号重命名**: 编写一个类似的 monorepo 端到端测试，用于验证 `RenameSymbolOperation` 是否也能正确更新跨包的符号引用。
*   **性能优化**: 对于非常大的 monorepo，`griffe` 的全量加载可能会很慢。可以探索基于变更文件进行增量分析的策略，以提高大规模重构的响应速度。
*   **更复杂的布局**: 测试更复杂的 monorepo 结构，例如没有 `src` 目录的扁平包布局，或者命名空间包。
