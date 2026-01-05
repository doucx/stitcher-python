你好。
根据你的指示，我将通过增强 `_UsageVisitor` 的逻辑来修复 `test_move_directory_monorepo_e2e.py` 中的断言错误。核心问题在于 `_UsageVisitor` 在处理 `Import` 和 `ImportFrom` 节点时，没有递归地将模块路径的各个部分（如 `cascade.engine.core`）注册为对应的 FQN 用法。这导致当重构操作针对路径中的中间部分（如 `core` 目录）时，`RenameSymbolOperation` 无法找到并更新这些引用。

我将重写 `_UsageVisitor`，特别是引入递归的 `_register_module_parts` 方法，确保导入路径的每一个层级都被正确注册。

简要回答：
修正 `_UsageVisitor` 以递归注册导入路径的各个部分，从而支持对模块路径中间层级的重命名操作。

## [WIP] fix(refactor): 增强 _UsageVisitor 以支持递归注册导入路径

### 错误分析
在 `test_move_directory_monorepo_e2e.py` 中，我们将 `cascade/engine/core` 移动到了 `cascade/runtime/core`。这意味着 FQN 前缀 `cascade.engine.core` 变更为了 `cascade.runtime.core`。
`MoveDirectoryOperation` 会为该目录移动生成一系列操作，其中包括针对 `core` 目录的重命名（隐含地或显式地）。
在消费者文件 `app.py` 中，导入语句为 `from cascade.engine.core.logic import EngineLogic`。
原有的 `_UsageVisitor` 仅将整个模块路径 `cascade.engine.core.logic` 注册为 `cascade.engine.core.logic` 的用法。
当 `RenameSymbolOperation` 尝试查找 `cascade.engine.core` 的引用时，它在 `app.py` 中找不到匹配项，因为它只知道 `cascade.engine.core.logic` 的用法。
通过在 `_UsageVisitor` 中递归注册，我们将 `cascade.engine.core` 也注册为 FQN `cascade.engine.core` 的用法，从而使重命名操作能够匹配并更新它。

### 用户需求
增强静态分析能力，使 `stitcher-refactor` 能够像 IDE 一样准确解析 `import` 语句中的模块路径链，并将其每一部分都注册为可重构的目标，以支持复杂的重构场景（如移动中间层级的包）。

### 评论
这是一个关键的架构增强。通过“递归剥离”导入路径，我们不仅解决了当前的测试失败，还为未来支持更细粒度的重构（如重命名父包、拆分包）奠定了坚实的基础。这使得 `stitcher-refactor` 的语义理解能力上了一个台阶。

### 目标
1.  修改 `stitcher/refactor/engine/graph.py`。
2.  在 `_UsageVisitor` 中实现 `_register_module_parts`，使其递归地将 `Attribute` 链（或 `Name`）注册到对应的 FQN 部分。
3.  确保 `visit_Import` 和 `visit_ImportFrom` 正确调用此新逻辑。

### 基本原理
LibCST 的 `Attribute` 节点是嵌套结构（例如 `a.b.c` 是 `Attr(Attr(a, b), c)`）。完全限定名 (FQN) 也是点分隔的字符串。这两者在结构上是同构的。我们可以通过同步遍历这两者（剥离 Attribute 的 `value` 和 FQN 的最后一个点号部分），将每一个子节点映射到其对应的 FQN。这确保了无论重构目标是路径链中的哪一部分，都能找到对应的 CST 节点进行替换。

### 标签
#intent/fix #flow/ready #priority/high #comp/engine #concept/graph #scope/core #ai/instruct #task/domain/refactor #task/object/usage-visitor #task/action/enhance #task/state/continue

---

### Script

#### Acts 1: 重写 `graph.py` 以增强 `_UsageVisitor`
我们将使用 `write_file` 更新 `stitcher/refactor/engine/graph.py`，因为改动涉及 `_UsageVisitor` 的多个方法和核心逻辑，整体重写比 patch 更安全且易于阅读。

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py
~~~~~
~~~~~python
import libcst as cst
from libcst import helpers
from libcst.metadata import PositionProvider
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, DefaultDict
from collections import defaultdict
import griffe
from stitcher.refactor.workspace import Workspace
from libcst.helpers import (
    get_absolute_module_from_package_for_import,
    get_full_name_for_node,
)


