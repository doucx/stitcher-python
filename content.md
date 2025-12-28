好的，逻辑修改已全部完成并经过验证。现在我将这些变更作为一个完整的逻辑单元进行提交。

## [COMMIT] feat(cli): 引入调试日志系统并修复扫描路径配置

### 用户需求
1.  引入 DEBUG 日志等级，以便通过 `--verbose` 选项观察文件扫描过程。
2.  消除 CLI 中的帮助文本硬编码，统一使用国际化资源。
3.  修复 `pyproject.toml` 中 `pyneedle-runtime` 扫描路径遗漏的问题。

### 评论
这是一个提升系统可观测性（Observability）的重要提交。通过引入 Debug 级别，开发者现在可以清晰地看到 Stitcher 的内部决策逻辑（如扫描了哪些路径，发现了哪些文件），这对于排查配置问题至关重要。同时，修复扫描路径配置恢复了对核心运行时包的支持。

### 目标
1.  提交所有涉及 `MessageBus` 扩展、`Renderer` 过滤逻辑、CLI 回调更新以及配置修复的文件。
2.  包含为此编写的集成测试用例。

### 基本原理
按照项目规范，所有的功能实现、优化和配置修复在通过验证后，应通过独立的 `[COMMIT]` 计划进行版本化记录。

### 标签
#intent/tooling #flow/ready #priority/medium #comp/cli #comp/common #comp/build #scope/dx #ai/instruct #task/domain/version-control #task/object/logging-and-config-fix #task/action/commit #task/state/end

---

### Script

#### Acts 1: 提交变更
将所有相关文件添加到暂存区并创建提交。

~~~~~act
git_add
packages/stitcher-common/src/stitcher/common/assets/needle/en/debug/log.json
packages/stitcher-common/src/stitcher/common/assets/needle/zh/debug/log.json
packages/stitcher-common/src/stitcher/common/messaging/bus.py
packages/stitcher-cli/src/stitcher/cli/rendering.py
packages/stitcher-cli/src/stitcher/cli/main.py
packages/stitcher-cli/src/stitcher/cli/assets/needle/en/cli/option.json
packages/stitcher-cli/src/stitcher/cli/assets/needle/zh/cli/option.json
packages/stitcher-application/src/stitcher/app/core.py
packages/stitcher-application/tests/integration/test_pump_test_files.py
pyproject.toml
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
feat(cli): implement debug logging and fix scan path configuration

Introduced a structured debug logging system to improve workspace
observability.

Key changes:
- Extended MessageBus with .debug() method for internal tracing.
- Upgraded CliRenderer to support log level filtering and dim-colored
  debug output via a new global --verbose/-v flag.
- Refactored CLI callback to implement proper dependency injection for
  the renderer, capturing global options before command execution.
- Replaced hardcoded help strings with internationalized L objects.
- Fixed a configuration error in pyproject.toml where the
  'pyneedle-runtime' package was missing from needle's scan_paths.
- Added an integration test to verify that files starting with 'test_'
  are correctly processed when explicitly included in scan paths.

This allows developers to diagnose file discovery issues by running:
'stitcher -v pump'
~~~~~

### 下一步建议
- **监控**: 现在你可以通过 `stitcher -v pump` 观察 `pyneedle-runtime` 包的扫描情况。
- **扩展调试**: 如果将来发现其他黑盒环节（如 AST 解析细节），可以继续利用新引入的 `bus.debug` 接口添加埋点。
