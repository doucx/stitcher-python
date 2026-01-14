我将立刻开始实施。遵循“高保真工程公理”，我们首先从最核心的契约（Protocol）层开始重构，确保整个系统的基础是稳固且语义清晰的。

这是一个分步计划的第一步，我们将首先修改 `stitcher-spec` 包中的核心定义。

## [WIP] refactor(spec): 在 DocstringSerializerProtocol 中分离 DTO 与视图序列化

### 用户需求

重构序列化协议，以支持用于数据库索引的、确定性的 JSON 安全数据，以及用于 `.stitcher.yaml` 文件的高保真视图。

### 评论

这是奠基性的一步。通过在 `spec` 中定义一个干净、语义精确的契约，我们消除了模糊性，并强制所有实现类都遵循新的、更清晰的架构。这是“接口隔离原则”的经典应用。

### 目标

将 `DocstringSerializerProtocol` 中模棱两可的 `to_yaml`/`from_yaml` 方法，替换为两对目标明确的方法：
1.  `to_transfer_data`/`from_transfer_data`: 用于数据库存储和哈希计算。
2.  `to_view_data`/`from_view_data`: 用于高保真的文件 I/O。

### 基本原理

现有的协议混淆了两种截然不同的职责，这导致了实现上的技巧和混乱，并且使得与基于 JSON 的数据库缓存集成在物理上变得不可能。将这些关注点分离到显式的方法中，会使系统的数据流变得透明和健壮。

### 标签

#intent/refine #flow/ready #priority/high #comp/spec #concept/serialization #scope/api #ai/brainstorm #task/domain/testing #task/object/serialization-protocol #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: 重构 DocstringSerializerProtocol

我们将更新 `protocols.py` 文件，用新的方法替换旧的 `DocstringSerializerProtocol` 定义，以明确区分数据传输和视图渲染两种场景。

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/protocols.py
~~~~~
~~~~~python.old
class DocstringSerializerProtocol(Protocol):
    def to_yaml(self, ir: DocstringIR) -> Union[str, Dict[str, Any]]: ...

    def from_yaml(self, data: Union[str, Dict[str, Any]]) -> DocstringIR: ...
~~~~~
~~~~~python.new
class DocstringSerializerProtocol(Protocol):
    """
    负责 DocstringIR 的序列化与反序列化。
    区分“数据传输(DTO)”与“人类视图(View)”两种场景。
    """

    # --- 数据传输层 (Data Transfer Layer) ---
    # 用于：Database Storage, Hashing, Inter-process Communication
    # 约束：必须返回 JSON-safe 的原生类型 (dict, list, str, int, bool)。严禁自定义对象。
    def to_transfer_data(self, ir: DocstringIR) -> Dict[str, Any]: ...

    def from_transfer_data(self, data: Dict[str, Any]) -> DocstringIR: ...

    # --- 视图层 (View Layer) ---
    # 用于：YAML File Generation, CLI Output
    # 约束：可以返回 ruamel.yaml 的富文本对象 (CommentedMap, LiteralScalarString) 以控制格式。
    def to_view_data(self, ir: DocstringIR) -> Any: ...

    def from_view_data(self, data: Any) -> DocstringIR: ...
~~~~~

### 下一步建议

契约已经更新。这必然会导致所有实现该协议的类（位于 `stitcher-lang-python` 包中）在类型检查时失败。

下一步，我们将修改 `RawSerializer`、`StructuredSerializer`、`GoogleSerializer` 和 `NumpySerializer`，使其遵循这个新的、更严格的协议。
