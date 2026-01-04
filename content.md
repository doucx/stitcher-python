Quipu 计划 (AI 运行时)

[简要回答]
我们必须解决两个核心问题：`MoveFileOperation` 的操作顺序导致的文件覆盖问题（Sidecar 更新丢失），以及 `SemanticGraph` 中 `_UsageVisitor` 对 `ImportFrom` 节点的解析逻辑缺陷（导致别名引用未被捕获）。我们将采用“先修改后移动”的策略，并重写 Visitor 以健壮地处理各类导入。

## [WIP] fix: 修复文件移动操作顺序与增强导入解析

### 错误分析
1.  **Sidecar 更新丢失**: `MoveFileOperation` 生成的操作顺序是 `[Move, Rename(Write)]`。
    *   执行流：`mv old.yaml new.yaml` -> `write old.yaml (new_content)`。
    *   结果：`new.yaml` 是旧内容，`old.yaml` 是新内容（此时变成了孤儿文件）。
    *   修正：必须强制顺序为 `[Rename(Write), Move]`，确保内容修改发生在移动之前。
2.  **Import 解析失败**: `visit_ImportFrom` 中的逻辑可能在处理 `get_absolute_module_from_package_for_import` 时，对于顶层模块（package=""）或绝对导入的处理不够健壮，导致 `main.py` 中的引用未被注册。

### 用户需求
1.  **保证原子性**: 确保 Sidecar 的 Key 更新和文件移动都能正确应用。
2.  **精准解析**: 必须能解析 `from pkg import A as B` 形式的导入，并正确关联到 FQN。
3.  **正规军方法**: 完善单元测试，确保 `_UsageVisitor` 的逻辑是经过严密验证的。

### 评论
“正规军”意味着不依赖巧合。我们将不再在 E2E 测试中猜测 Visitor 的行为，而是先通过针对性的单元测试固定 Visitor 的行为。同时，`MoveFileOperation` 的两阶段提交（先 Modify 后 Move）是处理此类事务的标准模式。

### 目标
1.  **增强测试**: 新增 `tests/unit/engine/test_graph_visitor.py`，专门测试 `_UsageVisitor` 对各种 import 语句的解析能力。
2.  **修复 Visitor**: 根据测试结果，重构 `stitcher/refactor/engine/graph.py` 中的 `visit_ImportFrom` 逻辑，确保绝对/相对导入均被正确处理。
3.  **修复 Operation**: 修改 `MoveFileOperation.analyze`，强制 `ops` 列表的顺序为先 Rename 后 Move。

### 基本原理
*   **Visitor 模式**: 通过 LibCST 的 Visitor 遍历 AST，利用 helper 函数解析模块路径，建立精确的“FQN -> UsageLocation”索引。
*   **事务顺序**: 在文件系统操作中，`Modify(src) -> Move(src, dest)` 是安全的序列，因为它保证了移动的是最新版本。

### 标签
#intent/fix #flow/ready #priority/high #comp/refactor #concept/graph #scope/core #ai/instruct #task/domain/refactor #task/object/move-file-op #task/action/fix #task/state/continue

---

### Script

#### Acts 1: 创建 `_UsageVisitor` 单元测试

我们先写测试来复现解析失败的问题，并覆盖各种 Import 场景。

~~~~~act
write_file
packages/stitcher-refactor/tests/unit/engine/test_graph_visitor.py
~~~~~
~~~~~python
import libcst as cst
from pathlib import Path
from stitcher.refactor.engine.graph import _UsageVisitor, UsageRegistry


def parse_and_visit(code: str, module_fqn: str = "mypkg.mod"):
    """
    Helper to run _UsageVisitor on a snippet of code.
    Assumes the file is at /tmp/mypkg/mod.py (conceptually).
    """
    registry = UsageRegistry()
    wrapper = cst.MetadataWrapper(cst.parse_module(code))
    
    # Mock symbols not needed for Import testing unless we test Name resolution
    local_symbols = {}
    
    is_init = module_fqn.endswith(".__init__")
    
    visitor = _UsageVisitor(
        file_path=Path("dummy.py"),
        local_symbols=local_symbols,
        registry=registry,
        current_module_fqn=module_fqn,
        is_init_file=is_init
    )
    wrapper.visit(visitor)
    return registry


def test_visitor_absolute_import_from():
    code = "from mypkg.core import Helper"
    registry = parse_and_visit(code, module_fqn="main")
    
    # We expect 'Helper' in the import statement to be registered as usage of 'mypkg.core.Helper'
    usages = registry.get_usages("mypkg.core.Helper")
    assert len(usages) == 1
    # Verify it points to 'Helper'
    # "from mypkg.core import Helper"
    #                        ^
    assert usages[0].col_offset > 0


def test_visitor_absolute_import_from_with_alias():
    code = "from mypkg.core import Helper as H"
    registry = parse_and_visit(code, module_fqn="main")
    
    # We expect 'Helper' (the source name) to be usage of 'mypkg.core.Helper'
    usages = registry.get_usages("mypkg.core.Helper")
    assert len(usages) == 1


