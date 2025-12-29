简要回答
好的，既然 Griffe 解析器的所有功能（包括结构解析、导入提取和自动补充缺失 `typing` 符号）都已实现并经过测试，并且混合解析器架构也已配置。现在是时候将这些工作作为一个完整的特性提交到代码库中。

我将生成一个 `[COMMIT]` 计划，其中包含所有受影响文件的 `git add` 和一个详细的 `git commit` 消息。

## [COMMIT] feat(adapter): 全面集成 Griffe 作为混合模式 Python 解析器

### 用户需求
1.  在 `stitcher` 项目中全面集成 Griffe，利用其强大的静态分析能力。
2.  实现一个混合解析器策略，根据 CLI 命令（分析型 vs. 转换型）动态选择 Griffe 或 LibCST。
3.  确保 Griffe 解析器能够正确处理函数、类、属性的解析。
4.  确保 Griffe 解析器能从源代码中提取 `import` 语句，并自动补充 `typing` 模块的缺失导入。
5.  解决 Griffe 在处理相对导入和外部 Alias 时可能发生的崩溃及解析错误。
6.  解决生成的 `.pyi` 文件中类属性赋值导致的语法错误。

### 评论
本次集成是一项重大的架构改进，显著提升了 `stitcher` 的代码理解能力，特别是对于类型注解和复杂的 Python 语法。混合模式的设计确保了我们能够根据具体任务（静态分析或无损代码转换）选择最合适的工具，平衡了性能、准确性与代码格式保真度。虽然 Griffe 作为 `generate` 和 `check` 命令的解析器，但其在 `ModuleDef.imports` 自动补全能力目前仅限于 `typing` 模块，对于项目内部的跨模块类型引用仍有提升空间，但已经足以满足当前的核心需求。

### 目标
1.  将 Griffe 集成作为 `stitcher-python-adapter` 模块的核心组件。
2.  通过 `stitcher-cli` 工厂机制，实现 `generate` 和 `check` 命令使用 Griffe，而 `init`, `pump`, `strip`, `inject` 仍使用 LibCST。
3.  通过新的集成测试和现有单元测试的通过，验证 Griffe 解析器的正确行为和稳定性。
4.  将所有相关代码变更写入一个逻辑且完整的 Git 提交。

### 基本原理
我们遵循了依赖倒置原则，在 `stitcher-cli` 的 Composition Root 处，通过修改 `make_app` 工厂函数，实现了 `LanguageParserProtocol` 的具体实现（GriffePythonParser 或 PythonParser）的选择。这使得 `StitcherApp` 核心逻辑无需改变，同时能够根据上层命令的意图，动态切换底层解析引擎，从而最大化两种解析器的优势。

### 标签
#intent/build #flow/ready #priority/high
#comp/runtime #comp/cli #comp/test
#concept/parser #concept/codegen #concept/state #concept/architecture
#scope/core #scope/api #scope/dx
#ai/instruct
#task/domain/engine #task/object/griffe-parser #task/action/integration #task/state/end

---

### Script

#### Acts 1: 添加所有更改到 Git 暂存区

我们将暂存所有在 Griffe 集成过程中修改或新增的文件，包括源代码、测试文件和 `factories.py`。

~~~~~act
git_add
packages/stitcher-python-adapter/tests/integration/test_griffe_resolution.py
packages/stitcher-python-adapter/src/stitcher/adapter/python/griffe_parser.py
packages/stitcher-python-adapter/tests/unit/test_griffe_parser.py
packages/stitcher-python-adapter/src/stitcher/adapter/python/internal/stub_generator.py
packages/stitcher-python-adapter/tests/unit/test_stub_generator.py
packages/stitcher-cli/src/stitcher/cli/factories.py
packages/stitcher-cli/src/stitcher/cli/commands/basics.py
packages/stitcher-cli/src/stitcher/cli/commands/check.py
packages/stitcher-cli/src/stitcher/cli/commands/pump.py
~~~~~

#### Acts 2: 执行 Git 提交

创建一个清晰且详细的提交信息，总结本次 Griffe 集成的所有关键点。

~~~~~act
git_commit
~~~~~
~~~~~text
feat(adapter): Integrate Griffe with hybrid parser strategy

This commit fully integrates Griffe as a primary Python parsing backend, enabling a hybrid parser strategy within Stitcher. This significantly enhances static analysis capabilities for `generate` and `check` commands, while preserving the fidelity of source code transformations for `pump`, `strip`, and `inject` commands through LibCST.

**Key Changes & Improvements:**

1.  **Hybrid Parser Strategy:** Implemented a new mechanism in `stitcher-cli`'s `make_app` factory to dynamically select between `GriffePythonParser` (for analysis-heavy tasks like `generate` and `check`) and `PythonParser` (LibCST-based, for transformation tasks like `pump`, `strip`, `inject`).
2.  **GriffePythonParser Implementation:**
    *   **Full Structural Parsing:** Extended to correctly parse function, class, and module-level attributes, including their docstrings, annotations, and values.
    *   **Robust Import Handling:**
        *   Resolved `BuiltinModuleError` by providing `filepath` to `griffe.visit` for accurate relative import resolution.
        *   Mitigated `AliasResolutionError` during module member iteration by safely skipping `member.is_alias` entries, focusing solely on definitions within the current module.
        *   **Automatic `typing` Import Enrichment:** Ported the `_enrich_typing_imports` logic to automatically add `from typing import ...` statements to the `ModuleDef.imports` list based on annotations found, ensuring generated `.pyi` files are type-checker compliant.
3.  **Stub Generator Fix:** Modified `StubGenerator._generate_attribute` to suppress default values for class-level attributes in `.pyi` files (e.g., `_run_id: Any = run_id`) to prevent runtime `NameError` due to incorrect scope inference. Module-level attributes retain their values.
4.  **Comprehensive Testing:** Added new integration and unit tests (e.g., `test_griffe_resolution.py`, `test_griffe_parser.py` enhancements) to validate Griffe's parsing capabilities, import resolution, and stub generation correctness.

This integration leverages Griffe's advanced semantic understanding for critical analysis tasks, positioning Stitcher for better type stub generation and more precise code health checks, while maintaining the non-destructive nature of code transformation commands.
~~~~~
