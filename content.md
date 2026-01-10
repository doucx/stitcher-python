分析完全正确。在我们上次的重构中，`RefactorRunner` 和 `Workspace` 的初始化流程被改变为强制依赖于一个 `StitcherConfig` 对象。然而，相关的集成测试 `test_refactor_apply_e2e` 和 `test_refactor_apply_dry_run` 没有被同步更新，它们创建的测试环境中缺少了 `[tool.stitcher]` 配置。

因此，当测试运行 `refactor apply` 命令时：
1.  `StitcherApp.run_refactor_apply` 调用 `_load_configs()`。
2.  `_load_configs()` 在测试生成的 `pyproject.toml` 中找不到 `[tool.stitcher]` 部分，因此返回一个空列表。
3.  `run_refactor_apply` 检测到 `configs` 为空，发出 `L.error.config.not_found` 错误消息，并返回 `False`。
4.  CLI 命令接收到 `False` 的结果，随即以 `typer.Exit(code=1)` 退出，导致测试断言失败。

应用程序的行为是完全正确的——它正确地指出了配置缺失的错误。我们需要修复的是测试用例，使其提供一个完整的、有效的测试环境。

我将生成一个计划来修复这些测试。

## [WIP] fix: Update refactor command tests to provide Stitcher config

### 错误分析

在将 `Workspace` 的构建逻辑重构为依赖 `StitcherConfig` 后，`refactor apply` 命令现在强制要求在 `pyproject.toml` 中存在一个有效的 `[tool.stitcher]` 配置节。

当前的集成测试 (`test_refactor_apply_e2e` 和 `test_refactor_apply_dry_run`) 使用 `WorkspaceFactory` 创建测试项目，但没有为 `refactor` 命令提供必要的配置。这导致 `StitcherApp` 在执行时无法加载到任何配置，从而提前返回失败状态，CLI 随之以退出码 1 终止，导致测试失败。

此问题并非应用逻辑的 Bug，而是测试环境与应用最新前置条件不匹配导致的。

### 用户需求

修复 `packages/stitcher-cli/tests/integration/test_refactor_command.py` 中两个失败的测试，使其能够适应 `refactor apply` 命令对 `StitcherConfig` 的新依赖。

### 评论

这是一个很好的例子，展示了测试套件如何在我们重构和增强系统时，充当安全网并明确地指出契约变化。测试的失败不是一个问题，而是一个信号，它告诉我们命令的外部依赖已经改变。通过修复测试，我们使其更准确地反映了应用的当前行为和要求。

### 目标

1.  定位到 `test_refactor_command.py` 文件中 `test_refactor_apply_e2e` 和 `test_refactor_apply_dry_run` 两个测试函数。
2.  在每个测试的 `WorkspaceFactory` 构建链中，使用 `.with_config()` 方法添加一个最小化的 `[tool.stitcher]` 配置。
3.  该配置必须包含 `scan_paths = ["src"]`，以确保 `Workspace` 能够正确发现测试代码。

### 基本原理

我们将利用 `stitcher-test-utils` 包中提供的 `WorkspaceFactory` 的流式 API。通过在其构建链上增加一个 `.with_config({"scan_paths": ["src"]})` 调用，`WorkspaceFactory` 将在生成的 `pyproject.toml` 文件中自动创建 `[tool.stitcher]` 表，并填入指定的 `scan_paths`。这将为 `refactor` 命令提供其现在必需的配置信息，使得 `_load_configs()` 能够成功加载配置，从而让测试流程可以继续执行并验证核心的重构逻辑。

### 标签

#intent/fix #flow/ready #priority/high #comp/tests #comp/cli #concept/config #scope/dx #ai/instruct #task/domain/architecture #task/object/config-unification #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 修复集成测试

我们将为两个失败的测试用例的 `WorkspaceFactory` 设置添加 `.with_config()` 调用。

首先是 `test_refactor_apply_e2e`：

~~~~~act
patch_file
packages/stitcher-cli/tests/integration/test_refactor_command.py
~~~~~
~~~~~python.old
def test_refactor_apply_e2e(tmp_path, monkeypatch):
    # 1. Arrange: Create a project and a migration script
    factory = WorkspaceFactory(tmp_path)
    # Project with a symbol to be renamed
    (
        factory.with_project_name("mypkg")
        .with_source("src/mypkg/__init__.py", "")
        .with_source("src/mypkg/core.py", "class Old: pass")
        .with_source("src/mypkg/app.py", "from mypkg.core import Old")
    ).build()
~~~~~
~~~~~python.new
def test_refactor_apply_e2e(tmp_path, monkeypatch):
    # 1. Arrange: Create a project and a migration script
    factory = WorkspaceFactory(tmp_path)
    # Project with a symbol to be renamed
    (
        factory.with_project_name("mypkg")
        .with_config({"scan_paths": ["src"]})
        .with_source("src/mypkg/__init__.py", "")
        .with_source("src/mypkg/core.py", "class Old: pass")
        .with_source("src/mypkg/app.py", "from mypkg.core import Old")
    ).build()
~~~~~

然后是 `test_refactor_apply_dry_run`：

~~~~~act
patch_file
packages/stitcher-cli/tests/integration/test_refactor_command.py
~~~~~
~~~~~python.old
    (
        factory.with_project_name("mypkg")
        .with_source("src/mypkg/__init__.py", "")
        .with_source("src/mypkg/core.py", "class Old: pass")
        .with_source("src/mypkg/app.py", "from mypkg.core import Old")
    ).build()
~~~~~
~~~~~python.new
    (
        factory.with_project_name("mypkg")
        .with_config({"scan_paths": ["src"]})
        .with_source("src/mypkg/__init__.py", "")
        .with_source("src/mypkg/core.py", "class Old: pass")
        .with_source("src/mypkg/app.py", "from mypkg.core import Old")
    ).build()
~~~~~

### 下一步建议

我们已经修复了因上次重构而损坏的测试。现在，测试套件应该能再次成功通过 (回到 GREEN 状态)。

我建议先在本地运行测试以确认修复。一旦确认，我们就可以继续执行路线图的下一个任务：**阶段 4.1：实现“观测域”逻辑**，即让 `SemanticGraph` 能够加载并解析 `peripheral_paths` 中定义的脚本文件。
