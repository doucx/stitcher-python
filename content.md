简要回答
我们正式进入 Phase 3。第一步的目标是建立 `stitcher-refactor` 与 `stitcher-index` 的连接，并用基于 DB 的查询替代昂贵的内存扫描。

## [WIP] feat(refactor): 引入 IndexStore 并适配 Usage 查询

### 用户需求
1.  在 `IndexStore` 中实现 `find_references(target_fqn)` 方法，支持跨文件查找引用。
2.  更新 `RefactorContext` 以包含 `IndexStore` 实例。
3.  重构 `SemanticGraph`：
    *   注入 `IndexStore`。
    *   **移除** 昂贵的 `_scan_module_usages` 调用（不再重复扫描 AST）。
    *   实现 `find_usages(fqn)`，将 DB 结果转换为重构引擎所需的 `UsageLocation` 对象。

### 评论
这是架构融合的关键一步。通过切断 Refactor 对 `UsageScanVisitor` 的直接依赖，我们将大大降低重构操作的启动时间和内存占用，真正实现“一次索引，多次重构”。

### 目标
1.  修改 `packages/stitcher-index/src/stitcher/index/store.py`。
2.  修改 `packages/stitcher-refactor/src/stitcher/refactor/engine/context.py`。
3.  修改 `packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py`。
4.  修改 `packages/stitcher-refactor/src/stitcher/refactor/engine/renamer.py` 以适配新的 API。

### 基本原理
Refactor 引擎不需要知道引用是如何被发现的（是通过实时扫描还是 DB 查询）。通过在 `SemanticGraph` 层抽象 `find_usages` 方法，我们可以在不破坏上层逻辑（如 Renamer）的情况下替换底层实现。

### 标签
#intent/refine #flow/ready #priority/high #comp/refactor #comp/index #concept/state #scope/core #ai/instruct #task/domain/storage #task/object/refactor-engine #task/action/integration #task/state/begin

---

### Script

#### Acts 1: 扩展 IndexStore 支持引用查找

我们需要一个能联表查询（References JOIN Files）的方法，以便获取引用的物理路径。

~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/store.py
~~~~~
~~~~~python.old
    def delete_file(self, file_id: int) -> None:
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
~~~~~
~~~~~python.new
    def delete_file(self, file_id: int) -> None:
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM files WHERE id = ?", (file_id,))

    def find_references(
        self, target_fqn: str
    ) -> List[Tuple[ReferenceRecord, str]]:
        """
        Finds all references to a specific FQN.
        Returns a list of (ReferenceRecord, file_path_str) tuples.
        """
        with self.db.get_connection() as conn:
            # Join references with files to get the path
            rows = conn.execute(
                """
                SELECT r.*, f.path as file_path
                FROM "references" r
                JOIN files f ON r.source_file_id = f.id
                WHERE r.target_fqn = ?
                """,
                (target_fqn,),
            ).fetchall()
            return [
                (ReferenceRecord(**{k: v for k, v in dict(row).items() if k != "file_path"}), row["file_path"])
                for row in rows
            ]
~~~~~

#### Acts 2: 更新 RefactorContext

将 `IndexStore` 注入到上下文中。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/context.py
~~~~~
~~~~~python.old
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from .graph import SemanticGraph


@dataclass
class RefactorContext:
    workspace: Workspace
    graph: SemanticGraph
    sidecar_manager: SidecarManager
~~~~~
~~~~~python.new
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.index.store import IndexStore
from .graph import SemanticGraph


@dataclass
class RefactorContext:
    workspace: Workspace
    graph: SemanticGraph
    sidecar_manager: SidecarManager
    index_store: IndexStore
~~~~~

#### Acts 3: 重构 SemanticGraph

这是核心变更：移除 `UsageRegistry` 和 `_scan_module_usages`，转而使用 `find_usages` 查询 DB。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py
~~~~~
~~~~~python.old
import libcst as cst
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Set
import logging
import griffe
from stitcher.refactor.workspace import Workspace
from stitcher.python.analysis.cst.usage_visitor import UsageScanVisitor, UsageRegistry

log = logging.getLogger(__name__)


@dataclass
class SymbolNode:
    fqn: str
    kind: str
    path: Path


