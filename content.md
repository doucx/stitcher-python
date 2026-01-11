好的，我们已经完成了代码修改并验证了测试。现在，我将生成一个 `[COMMIT]` 计划，将这些针对基准存档与 SURI 对齐的改进正式提交。

## [COMMIT] refactor(application): 将签名存档标识符对齐为 SURI

### 用户需求
根据阶段 2 的实施计划，将 `.stitcher/signatures/*.json` 中的基准数据标识符从局部的 FQN 片段升级为全局唯一的 SURI，并扩展对新增基准哈希字段的支持。

### 评论
通过此次重构，我们成功地将基准存档（Baseline）与索引现状（Current State）在标识符层面上进行了统一。这不仅消除了跨文件符号识别的歧义，还为下一步实现完全不依赖源码读取的 `check` 逻辑奠定了坚实的数据基础。

### 目标
1.  将 `SignatureManager` 的 JSON 存储格式切换为 SURI Key。
2.  确保 `Fingerprint` 能够正确加载和存储新增的 `signature_text` 和 `docstring_hash` 基准字段。
3.  同步更新测试基础设施 (`get_stored_hashes`) 以维持开发体验。

### 基本原理
我们利用 `SURIGenerator` 作为权威的身份编码器，在写入 JSON 时将文件路径与 FQN 缝合为 SURI，在读取时将其解构回 FQN 片段。这种“全局键，局部值”的模式既保证了存储层面的绝对唯一性，又保持了应用层逻辑的兼容性。

### 标签
#intent/refine #flow/ready #priority/high #comp/application #comp/engine #comp/tests #concept/state #scope/core #ai/instruct #task/domain/storage #task/object/signature-archive #task/action/alignment #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更

我们将把涉及 `stitcher-index`, `stitcher-python-adapter`, `stitcher-application` 以及 `stitcher-test-utils` 的所有改动一并提交，因为它们构成了一个完整的架构升级单元。

~~~~~act
git_add
packages/stitcher-index/src/stitcher/index/schema.sql
packages/stitcher-index/src/stitcher/index/types.py
packages/stitcher-index/src/stitcher/index/store.py
packages/stitcher-python-adapter/src/stitcher/adapter/python/fingerprint.py
packages/stitcher-python-adapter/src/stitcher/adapter/python/index_adapter.py
packages/stitcher-application/src/stitcher/app/services/signature_manager.py
packages/stitcher-application/tests/unit/test_signature_manager.py
packages/stitcher-test-utils/src/stitcher/test_utils/helpers.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor: align signature storage with SURI identifiers

This commit implements Phase 1 and Phase 2 of the Stitcher 2.0 roadmap, focusing on semantic infrastructure and baseline identifier alignment.

Core Changes:
1.  Stitcher Index Schema Upgrade: Added 'signature_text' and 'docstring_hash' fields to the 'symbols' table in index.db to allow query-first logic.
2.  PythonAdapter Enhancement: Implemented 'DocstringHasher' and updated the extraction pipeline to populate the new semantic fields during indexing.
3.  SURI Identifier Alignment: Refactored 'SignatureManager' to use SURI (Stitcher Uniform Resource Identifier) as the unique key in JSON baseline files (e.g., 'py://src/app.py#func').
4.  Fingerprint Expansion: Enabled storage of signature text and docstring hashes in baseline fingerprints.
5.  Test Infrastructure Update: Synchronized 'get_stored_hashes' helper in test-utils to support SURI resolution, ensuring test suite stability.

These changes decouple the 'Actual' and 'Baseline' states from raw source code reading, enabling the upcoming 'Query-First' refactoring of the Check and Pump runners.
~~~~~

### 下一步建议

阶段 2 已圆满结束。现在系统的“地基”已经完全对齐。下一步，我们将进入 **阶段 3：逻辑驱动重构 (Query-First Runners)**。

我建议首先重构 `CheckRunner`。目标是让它在执行 `analyze_batch` 时，不再对每一个文件调用 `self.parser.parse()`，而是直接通过 `index_store` 查询数据库，将得到的 `Actual` 结果与 `SignatureManager` 加载的 `Baseline` 结果在内存中进行比对。这将使 `check` 操作变得极快。

如果你准备好了，请指示我开始重构 `CheckRunner`。
