好的，所有的代码修改、测试工具升级以及集成测试用例都已经准备就绪并经过了验证。现在我们将这些变更作为一个完整的逻辑单元提交到版本库中。

## [COMMIT] feat(cli): 实现层级化 --loglevel 选项并升级 SpyBus 过滤能力

### 用户需求

将 `--loglevel` 选项集成到 `stitcher` CLI 中，替换旧的 `--verbose` 开关，并确保测试基础设施（`SpyBus`）能够正确模拟该行为，同时提供完整的测试覆盖。

### 评论

通过引入层级化的日志级别，我们极大地提升了 `stitcher` 在不同环境（开发、CI、自动化脚本）下的适应性。同时，对 `SpyBus` 的升级确保了我们的测试能够以高保真度模拟真实的渲染行为，这体现了对工程质量的严苛追求。这次提交标志着这一功能的完整交付。

### 目标

1.  **提交核心实现**: 提交 `rendering.py` 和 `main.py` 中的日志级别过滤逻辑。
2.  **提交基础设施升级**: 提交 `stitcher-test-utils` 中具备“上下文感知”能力的 `SpyBus` 增强。
3.  **提交测试套件**: 提交新的 `test_loglevel_option.py` 集成测试。
4.  **更新国际化资源**: 提交 `needle` 资源文件中关于命令行选项的更新。

### 基本原理

通过在 CLI 渲染层（`CliRenderer`）实现过滤，我们保持了业务逻辑的简洁。通过让 `SpyBus` 尊重 `bus` 中配置的 `renderer` 的日志级别，我们解决了测试工具与被测系统之间的逻辑断层。这种设计确保了系统在运行态和测试态下行为的高度一致性。

### 标签

#intent/build #flow/ready #priority/high #comp/cli #comp/tests #concept/ui #scope/dx #ai/instruct #task/domain/cli #task/object/logging #task/action/implementation #task/state/end

---

### Script

#### Acts 1: 提交日志级别功能及相关测试加固

我们将所有相关变更添加到 Git 暂存区，并创建一个详细的提交。

~~~~~act
git_add
packages/stitcher-cli/src/stitcher/cli/rendering.py
packages/stitcher-cli/src/stitcher/cli/main.py
packages/stitcher-test-utils/src/stitcher/test_utils/bus.py
packages/stitcher-cli/tests/integration/test_loglevel_option.py
packages/stitcher-common/src/stitcher/common/assets/needle/en/cli/option.json
packages/stitcher-common/src/stitcher/common/assets/needle/zh/cli/option.json
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
feat(cli): implement hierarchical --loglevel and upgrade SpyBus filtering

Replaced the binary `--verbose` flag with a hierarchical `--loglevel` option (debug, info, success, warning, error) to provide better control over CLI output.

Key changes:
- Integrated `LogLevel` filtering into `CliRenderer`.
- Updated `main.py` to use `--loglevel` as a global option with localized help strings.
- Upgraded `SpyBus` test utility to be context-aware, allowing it to accurately simulate `CliRenderer`'s filtering logic during integration tests.
- Added a comprehensive integration test suite `test_loglevel_option.py` verifying behavior across all levels.
- Updated English and Chinese i18n assets to reflect the new option.

This change improves DX by allowing cleaner CI logs and better debugging capabilities while maintaining high test fidelity.
~~~~~

### 下一步建议

- **清理旧引用**: 建议在全项目中搜索是否还有硬编码引用 `--verbose` 的地方（例如在某些旧的 Readme 或辅助脚本中），并将其更新为 `--loglevel debug`。
- **扩展日志记录**: 现在的架构已经支持层级化日志，可以考虑在 `RefactorRunner` 等复杂流程中增加更多的 `DEBUG` 级别消息，以便在开发过程中进行深度诊断。

任务圆满完成。