class SemanticGraph:
    def __init__(self, workspace: Workspace):
        self.workspace = workspace
        self.root_path = workspace.root_path
        self.search_paths = self.workspace.get_search_paths()
        self._griffe_loader = griffe.GriffeLoader(search_paths=self.search_paths)
        self._modules: Dict[str, griffe.Module] = {}
        self.registry = UsageRegistry()

    def load(self, package_name: str, submodules: bool = True) -> None:
        module = self._griffe_loader.load(package_name, submodules=submodules)
        # Ensure we are dealing with a Module, not an Alias
        if isinstance(module, griffe.Module):
            self._modules[package_name] = module
            self._griffe_loader.resolve_aliases()
            self._build_registry(module)

    def load_from_workspace(self) -> None:
        # 1. Load all main packages
        for pkg_name in self.workspace.import_to_source_dirs.keys():
            try:
                module = self._griffe_loader.load(pkg_name, submodules=True)
                if isinstance(module, griffe.Module):
                    self._modules[pkg_name] = module
            except Exception as e:
                log.error(f"Failed to load package '{pkg_name}': {e}")
                # We continue loading other packages even if one fails
                continue

        # 2. Load all peripheral files/directories
        for p_dir in self.workspace.peripheral_source_dirs:
            if p_dir.is_dir():
                for py_file in p_dir.rglob("*.py"):
                    try:
                        self._griffe_loader.load(py_file)
                    except Exception as e:
                        log.warning(f"Failed to load peripheral file {py_file}: {e}")
            elif p_dir.is_file() and p_dir.suffix == ".py":
                try:
                    self._griffe_loader.load(p_dir)
                except Exception as e:
                    log.warning(f"Failed to load peripheral file {p_dir}: {e}")

        # 3. Resolve all aliases now that everything is loaded
        self._griffe_loader.resolve_aliases()

        # 4. Build usage registry for everything
        # Fix: ModulesCollection does not have .values(), we must access .members
        for module in self._griffe_loader.modules_collection.members.values():
            self._build_registry(module)

    def _build_registry(
        self, module: griffe.Module, visited: Optional[Set[str]] = None
    ):
        if visited is None:
            visited = set()

        if module.path in visited:
            return
        visited.add(module.path)

        for member in module.members.values():
            if isinstance(member, griffe.Module):
                self._build_registry(member, visited)

        # module.filepath can be a list for namespace packages; we only scan single files
        if module.filepath and isinstance(module.filepath, Path):
            self._scan_module_usages(module)

    def _scan_module_usages(self, module: griffe.Module):
        # We assume module.filepath is a Path here, checked by caller
        if not isinstance(module.filepath, Path):
            return

        local_symbols: Dict[str, str] = {}
        for name, member in module.members.items():
            try:
                if isinstance(member, griffe.Alias):
                    target_fqn = member.target_path
                else:
                    target_fqn = member.path
                local_symbols[name] = target_fqn
            except Exception as e:
                log.warning(f"Failed to resolve symbol '{name}' in {module.path}: {e}")

        try:
            source = module.filepath.read_text(encoding="utf-8")
            wrapper = cst.MetadataWrapper(cst.parse_module(source))
            is_init = module.filepath.name == "__init__.py"
            visitor = UsageScanVisitor(
                module.filepath,
                local_symbols,
                self.registry,
                current_module_fqn=module.path,
                is_init_file=is_init,
            )
            wrapper.visit(visitor)
        except Exception as e:
            log.error(f"Failed to scan usages in {module.filepath}: {e}")
            raise  # Re-raise to ensure tests fail if scanning fails

    def get_module(self, package_name: str) -> Optional[griffe.Module]:
~~~~~
~~~~~python.new
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Set
import logging
import griffe
from stitcher.refactor.workspace import Workspace
from stitcher.index.store import IndexStore
from stitcher.python.analysis.models import UsageLocation, ReferenceType

log = logging.getLogger(__name__)


@dataclass
class SymbolNode:
    fqn: str
    kind: str
    path: Path