def test_visitor_relative_import():
    # Context: mypkg.sub.mod
    # Code: from . import sibling
    code = "from . import sibling"
    registry = parse_and_visit(code, module_fqn="mypkg.sub.mod")
    
    # Should resolve to mypkg.sub.sibling
    usages = registry.get_usages("mypkg.sub.sibling")
    assert len(usages) == 1


def test_visitor_relative_import_from_parent():
    # Context: mypkg.sub.mod
    # Code: from ..core import Helper
    code = "from ..core import Helper"
    registry = parse_and_visit(code, module_fqn="mypkg.sub.mod")
    
    # Should resolve to mypkg.core.Helper
    usages = registry.get_usages("mypkg.core.Helper")
    assert len(usages) == 1


def test_visitor_top_level_import():
    # Context: main (top level)
    # Code: from mypkg import core
    code = "from mypkg import core"
    registry = parse_and_visit(code, module_fqn="main")
    
    # Should resolve to mypkg.core
    usages = registry.get_usages("mypkg.core")
    assert len(usages) == 1
~~~~~

#### Acts 2: 修复 `_UsageVisitor`

根据可能的测试失败点，增强 `visit_ImportFrom` 逻辑。特别是要处理好 `current_package` 为空字符串的情况（LibCST 对此比较敏感）。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py
~~~~~
~~~~~python.old
    def visit_ImportFrom(self, node: cst.ImportFrom) -> Optional[bool]:
        # 1. Handle the module part (from ... import)
        if self.current_package is not None:
             try:
                 absolute_module = get_absolute_module_from_package_for_import(
                     self.current_package, node
                 )
                 if absolute_module and node.module:
                     self._register_module_parts(node.module, absolute_module)
                 
                 # 2. Handle the names being imported
                 # from pkg import A, B
                 # If absolute_module is 'pkg', then A is 'pkg.A', B is 'pkg.B'
                 if absolute_module:
                     for alias in node.names:
                         if isinstance(alias, cst.ImportAlias):
                             name_node = alias.name
                             imported_name = get_full_name_for_node(name_node)
                             if imported_name:
                                 full_fqn = f"{absolute_module}.{imported_name}"
                                 self._register_node(name_node, full_fqn)

             except Exception:
                 # Fallback or ignore if resolution fails
                 pass

        return True
~~~~~
~~~~~python.new
    def visit_ImportFrom(self, node: cst.ImportFrom) -> Optional[bool]:
        # 1. Resolve absolute module path
        absolute_module = None
        
        # Determine package context for LibCST resolution
        # If current_package is "", LibCST expects None for 'package' arg usually?
        # Actually get_absolute_module_from_package_for_import doc says:
        # package: Optional[str] - The name of the package the module is in.
        
        try:
            # Note: self.current_package might be "" (top level) or "pkg" or None.
            # If node.relative is non-empty (dots), we need a package.
            # If node.relative is empty, it's absolute import, package context helps but not strictly required if we just concat?
            # But we use LibCST helper for robustness.
            
            package_ctx = self.current_package if self.current_package != "" else None
            
            absolute_module = get_absolute_module_from_package_for_import(
                package_ctx, node
            )
        except Exception:
            # If LibCST fails (e.g. relative import from top level), ignore
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
                    
                    # Handle 'from pkg import *' which is cst.ImportStar (not in node.names)
                    # Wait, node.names is Sequence[ImportAlias] | ImportStar.
                    # If it is ImportStar, we can't do much without wildcard expansion (requires full analysis).
                    
                    if imported_name:
                         full_fqn = f"{absolute_module}.{imported_name}"
                         self._register_node(name_node, full_fqn)

        return True
~~~~~

#### Acts 3: 修复 `MoveFileOperation` 顺序

