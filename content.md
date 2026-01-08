好的，我们已经成功完成了 Phase 2 的核心逻辑重构和导入问题的修复。这标志着系统现在已经具备了处理多种文档风格的底层基础设施。

我将生成一个 `[COMMIT]` 计划，将这些更改作为一个完整的工作单元提交。

## [COMMIT] feat: 核心解耦与配置驱动的文档处理集成

### 用户需求
提交 Phase 2 的实施成果：完成 `DocumentManager` 与具体解析/序列化策略的解耦，并在 `StitcherApp` 中集成配置驱动的策略注入。

### 评论
这是结构化文档支持路线图中的一个里程碑。我们不仅实现了功能，还修复了一个关键的 API 导出问题，提升了整个项目的架构健壮性和开发者体验 (DX)。

### 目标
1.  将所有修改后的文件添加到 Git 暂存区。
2.  创建一个包含详细变更说明的 Git 提交。

### 基本原理
遵循 `[COMMIT]` 计划规范，将逻辑相关的变更合并为一个原子提交，确保版本历史的清晰。

### 标签
#intent/build #flow/ready #priority/high 
#comp/runtime #comp/core #concept/config #scope/api
#task/domain/storage #task/object/doc-manager #task/action/integration
#task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更

我们将把涉及到的应用层和服务层代码，以及适配器层的 API 更新一并提交。

~~~~~act
git_add
packages/stitcher-application/src/stitcher/app/core.py
packages/stitcher-application/src/stitcher/app/services/doc_manager.py
packages/stitcher-application/src/stitcher/app/services/doc_manager.stitcher.yaml
packages/stitcher-python-adapter/src/stitcher/adapter/python/__init__.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
feat(app): decouple DocumentManager and integrate config-driven docstring strategy

This completes Phase 2 of the 'Full Formatting' roadmap.

1.  Decoupled `DocumentManager` from hardcoded `RawDocstringParser`. It now supports dynamic injection of `DocstringParserProtocol` and `DocstringSerializerProtocol` via a new `set_strategy` method.
2.  Refactored `DocumentManager` serialization/deserialization logic to delegate to the injected serializer, enabling support for Google and NumPy style YAML structures.
3.  Integrated the strategy injection into `StitcherApp`. During configuration, the app now uses the `get_docstring_codec` and `get_docstring_serializer` factories from the adapter to configure the `DocumentManager` based on the `docstring_style` setting.
4.  Fixed an `ImportError` by exporting all docstring-related components (parsers, renderers, serializers, and factories) in the top-level `stitcher.adapter.python` package.
~~~~~

### 下一步建议

Phase 2 已正式完成。接下来我们应该转向：
*   **阶段 3: 渲染管线集成**: 这是最具挑战性的部分。我们需要修改 `StubGenerator`，使其不再只是搬运字符串，而是能够将 YAML 中的结构化描述与代码中的类型信息在渲染时进行“缝合”。
*   **增加测试**: 在开始 Phase 3 之前，我建议先编写几个针对 `DocumentManager` 策略切换的单元测试，确保序列化逻辑在不同风格下都能如期工作。
