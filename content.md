You've uncovered a couple of excellent, subtle bugs. The test failures point to two distinct issues which I will address.

1.  **Behavioral Bug (`no_ops` issue):** The two integration tests are failing because the refactor engine incorrectly plans zero operations (`no_ops`). This is due to a flaw in how the `SemanticGraph` is built. It's trying to analyze usages *during* the loading of each package, *before* all cross-module aliases have been resolved. The fix is to separate the loading phase from the analysis phase.
2.  **Test Drift (`AttributeError`):** The unit test is failing because it wasn't updated after my last change where I renamed `src_path` to `src`. I will fix this test.

I will now generate a plan to fix both of these issues.

## [WIP] fix(refactor): Decouple semantic analysis from module loading

### 错误分析

测试套件中出现了三处失败，指向两个不同的根本原因：

1.  **`test_refactor_apply_e2e` 和 `test_refactor_apply_dry_run` 失败**:
    *   **现象**: `SpyBus` 捕获到的最后一条消息是 `refactor.run.no_ops`，表明 `Planner` 未生成任何文件操作。
    *   **根本原因**: `SemanticGraph` 的设计存在时序问题。它在 `load()` 方法中加载一个包后，立即对其进行语法分析以查找符号用法 (`_build_registry`)。然而，Griffe 的跨模块别名解析 (`resolve_aliases()`) 需要在**所有**相关的包都被加载后才能正确工作。因此，当分析第一个包时，它无法解析引用了第二个包中符号的别名，导致符号用法（usages）的注册不完整。最终，`RenameSymbolOperation` 找不到任何用法，也就不会生成任何操作。

2.  **`test_migration_spec_add_operations` 失败**:
    *   **现象**: `AttributeError: 'MoveFileOperation' object has no attribute 'src_path'`.
    *   **根本原因**: 这是由我上一次修复引入的“测试漂移”。我为了统一 API 将 `MoveFileOperation` 的 `__init__` 参数从 `src_path` 改为了 `src`，但忘记更新引用了旧属性名的单元测试。

### 用户需求

修复重构引擎，使其能够：
1.  正确识别并解析跨包的符号引用。
2.  通过完整的测试套件验证。

### 评论

这是一个非常关键的修复。将模块加载（I/O和初始解析）与全域分析（别名解析和用法扫描）解耦，是构建健壮的、能理解整个代码库的重构引擎的正确架构。这个修复将使引擎从只能理解单个文件，进化到能理解整个项目。

### 目标

1.  **重构 `SemanticGraph`**:
    *   修改 `load()` 方法，使其只负责加载模块到 Griffe 加载器中。
    *   创建一个新的 `build()` 方法，该方法在所有模块加载完毕后被调用。它将首先调用 `resolve_aliases()`，然后遍历所有已加载的模块来构建完整的用法注册表。
2.  **更新 `refactor_command`**: 在加载完所有顶层包后，调用新的 `graph.build()` 方法。
3.  **修复单元测试**: 更新 `test_spec.py` 以使用正确的属性名 `.src`。

### 基本原理

我们将遵循“分阶段”处理的原则。首先，`refactor_command` 将负责“加载阶段”，它会告诉 `SemanticGraph` 去加载所有发现的顶层包。`SemanticGraph` 在此阶段只收集模块。然后，`refactor_command` 会显式触发“构建阶段”，调用 `graph.build()`。`build()` 方法现在拥有了代码库的“全景图”，可以安全地解析所有别名，并准确地扫描所有符号的用法。这个改动确保了分析的正确性，从而解决了 `no_ops` 的问题。

### 标签

#intent/fix #flow/ready #priority/critical #comp/refactor #concept/state #scope/core #ai/brainstorm #task/domain/tooling #task/object/refactor-engine #task/action/dogfooding #task/state/continue

---

### Script

#### Acts 1: Refactor `SemanticGraph` to separate loading and analysis

我们将修改 `graph.py`，引入新的 `build()` 方法。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py
~~~~~
~~~~~python.old
    def load(self, package_name: str, submodules: bool = True) -> None:
        # 1. Load with Griffe (resolves aliases)
        module = self._griffe_loader.load(package_name, submodules=submodules)
        self._modules[package_name] = module

        # 2. Resolve aliases to ensure we have full resolution
        self._griffe_loader.resolve_aliases()

        # 3. Build Usage Registry
        self._build_registry(module)
