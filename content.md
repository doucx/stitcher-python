这是一个里程碑式的时刻。我们成功地完成了 Stitcher 自项目启动以来最重要的一次架构演进。

通过将核心业务逻辑与 Python 语言实现彻底解耦，我们将 Stitcher 从一个特定的 Python 工具提升为了一个通用的、协议驱动的文档引擎框架。这不仅解决了技术债务和测试困难的问题，更为未来的多语言支持和更复杂的交互协议铺平了道路。

## [COMMIT] refactor: 彻底解耦业务逻辑与 Python 实现，建立协议驱动的架构

### 用户需求
执行提案 `01KDJ9PXS0PJQQZ32JZDQHW9CW`：将 Stitcher 的通用业务逻辑（状态管理、工作流编排）与 Python 语言的具体实现（AST 解析、存根生成）解耦，建立一套基于协议的可插拔语言核心架构。

### 评论
这次重构不仅是代码位置的搬迁，更是软件设计思想的深刻转变。通过引入协议和依赖注入，我们实现了高层业务逻辑与底层技术细节的完全隔离。现在的 `StitcherApp` 已经成为了一个纯粹的“指挥官”，它通过抽象接口调度各种“士兵”（适配器），这种灵活性在处理大型、复杂项目时将展现出巨大的威力。

### 目标
1.  **定义核心抽象**: 在 `stitcher-spec` 中建立了一套完整的语言核心协议（Parsing, Transformation, Hashing, Generation）。
2.  **构建语言适配器**: 创建了 `stitcher-python-adapter` 包，作为 Python 逻辑的唯一归口，实现了高度可扩展的组合式指纹策略。
3.  **实现依赖注入**: 全面改造 `StitcherApp` 及其服务层，通过构造函数注入协议实例，消除了对具体实现包的硬编码引用。
4.  **优化资源布局**: 将通用的 IO 适配器（YAML/Document）迁移至 `stitcher-common`，并清理了 IR 模型中不再属于模型职责的遗留方法。
5.  **质量保证**: 删除了废弃的 `stitcher-scanner` 和 `stitcher-io` 包，修复了重构过程中的所有回归，并为新适配器补充了关键的单元测试。

### 基本原理
本次重构严格遵循了 **依赖倒置原则 (DIP)** 和 **关注点分离 (SoC)**。
- **策略模式**: `FingerprintStrategy` 采用组合模式，使得我们可以像拼积木一样组合不同的哈希算法（结构哈希、文本哈希、未来可能的 AST 哈希），而无需修改接口。
- **组合根模式**: CLI 层现在作为唯一的“组合根”，负责根据环境实例化具体的适配器并组装出完整的 `StitcherApp`，保证了核心代码的纯净和可测试性。

### 标签
#intent/refine #flow/ready #priority/high 
#comp/engine #comp/runtime #comp/cli #comp/interfaces #comp/docs #comp/tests #comp/build
#concept/parser #concept/executor #scope/core #scope/api #scope/dx
#ai/delegate
#task/domain/architecture #task/object/language-core #task/action/refactor #task/state/end #task/status/completed

---

### Script

#### Acts 1: 暂存变更并提交重构成果

我们将所有涉及架构解耦、协议定义、适配器实现、依赖注入改造以及后续清理和修复的变更打包提交。

~~~~~act
git_add
packages/stitcher-spec/src/stitcher/spec/protocols.py
packages/stitcher-spec/src/stitcher/spec/protocols.stitcher.yaml
packages/stitcher-spec/src/stitcher/spec/__init__.py
packages/stitcher-spec/src/stitcher/spec/models.py
packages/stitcher-spec/src/stitcher/spec/fingerprint.py
packages/stitcher-common/src/stitcher/common/interfaces.py
packages/stitcher-common/src/stitcher/common/adapters/yaml_adapter.py
packages/stitcher-common/src/stitcher/common/__init__.py
packages/stitcher-python-adapter
packages/stitcher-application/src/stitcher/app/core.py
packages/stitcher-application/src/stitcher/app/services/signature_manager.py
packages/stitcher-application/src/stitcher/app/services/doc_manager.py
packages/stitcher-application/pyproject.toml
packages/stitcher-application/tests/unit/test_signature_extraction.py
packages/stitcher-application/tests/unit/test_signature_manager.py
packages/stitcher-application/tests/unit/test_doc_manager.py
packages/stitcher-application/tests/unit/test_doc_overlay.py
packages/stitcher-cli/src/stitcher/cli/factories.py
packages/stitcher-cli/pyproject.toml
packages/stitcher-test-utils/src/stitcher/test_utils/helpers.py
packages/stitcher-test-utils/src/stitcher/test_utils/helpers.stitcher.yaml
packages/stitcher-test-utils/src/stitcher/test_utils/__init__.py
packages/stitcher-test-utils/pyproject.toml
pyproject.toml
tests
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor: decouple business logic from Python implementation

Implemented the strategic architectural refactoring to separate language-agnostic 
business logic from Python-specific implementations.

Key Changes:
- Introduced LanguageParser, LanguageTransformer, FingerprintStrategy, and 
  StubGenerator protocols in `stitcher-spec`.
- Created `stitcher-python-adapter` as the standard implementation of these 
  protocols for Python.
- Refactored `StitcherApp` and its services to use Dependency Injection via 
  protocols, enabling true isolation and testability.
- Implemented a composite `FingerprintStrategy` that allows plugging in 
  multiple hashing algorithms (Structure, Signature Text, etc.).
- Relocated shared IO adapters (YAML/Document) to `stitcher-common`.
- Removed deprecated `stitcher-scanner` and `stitcher-io` packages.
- Fixed regressions in IR models and updated the test suite to use a new 
  `create_test_app` factory.
- Added comprehensive unit tests for the Python adapter components.

This establishes a clean, extensible, and professional foundation for the 
Stitcher project's future growth.
~~~~~

### 下一步建议
- **业务逻辑深度测试**: 利用当前可 Mock 适配器的优势，针对 `StitcherApp` 复杂的冲突解决逻辑编写纯单元测试。
- **多目标语言预研**: 尝试定义一个简单的伪语言适配器，验证架构在处理非 Python 语言时的适应性。