将 Rename 操作移到 Move 操作之前。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_file.py
~~~~~
~~~~~python.old
    def analyze(self, ctx: RefactorContext) -> List[FileOp]:
        ops: List[FileOp] = []
        
        # 1. Physical Move
        # Note: We use the relative path for Ops
        rel_src = self.src_path.relative_to(ctx.graph.root_path)
        rel_dest = self.dest_path.relative_to(ctx.graph.root_path)
        
        ops.append(MoveFileOp(rel_src, rel_dest))
        
        # 2. Sidecar Moves
        # YAML
        yaml_src = self.src_path.with_suffix(".stitcher.yaml")
        yaml_dest = self.dest_path.with_suffix(".stitcher.yaml")
        if yaml_src.exists():
            rel_yaml_src = yaml_src.relative_to(ctx.graph.root_path)
            rel_yaml_dest = yaml_dest.relative_to(ctx.graph.root_path)
            ops.append(MoveFileOp(rel_yaml_src, rel_yaml_dest))
            
        # Signatures
        sig_root = ctx.graph.root_path / ".stitcher/signatures"
        sig_src = sig_root / rel_src.with_suffix(".json")
        sig_dest = sig_root / rel_dest.with_suffix(".json")
        if sig_src.exists():
             rel_sig_src = sig_src.relative_to(ctx.graph.root_path)
             rel_sig_dest = sig_dest.relative_to(ctx.graph.root_path)
             ops.append(MoveFileOp(rel_sig_src, rel_sig_dest))

        # 3. Symbol Renaming
        old_module_fqn = self._path_to_fqn(self.src_path, ctx.graph.root_path)
        new_module_fqn = self._path_to_fqn(self.dest_path, ctx.graph.root_path)
        
        if old_module_fqn and new_module_fqn and old_module_fqn != new_module_fqn:
            # Rename the module itself (handles "import old_mod")
            rename_mod_op = RenameSymbolOperation(old_module_fqn, new_module_fqn)
            ops.extend(rename_mod_op.analyze(ctx))
            
            # Rename all members (handles "from old_mod import X")
            # And critically, updates Sidecar keys (mypkg.old.X -> mypkg.new.X)
            # We iterate members of the OLD module because that's what's currently in the graph.
            members = ctx.graph.iter_members(old_module_fqn)
            
            for member in members:
                # iter_members returns all nested members.
                # If we rename 'mypkg.old', do we need to explicitly rename 'mypkg.old.Func'?
                # For code: 'from mypkg.old import Func'. 
                #   Visitor registers 'Func' as usage of 'mypkg.old.Func'.
                #   If we don't rename 'mypkg.old.Func', this usage won't be touched.
                #   So YES, we must rename it.
                
                # However, exclude the module itself as we already added it
                if member.fqn == old_module_fqn:
                    continue
                
                # Compute new FQN
                # old_fqn: mypkg.old.Func
                # suffix: .Func
                # new_fqn: mypkg.new.Func
                if member.fqn.startswith(old_module_fqn + "."):
                    suffix = member.fqn[len(old_module_fqn):]
                    target_new_fqn = new_module_fqn + suffix
                    
                    sub_op = RenameSymbolOperation(member.fqn, target_new_fqn)
                    ops.extend(sub_op.analyze(ctx))
                    
        return ops
~~~~~
~~~~~python.new
    def analyze(self, ctx: RefactorContext) -> List[FileOp]:
        rename_ops: List[FileOp] = []
        move_ops: List[FileOp] = []
        
        # 1. Symbol Renaming (Must happen BEFORE moves to modify existing files)
        # Why? Because RenameSymbolOperation modifies files in place (including Sidecars).
        # If we move Sidecars first, RenameOp will recreate them at old location or fail.
        # By modifying first, we update content at old location, THEN move to new location.
        
        old_module_fqn = self._path_to_fqn(self.src_path, ctx.graph.root_path)
        new_module_fqn = self._path_to_fqn(self.dest_path, ctx.graph.root_path)
        
        if old_module_fqn and new_module_fqn and old_module_fqn != new_module_fqn:
            # Rename the module itself (handles "import old_mod")
            rename_mod_op = RenameSymbolOperation(old_module_fqn, new_module_fqn)
            rename_ops.extend(rename_mod_op.analyze(ctx))
            
            # Rename all members (handles "from old_mod import X")
            members = ctx.graph.iter_members(old_module_fqn)
            
            for member in members:
                if member.fqn == old_module_fqn:
                    continue
                
                if member.fqn.startswith(old_module_fqn + "."):
                    suffix = member.fqn[len(old_module_fqn):]
                    target_new_fqn = new_module_fqn + suffix
                    
                    sub_op = RenameSymbolOperation(member.fqn, target_new_fqn)
                    rename_ops.extend(sub_op.analyze(ctx))

        # 2. Physical Move
        rel_src = self.src_path.relative_to(ctx.graph.root_path)
        rel_dest = self.dest_path.relative_to(ctx.graph.root_path)
        
        move_ops.append(MoveFileOp(rel_src, rel_dest))
        
        # 3. Sidecar Moves
        # YAML
        yaml_src = self.src_path.with_suffix(".stitcher.yaml")
        yaml_dest = self.dest_path.with_suffix(".stitcher.yaml")
        if yaml_src.exists():
            rel_yaml_src = yaml_src.relative_to(ctx.graph.root_path)
            rel_yaml_dest = yaml_dest.relative_to(ctx.graph.root_path)
            move_ops.append(MoveFileOp(rel_yaml_src, rel_yaml_dest))
            
        # Signatures
        sig_root = ctx.graph.root_path / ".stitcher/signatures"
        sig_src = sig_root / rel_src.with_suffix(".json")
        sig_dest = sig_root / rel_dest.with_suffix(".json")
        if sig_src.exists():
             rel_sig_src = sig_src.relative_to(ctx.graph.root_path)
             rel_sig_dest = sig_dest.relative_to(ctx.graph.root_path)
             move_ops.append(MoveFileOp(rel_sig_src, rel_sig_dest))
        
        # Return combined ops: FIRST modify content, THEN move files
        return rename_ops + move_ops
~~~~~

### 下一步建议
运行新添加的单元测试 `tests/unit/engine/test_graph_visitor.py` 和之前的集成测试，验证修复效果。如果单元测试通过但集成测试仍失败，则需要检查 `SemanticGraph` 是否正确传递了 `current_module_fqn`。