~~~~~
~~~~~python.new
    def load(self, package_name: str, submodules: bool = True) -> None:
        # Phase 1: Just load the module. Analysis happens in `build`.
        module = self._griffe_loader.load(package_name, submodules=submodules)
        self._modules[package_name] = module

    def build(self) -> None:
        # Phase 2: Once all modules are loaded, resolve aliases globally.
        self._griffe_loader.resolve_aliases()

        # Phase 3: Now that resolution is complete, scan for usages.
        for module in self._modules.values():
            self._build_registry(module)
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py
~~~~~
~~~~~python.old
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
            visitor = _UsageVisitor(module.filepath, local_symbols, self.registry)
            wrapper.visit(visitor)
        except Exception:
            # Handle syntax errors or IO errors gracefully
            pass
~~~~~
~~~~~python.new
    def _scan_module_usages(self, module: griffe.Module):
        if not module.filepath or not module.filepath.exists():
            return

        # 1. Build Local Symbol Table (Name -> FQN)
        local_symbols: Dict[str, str] = {}

        # First, add definitions within this module
        for name, member in module.members.items():
            if not member.is_alias:
                local_symbols[name] = member.path

        # Second, add resolved aliases (imports)
        for name, member in module.aliases.items():
            try:
                # After resolve_aliases(), target_path should be correct
                target_fqn = member.target_path
                local_symbols[name] = target_fqn
            except Exception:
                # Alias resolution might fail for various reasons, skip it
                pass

        # 2. Parse CST and scan
        try:
            source = module.filepath.read_text(encoding="utf-8")
            # Determine module FQN for relative import resolution
            is_init = module.filepath.name == "__init__.py"
            module_fqn = module.path

            wrapper = cst.MetadataWrapper(cst.parse_module(source))
            visitor = _UsageVisitor(
                module.filepath, local_symbols, self.registry, module_fqn, is_init
            )
            wrapper.visit(visitor)
        except Exception:
            # Handle syntax errors or IO errors gracefully
            pass
~~~~~


#### Acts 2: Update CLI to call the new `build` method

现在我们修改 `refactor.py` 来适应 `SemanticGraph` 的新工作流程。

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/commands/refactor.py
~~~~~
~~~~~python.old
        for pkg_name in sorted(list(top_level_imports)):
            bus.debug(L.debug.log.msg, msg=f"Loading top-level package: {pkg_name}")
            graph.load(pkg_name)

        ctx = RefactorContext(graph)
~~~~~
~~~~~python.new
        for pkg_name in sorted(list(top_level_imports)):
            bus.debug(L.debug.log.msg, msg=f"Loading top-level package: {pkg_name}")
            graph.load(pkg_name)

        # After loading all packages, build the unified semantic view
        graph.build()

        ctx = RefactorContext(graph)
~~~~~

#### Acts 3: Fix the unit test drift

最后，修正 `test_spec.py` 中的断言。

~~~~~act
patch_file
packages/stitcher-refactor/tests/unit/migration/test_spec.py
~~~~~
~~~~~python.old
    assert isinstance(spec.operations[1], MoveFileOperation)
    assert spec.operations[1].src_path == Path("src/old.py")
~~~~~
~~~~~python.new
    assert isinstance(spec.operations[1], MoveFileOperation)
    assert spec.operations[1].src == Path("src/old.py")
~~~~~

### 下一步建议

这些修复应该已经解决了所有测试失败的问题。我建议你重新运行整个测试套件。一旦测试通过，你就可以再次运行你的迁移脚本，它现在应该能够正确识别所有符号用法并成功重构代码了。

```bash
# First, verify the fix by running the tests
pytest packages/stitcher-refactor/tests/unit/migration/test_spec.py
pytest packages/stitcher-cli/tests/integration/test_refactor_command.py

# Then, apply your migration
stitcher refactor apply migrations/001_refactor_cli_l_pointers.py
```
