好的，我们已经完成了适配器层的开发并理顺了测试结构。现在是时候将这些工作作为一个完整的逻辑单元进行提交了。

我将生成一个 `[COMMIT]` 计划，包含所有新增文件和重构后的测试。

## [COMMIT] feat(adapter): 实现结构化文档解析器与渲染器 (Phase 1)

### 用户需求

提交阶段 1 的所有工作，包括 Griffe 解析器、结构化渲染器、Codec 工厂以及符合 Monorepo 规范的单元测试。

### 评论

阶段 1 的完成为 Stitcher 引入了理解和生成 Google/Numpy 风格文档的能力。通过 Codec 模式，我们将这种复杂的文档风格处理逻辑封装在适配器层，为后续在应用层实现自动格式化和插件系统打下了坚实的架构基础。

### 目标

1.  将所有新增和修改的文件添加到 Git 暂存区。
2.  执行 Git 提交，记录阶段 1 的核心成果。

### 基本原理

遵循 `d3-constraint-quipu-plan-script-rules`，我们在独立的 `[COMMIT]` 计划中执行提交操作。提交消息将详细说明本次变更的架构意义。

### 标签

#intent/build #flow/ready #priority/high 
#comp/adapter #comp/tests #concept/parser #concept/renderer #scope/core
#ai/instruct
#task/domain/docstring #task/object/adapter #task/action/implementation
#task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交适配器层变更

我们将所有相关变更添加到暂存区。注意包含新增的 `parsers.py`, `renderers.py`, `factory.py` 以及移动后的测试文件。

~~~~~act
git_add
packages/stitcher-python-adapter/src/stitcher/adapter/python/docstring/parsers.py
packages/stitcher-python-adapter/src/stitcher/adapter/python/docstring/renderers.py
packages/stitcher-python-adapter/src/stitcher/adapter/python/docstring/factory.py
packages/stitcher-python-adapter/src/stitcher/adapter/python/docstring/__init__.py
packages/stitcher-python-adapter/src/stitcher/adapter/python/__init__.py
packages/stitcher-python-adapter/tests/unit/docstring/test_parsers.py
packages/stitcher-python-adapter/tests/unit/docstring/test_renderers.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
feat(adapter): implement structured docstring parsers and renderers

This commit completes Phase 1 of the Structured Docstring Roadmap.

- Introduced the Codec pattern for docstring handling.
- Implemented 'GriffeDocstringParser' to parse Google and Numpy style docstrings into 'DocstringIR'.
- Implemented 'GoogleDocstringRenderer' and 'NumpyDocstringRenderer' for high-fidelity docstring generation.
- Added 'get_docstring_codec' factory to decouple style configuration from implementation.
- Refactored IR mapping to correctly handle Return/Yield types and standard titles.
- Established a dedicated unit testing suite for docstrings under the package-local 'tests/unit' directory.

This infrastructure allows the 'DocumentManager' to process structured documentation instead of raw strings, enabling cross-style formatting and plugin support in upcoming phases.
~~~~~

### 下一步建议

阶段 1 正式结束。接下来我们将开始 **阶段 2: 存储层升级 (The Storage Layer)**。

核心任务是重构 `DocumentManager`：
1.  **序列化升级**: 使其能够将 `DocstringIR` 中的结构化字段（如 `Summary`, `Args`, `Returns`）映射为 YAML 的键值对，实现 Fully Structured 存储。
2.  **哈希一致性**: 升级 `compute_yaml_content_hash`，确保它是基于“规范化后的 IR”计算，从而彻底解决格式微调导致的哈希漂移问题。

如果您准备好了，请告知我，我将为您生成阶段 2 的第一个实施计划。
