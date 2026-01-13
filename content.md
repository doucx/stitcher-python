您完全正确。我的 apologies，我犯了一个典型的接口与实现不同步的错误。`pyright` 的静态分析错误和 `AttributeError` 测试失败指向了同一个根本原因：我将新方法添加到了具体的 `DocumentManager` *实现*中，却忘记了更新所有依赖方所遵循的 `DocumentManagerProtocol` *接口*。

这是一个严重的疏忽，感谢您的精确指正。我们必须首先修复这个契约，然后一切才能恢复正常。

## [WIP] fix(spec): 更新 DocumentManagerProtocol 以包含高保真方法

### 错误分析

`pyright` 和 `mocker.create_autospec` 都以 `DocumentManagerProtocol` 作为其行为的“真理之源”。由于我未能在此协议中声明 `load_raw_data` 和 `dump_raw_data_to_string` 方法，导致静态类型检查器认为这些调用是非法的，而测试 mock 在创建时也未能包含这些属性，从而在运行时引发了 `AttributeError`。

### 用户需求

更新位于 `stitcher-spec` 包中的 `DocumentManagerProtocol`，为其添加 `load_raw_data` 和 `dump_raw_data_to_string` 两个新方法，使其接口与 `DocumentManager` 的具体实现保持一致。

### 评论

这是一个关键的架构卫生修复。依赖于抽象（协议）而非具体实现是保持系统松耦合的核心原则。通过修复这个协议，我们不仅能解决当前的测试失败和类型错误，还能确保未来任何遵循此协议的组件都具备正确的接口契约。

### 目标

1.  在 `packages/stitcher-spec/src/stitcher/spec/managers.py` 文件中，为 `DocumentManagerProtocol` 添加 `load_raw_data` 和 `dump_raw_data_to_string` 两个方法的定义。

### 基本原理

一旦协议被更新，`pyright` 将能够正确验证 `PumpExecutor` 中对这些方法的调用。同样，`mocker.create_autospec(DocumentManagerProtocol, ...)` 将会创建一个正确包含了这些新方法的 mock 对象，从而解决 `test_pump_executor.py` 中的 `AttributeError`。这将一次性解决所有已报告的错误。

### 标签

#intent/fix #flow/ready #priority/critical #comp/spec #scope/api #ai/instruct #task/domain/architecture #task/object/fidelity-testing #task.action/bug-fix #task/state/end

---

### Script

#### Acts 1: 更新 DocumentManagerProtocol 接口

我将修改 `stitcher-spec` 中的协议文件，以包含新的高保真 I/O 方法。

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/managers.py
~~~~~
~~~~~python.old
    def compute_ir_hash(self, ir: DocstringIR) -> str: ...

    def dump_data(self, data: Dict[str, Any]) -> str: ...


class SignatureManagerProtocol(Protocol):
    def load_composite_hashes(self, file_path: str) -> Dict[str, Fingerprint]: ...
~~~~~
~~~~~python.new
    def compute_ir_hash(self, ir: DocstringIR) -> str: ...

    def dump_data(self, data: Dict[str, Any]) -> str: ...

    def load_raw_data(self, file_path: str) -> Dict[str, Any]: ...

    def dump_raw_data_to_string(self, data: Dict[str, Any]) -> str: ...


class SignatureManagerProtocol(Protocol):
    def load_composite_hashes(self, file_path: str) -> Dict[str, Fingerprint]: ...
~~~~~

### 下一步建议

这个修复直接命中了问题的根源。现在，协议、实现和消费者三者之间已经完全对齐。所有的测试，包括之前失败的 `PumpExecutor` 单元测试，现在都应该能够顺利通过。

我强烈建议您立即运行完整的测试套件。

一旦测试全部通过，我们就可以满怀信心地宣布，本次针对“高保真原则”的深度重构任务已圆满成功。我们不仅解决了最初的问题，还加固了整个系统的架构，并通过了严格的测试验证。

最后的待办事项仍然是为您记录 **“实现 `stitcher format` 命令”** 的未来任务。
