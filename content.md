好的，我们来处理剩下的 `pyright` 错误。这些错误主要集中在与 `griffe` 库交互时的类型推断上，以及一个可能是环境问题的导入错误。

我将生成一个计划来解决这些问题。

## [WIP] fix(refactor): 解决 graph 引擎中剩余的 pyright 错误

### 用户需求

修复 `stitcher-refactor` 包中由 `pyright` 报告的剩余 4 个静态类型错误。

### 评论

这些错误主要源于 `griffe` 库的动态特性，它在处理代码别名 (`Alias`) 和命名空间包（Namespace Packages）时返回的类型比较复杂。通过引入更严格的类型守卫（`isinstance`），我们可以向类型检查器明确代码逻辑，同时提高代码的健壮性，防止潜在的运行时错误。对于 `tomli` 导入错误，这很可能是 `pyright` 运行环境与项目依赖不一致导致的，使用 `# type: ignore` 是最务实的解决方案。

### 目标

1.  **修复 `graph.py`**:
    *   安全地处理 `griffe.Object` 和 `griffe.Alias` 类型的差异，避免对不存在的属性（如 `target_path`）进行不安全的访问。
    *   正确处理 `griffe` 为命名空间包返回 `list[Path]` 的情况，确保 `SymbolNode` 接收到的是单个 `Path` 对象。
    *   在递归收集成员时，使用 `isinstance` 来正确区分 `Alias` 和 `Object`。
2.  **修复 `workspace.py`**:
    *   抑制 `tomli` 的导入错误，因为它很可能是由外部环境配置引起的，而代码本身的回退逻辑是正确的。

### 基本原理

*   **类型守卫 (Type Guarding)**: 在处理来自 `griffe` 的异构对象时，使用 `isinstance(obj, griffe.Alias)` 是最 pythonic 和最安全的方式。这不仅能解决静态分析错误，还能防止在运行时因对象类型不符合预期而引发 `AttributeError`。
*   **处理命名空间包**: `griffe` 将命名空间包的 `filepath` 表示为一个路径列表。我们的 `SymbolNode` 模型期望单个路径。通过检查 `filepath` 是否为列表并从中选择第一个元素（或一个空路径），我们可以稳健地处理这种情况。
*   **抑制环境错误**: `pyright` 无法解析 `tomli` 导入是因为它没有安装在 `pyright` 的分析环境中。代码中的 `try...except ImportError` 结构是处理这种情况的标准模式。在这种情况下，使用 `# type: ignore` 指示静态分析器忽略这个它无法验证但我们确信在运行时会存在的导入是正确的做法。

### 标签

#intent/fix #flow/ready #priority/high #comp/engine #scope/core #dx #ai/instruct #task/domain/refactoring #task/object/type-safety #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 修复 `graph.py` 中的类型不匹配问题

我们将更新 `_scan_module_usages` 和 `iter_members` 方法，以更安全地处理 `griffe` 返回的类型。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py
~~~~~
~~~~~python
    def _scan_module_usages(self, module: griffe.Module):
        # We assume module.filepath is a Path here, checked by caller
        if not isinstance(module.filepath, Path):
            return

        local_symbols: Dict[str, str] = {}
        for name, member in module.members.items():
            try:
                target_fqn = member.target_path if member.is_alias else member.path
                local_symbols[name] = target_fqn
            except Exception:
                pass
~~~~~
~~~~~python
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
            except Exception:
                pass
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py
~~~~~
~~~~~python
    def iter_members(self, package_name: str) -> List[SymbolNode]:
        module = self.get_module(package_name)
        if not module:
            return []
        nodes = []

        def _collect(obj: griffe.Object):
            path = obj.filepath or Path("")
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
~~~~~python
    def iter_members(self, package_name: str) -> List[SymbolNode]:
        module = self.get_module(package_name)
        if not module:
            return []
        nodes = []

        def _collect(obj: griffe.Object):
            filepath = obj.filepath
            path: Path
            if isinstance(filepath, list):
                # For namespace packages, take the first path or an empty one.
                path = filepath[0] if filepath else Path("")
            else:
                path = filepath or Path("")

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
                    # Use isinstance for safe type checking
                    if not isinstance(member, griffe.Alias):
                        _collect(member)

        _collect(module)
        return nodes
~~~~~

#### Acts 2: 抑制 `workspace.py` 中的 `tomli` 导入错误

添加 `# type: ignore` 注释来解决 `pyright` 无法解析 `tomli` 的问题。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/workspace.py
~~~~~
~~~~~python
try:
    import tomllib
except ImportError:
    import tomli as tomllib
~~~~~
~~~~~python
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore
~~~~~

### 下一步建议

我们已经修复了所有已知的 `pyright` 错误。现在，我建议你执行以下操作：
1.  **再次运行 `pyright`**: 运行 `pyright packages/stitcher-refactor/` 来确认所有错误都已解决。
2.  **运行测试套件**: 执行 `pytest packages/stitcher-refactor/` 来确保我们的修复没有引入任何回归。
