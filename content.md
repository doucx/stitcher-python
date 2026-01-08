Phase 2 基础设施实现完毕。现在我们将这些变更提交到 Git。

## [COMMIT] feat(spec/adapter): implement style-aware docstring serializers

### 用户需求
实施存储层升级（Phase 2），通过引入风格感知的序列化器，使 YAML 存储结构能够根据配置（Google/NumPy）自动切换关键字和结构，从而提供更符合直觉的文档编辑体验。

### 评论
此次提交为文档处理管线引入了关键的解耦层。通过 Serializer 策略，我们成功地将内部统一的 `DocstringIR` 与面向用户的 YAML 展示层分离开来。这不仅提升了 DX（开发者体验），还确保了插件数据（Addons）在任何风格下都能被无损保留。

### 目标
1.  提交 `stitcher-spec` 中关于段落类型（`SectionKind`）和序列化协议的变更。
2.  提交 `stitcher-python-adapter` 中新增的 Google、NumPy 和 Raw 序列化器实现。
3.  提交工厂函数的更新，为应用层的集成做好准备。

### 基本原理
我们确立了“YAML 即 UI”的原则。序列化器层负责将 IR 转换为风格化的字典：
-   **语义映射**: 将内部段落类型映射为风格特定的关键字（如 `Args` 或 `Parameters`）。
-   **无损转换**: 采用 `(type) description` 模式编码参数信息，确保在不破坏 YAML 可读性的前提下保留类型元数据。
-   **插件共存**: 强制性的 Addon 透传机制保证了生态系统的扩展性。

### 标签
#intent/build #flow/ready #priority/high #comp/spec #comp/adapter #concept/docstring #task/domain/storage #task/object/docstring-serializer #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 提交 Phase 2 基础设施变更

我们将所有涉及协议定义和序列化器实现的文件添加到暂存区并提交。

~~~~~act
git_add
packages/stitcher-spec/src/stitcher/spec/docstring.py
packages/stitcher-spec/src/stitcher/spec/protocols.py
packages/stitcher-spec/src/stitcher/spec/__init__.py
packages/stitcher-python-adapter/src/stitcher/adapter/python/docstring/serializers.py
packages/stitcher-python-adapter/src/stitcher/adapter/python/docstring/factory.py
packages/stitcher-python-adapter/src/stitcher/adapter/python/docstring/__init__.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
feat(spec/adapter): implement style-aware docstring serializers

Introduces a polymorphic serialization layer to support Google and NumPy 
styled YAML storage, aligning with the "YAML as UI" philosophy.

Key changes:
- Added `SectionKind` enum and `DocstringSerializerProtocol` to the spec.
- Implemented `GoogleSerializer` and `NumpySerializer` in the Python adapter.
- Implemented a standard encoding strategy for items: `(type) description`.
- Ensured absolute preservation of `Addon.*` keys across all serializers.
- Updated factories to provide style-specific serializers.

This enables the system to present YAML structures that feel natural to 
developers depending on their configured docstring style (e.g., using 'Args' 
vs 'Parameters'), significantly improving DX for manual documentation edits.
~~~~~

### 下一步建议
-   **集成测试**: 编写针对 `serializers.py` 的单元测试，验证 Google 和 NumPy 风格在复杂场景下的互转行为。
-   **应用层集成**: 重构 `stitcher-application` 中的 `DocumentManager`，使其正式采用新的序列化基础设施，取代原有的硬编码逻辑。
-   **配置校验**: 确保 `pyproject.toml` 中的 `docstring_style` 配置能够正确传导至 `DocumentManager`。