class SemanticGraph:
    def __init__(self, workspace: Workspace, index_store: IndexStore):
        self.workspace = workspace
        self.root_path = workspace.root_path
        self.index_store = index_store
        self.search_paths = self.workspace.get_search_paths()
        self._griffe_loader = griffe.GriffeLoader(search_paths=self.search_paths)
        self._modules: Dict[str, griffe.Module] = {}

    def load(self, package_name: str, submodules: bool = True) -> None:
        module = self._griffe_loader.load(package_name, submodules=submodules)
        # Ensure we are dealing with a Module, not an Alias
        if isinstance(module, griffe.Module):
            self._modules[package_name] = module
            self._griffe_loader.resolve_aliases()

    def load_from_workspace(self) -> None:
        # 1. Load all main packages
        for pkg_name in self.workspace.import_to_source_dirs.keys():
            try:
                module = self._griffe_loader.load(pkg_name, submodules=True)
                if isinstance(module, griffe.Module):
                    self._modules[pkg_name] = module
            except Exception as e:
                log.error(f"Failed to load package '{pkg_name}': {e}")
                # We continue loading other packages even if one fails
                continue

        # 2. Load all peripheral files/directories
        for p_dir in self.workspace.peripheral_source_dirs:
            if p_dir.is_dir():
                for py_file in p_dir.rglob("*.py"):
                    try:
                        self._griffe_loader.load(py_file)
                    except Exception as e:
                        log.warning(f"Failed to load peripheral file {py_file}: {e}")
            elif p_dir.is_file() and p_dir.suffix == ".py":
                try:
                    self._griffe_loader.load(p_dir)
                except Exception as e:
                    log.warning(f"Failed to load peripheral file {p_dir}: {e}")

        # 3. Resolve all aliases now that everything is loaded
        self._griffe_loader.resolve_aliases()

    def find_usages(self, target_fqn: str) -> List[UsageLocation]:
        """
        Query the Index DB for usages of the given FQN.
        Maps DB ReferenceRecords to UsageLocation objects.
        """
        db_refs = self.index_store.find_references(target_fqn)
        usages = []
        for ref, file_path_str in db_refs:
            abs_path = self.root_path / file_path_str
            # We map DB 'kind' back to ReferenceType.
            # Assuming DB stores 'symbol' or 'import_path' matching the enum values.
            try:
                ref_type = ReferenceType(ref.kind)
            except ValueError:
                # Fallback or log warning if DB contains unknown kinds
                ref_type = ReferenceType.SYMBOL

            usages.append(
                UsageLocation(
                    file_path=abs_path,
                    lineno=ref.lineno,
                    col_offset=ref.col_offset,
                    end_lineno=ref.end_lineno,
                    end_col_offset=ref.end_col_offset,
                    ref_type=ref_type,
                    target_node_fqn=ref.target_fqn,
                )
            )
        return usages

    def get_module(self, package_name: str) -> Optional[griffe.Module]:
~~~~~

#### Acts 4: 适配 GlobalBatchRenamer

修改 Renamer 以使用 `find_usages` 而不是访问 `registry`。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/renamer.py
~~~~~
~~~~~python.old
    def analyze(self) -> List[WriteFileOp]:
        ops: List[WriteFileOp] = []
        usages_by_file: Dict[Path, List[UsageLocation]] = defaultdict(list)

        # 1. Collect all usages for all renames and group by file
        for old_fqn in self.rename_map.keys():
            usages = self.ctx.graph.registry.get_usages(old_fqn)
            for usage in usages:
                usages_by_file[usage.file_path].append(usage)

        # 2. For each affected file, apply a single transformation that handles ALL renames
~~~~~
~~~~~python.new
    def analyze(self) -> List[WriteFileOp]:
        ops: List[WriteFileOp] = []
        usages_by_file: Dict[Path, List[UsageLocation]] = defaultdict(list)

        # 1. Collect all usages for all renames and group by file
        for old_fqn in self.rename_map.keys():
            usages = self.ctx.graph.find_usages(old_fqn)
            for usage in usages:
                usages_by_file[usage.file_path].append(usage)

        # 2. For each affected file, apply a single transformation that handles ALL renames
~~~~~

### 下一步建议

实现此变更后，`stitcher-refactor` 将不再自建 Usage Registry，而是完全依赖 `stitcher-index`。

我们需要更新 `packages/stitcher-refactor/tests` 下的单元测试，因为这些测试之前可能通过 mock `UsageRegistry` 或假设其行为来工作。现在的测试设置需要提供一个 populated 的 `IndexStore` 或对其进行 mock。

这可能需要一个新的 [WIP] 计划来专门处理测试夹具的迁移。
