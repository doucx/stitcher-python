好的，所有的测试都已经顺利通过，这证明我们的重构不仅实现了预期的“高保真”目标，而且在逻辑上是严密且可靠的。

现在，我们将把这一系列极具价值的变更作为一个完整的逻辑单元提交到 Git 历史中。

## [COMMIT] refactor: 实现高保真 Sidecar 更新逻辑并净化系统架构

### 用户需求
在验证测试通过后，将本次关于“高保真原则”的所有架构修正、功能实现及测试增强正式提交。

### 评论
这是一次深度的、原则驱动的重构。我们不仅解决了具体的技术异味，更重要的是通过代码确立了“保真性高于一切”的工程准则。这为 Stitcher 成为一个尊重用户意图、专业且可靠的工具奠定了最坚实的基础。

### 目标
1.  将所有修改和新增的文件添加到 Git 暂存区。
2.  创建一个内容详尽的提交，记录本次重构的核心变更和架构决策。

### 基本原理
通过创建一个单一的、逻辑清晰的提交，我们为项目的演进留下了一份高质量的存证。这个提交记录了我们如何通过“意图感知”的 I/O 策略、接口契约的同步更新以及严格的集成测试，将模糊的架构共识转化为确定的代码实现。

### 标签
#intent/refine #flow/ready #priority/high #comp/core #scope/api #scope/dx #ai/instruct #task/domain/architecture #task/object/fidelity-refactor #task/action/integration #task/state/end

---

### Script

#### Acts 1: 提交变更

我将把所有相关的代码变更、协议更新和测试增强添加到暂存区，并创建一个详细的提交。

~~~~~act
git_add
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/adapter.py
packages/stitcher-lang-sidecar/tests/unit/test_sidecar_adapter.py
packages/stitcher-application/src/stitcher/app/services/doc_manager.py
packages/stitcher-application/src/stitcher/app/runners/pump/executor.py
packages/stitcher-application/src/stitcher/app/core.py
packages/stitcher-cli/tests/integration/test_fidelity_principles.py
packages/stitcher-application/tests/unit/runners/pump/test_pump_executor.py
packages/stitcher-spec/src/stitcher/spec/managers.py
packages/stitcher-refactor/src/stitcher/refactor/engine/planner.py
packages/stitcher-application/tests/unit/test_doc_overlay.py
packages/stitcher-common/src/stitcher/common/__init__.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor: implement high-fidelity sidecar updates and architectural cleanup

This commit enforces the "Fidelity is Paramount" and "Separation of Concerns" principles across the core engine and CLI.

Key Changes:
- SidecarAdapter: Re-implemented 'save_doc_irs' with intentional branching. It now distinguishes between 'CREATE' (standardized formatting) and 'UPDATE' (high-fidelity round-trip using ruamel.yaml) to preserve user comments, formatting, and key order.
- DocumentManager & Spec: Updated 'DocumentManagerProtocol' and its implementation to expose high-fidelity raw I/O methods.
- PumpExecutor: Refactored to use the new high-fidelity update path, ensuring 'stitcher pump' never corrupts manual documentation adjustments.
- Check Command: Removed implicit and destructive 'reformat_all' side-effects, ensuring 'check' remains a read-only validation tool.
- Architecture Cleanup: Physically removed the legacy 'YamlAdapter' from stitcher-common and 'updater.py' from stitcher-refactor, centralizing sidecar I/O in stitcher-lang-sidecar.
- Testing: Introduced 'test_fidelity_principles.py' to strictly verify that updates preserve comments/order and that 'check' has no formatting side-effects.

This refactor ensures that Stitcher respects the human element of documentation while maintaining structural integrity.
~~~~~

### 下一步建议

重构工作已圆满完成！为了保持这一势头，我建议您接下来的行动是：

1.  **记录未来任务**：在您的问题跟踪系统中正式创建 **“实现 `stitcher format` 命令”** 的任务。这将为需要确定性格式化（如 pre-commit 钩子）的用户提供一个显式的、可控的选择，同时不违背我们的高保真原则。
2.  **架构审查**：您可以审查一下 `stitcher-stubgen` 中是否存在类似的隐式格式化行为，确保“保真性”原则在整个项目中得到统一贯彻。

感谢您的信任与高效协作，我们共同构建了一个更加稳健的系统！