@dataclass
class UsageLocation:
    file_path: Path
    lineno: int
    col_offset: int
    end_lineno: int
    end_col_offset: int

    @property
    def range_tuple(self):
        return (self.lineno, self.col_offset)


@dataclass
class SymbolNode:
    fqn: str
    kind: str
    path: Path


class UsageRegistry:
    def __init__(self):
        # Key: Target FQN (The "Real" Name, e.g., "pkg.mod.Class")
        # Value: List of locations where this symbol is used/referenced
        self._index: DefaultDict[str, List[UsageLocation]] = defaultdict(list)

    def register(self, target_fqn: str, location: UsageLocation):
        self._index[target_fqn].append(location)

    def get_usages(self, target_fqn: str) -> List[UsageLocation]:
        return self._index.get(target_fqn, [])


class _UsageVisitor(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(
        self,
        file_path: Path,
        local_symbols: Dict[str, str],
        registry: UsageRegistry,
        current_module_fqn: Optional[str] = None,
        is_init_file: bool = False,
    ):
        self.file_path = file_path
        self.local_symbols = local_symbols  # map: local_name -> target_fqn
        self.registry = registry
        self.current_module_fqn = current_module_fqn
        self.is_init_file = is_init_file

        # Calculate current package for relative import resolution
        self.current_package = None
        if current_module_fqn:
            if is_init_file:
                self.current_package = current_module_fqn
            elif "." in current_module_fqn:
                self.current_package = current_module_fqn.rsplit(".", 1)[0]
            else:
                self.current_package = ""  # Top-level module, no package

    def _register_node(self, node: cst.CSTNode, fqn: str):
        pos = self.get_metadata(PositionProvider, node)
        loc = UsageLocation(
            file_path=self.file_path,
            lineno=pos.start.line,
            col_offset=pos.start.column,
            end_lineno=pos.end.line,
            end_col_offset=pos.end.column,
        )
        self.registry.register(fqn, loc)

    def _register_module_parts(self, node: cst.CSTNode, absolute_module: str):
        """
        Recursively registers the parts of a module node (Attribute chain or Name)
        against the corresponding parts of the absolute FQN.

        e.g. node=`a.b.c`, absolute_module=`pkg.a.b.c`
        Registers:
          `a.b.c` -> `pkg.a.b.c`
          `a.b`   -> `pkg.a.b`
          `a`     -> `pkg.a`
        """
        curr_node = node
        curr_fqn = absolute_module

        # Iterate down the Attribute chain
        # Note: Attribute(value=Attribute(value=Name(a), attr=Name(b)), attr=Name(c)) corresponds to a.b.c
        # The 'value' is the prefix.
        while isinstance(curr_node, cst.Attribute):
            self._register_node(curr_node, curr_fqn)

            # Peel off the last part of the FQN
            if "." in curr_fqn:
                curr_fqn = curr_fqn.rsplit(".", 1)[0]
            else:
                # If we run out of FQN parts but still have attributes, stop (mismatch or aliasing)
                break

            curr_node = curr_node.value

        # Register the base Name node
        if isinstance(curr_node, cst.Name):
            self._register_node(curr_node, curr_fqn)

    def visit_Name(self, node: cst.Name):
        # In LibCST, Name nodes appear in definitions (ClassDef.name),
        # references (a = 1), and aliases (import x as y).
        target_fqn = self.local_symbols.get(node.value)
        if target_fqn:
            self._register_node(node, target_fqn)

    def visit_Import(self, node: cst.Import) -> Optional[bool]:
        for alias in node.names:
            # alias.name is the module being imported (Name or Attribute)
            # e.g. import a.b.c
            absolute_module = get_full_name_for_node(alias.name)
            if absolute_module:
                self._register_module_parts(alias.name, absolute_module)
        return True

    def visit_ImportFrom(self, node: cst.ImportFrom) -> Optional[bool]:
        # 1. Resolve absolute module path
        absolute_module = None

        try:
            package_ctx = self.current_package if self.current_package != "" else None

            absolute_module = get_absolute_module_from_package_for_import(
                package_ctx, node
            )
        except Exception:
            pass

        if absolute_module:
            # Register the module part itself (e.g. 'mypkg.core' in 'from mypkg.core import ...')
            if node.module:
                self._register_module_parts(node.module, absolute_module)

            # 2. Handle the names being imported
            # from pkg import A, B -> A is pkg.A
            for alias in node.names:
                if isinstance(alias, cst.ImportAlias):
                    name_node = alias.name
                    imported_name = get_full_name_for_node(name_node)

                    if imported_name:
                        full_fqn = f"{absolute_module}.{imported_name}"
                        self._register_node(name_node, full_fqn)

        return True

    def visit_Attribute(self, node: cst.Attribute) -> Optional[bool]:
        # Handle: mypkg.core.OldHelper
        # This comes in as Attribute(value=..., attr=Name(OldHelper))

        # We try to resolve the full name of the expression
        full_name = helpers.get_full_name_for_node(node)
        if not full_name:
            return True

        parts = full_name.split(".")
        if not parts:
            return True

        root_name = parts[0]
        root_fqn = self.local_symbols.get(root_name)

        if root_fqn:
            # Reconstruct the absolute FQN
            suffix = ".".join(parts[1:])
            absolute_fqn = f"{root_fqn}.{suffix}" if suffix else root_fqn

            # We register the Attribute node itself as the usage.
            self._register_node(node, absolute_fqn)

        return True


class SemanticGraph:
    def __init__(self, workspace: Workspace):
        self.workspace = workspace
        self.root_path = (
            workspace.root_path
        )  # Keep for compatibility with downstream operations
        self.search_paths = self.workspace.get_search_paths()
        self._griffe_loader = griffe.GriffeLoader(search_paths=self.search_paths)
        self._modules: Dict[str, griffe.Module] = {}
        self.registry = UsageRegistry()

    def load(self, package_name: str, submodules: bool = True) -> None:
        # 1. Load with Griffe (resolves aliases)
        module = self._griffe_loader.load(package_name, submodules=submodules)
        self._modules[package_name] = module

        # 2. Resolve aliases to ensure we have full resolution
        self._griffe_loader.resolve_aliases()

        # 3. Build Usage Registry
        self._build_registry(module)

    def _build_registry(self, module: griffe.Module):
        # Recursively process members that are modules
        for member in module.members.values():
            if isinstance(member, griffe.Module) and not member.is_alias:
                self._build_registry(member)

        # Process the current module
        if module.filepath:
            self._scan_module_usages(module)

    def _scan_module_usages(self, module: griffe.Module):
        # 1. Build Local Symbol Table (Name -> FQN)
        local_symbols: Dict[str, str] = {}

        for name, member in module.members.items():
            if member.is_alias:
                try:
                    target_fqn = member.target_path
                    local_symbols[name] = target_fqn
                except Exception:
                    pass
            else:
                # It's a definition (Class, Function) in this module.
                local_symbols[name] = member.path

        # 2. Parse CST and scan
        try:
            source = module.filepath.read_text(encoding="utf-8")
            wrapper = cst.MetadataWrapper(cst.parse_module(source))
            visitor = _UsageVisitor(module.filepath, local_symbols, self.registry, current_module_fqn=module.path, is_init_file=module.filepath.name == "__init__.py")
            wrapper.visit(visitor)
        except Exception:
            # Handle syntax errors or IO errors gracefully
            pass

    def get_module(self, package_name: str) -> Optional[griffe.Module]:
        return self._modules.get(package_name)

    def iter_members(self, package_name: str) -> List[SymbolNode]:
        module = self.get_module(package_name)
        if not module:
            return []
        nodes = []

        def _collect(obj: griffe.Object):
            path = obj.filepath if obj.filepath else Path("")
            kind = "unknown"
            if obj.is_module:
                kind = "module"
            elif obj.is_class:
                kind = "class"
            elif obj.is_function:
                kind = "function"
            elif obj.is_attribute:
                kind = "attribute"
            nodes.append(SymbolNode(fqn=obj.path, kind=kind, path=path))
            if hasattr(obj, "members"):
                for member in obj.members.values():
                    if not member.is_alias:
                        _collect(member)

        _collect(module)
        return nodes
~~~~~

### 下一步建议
一旦此修复应用，`test_move_directory_monorepo_e2e.py` 应该就能通过。建议运行所有测试以确认没有回归，并验证新的递归注册逻辑是否正常工作。之后，可以继续进行 `MoveDirectoryOperation` 相关的其他功能增强或清理工作。
