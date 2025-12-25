简要回答：
你的分析完全正确。这是一个非常经典的 `pytest` 配置问题。

**问题**：`pytest` 的测试发现机制非常强大，它会递归地查找所有符合 `test_*.py` 模式的文件，**包括我们放在 `tests/fixtures/` 里的测试数据**。当它找到 `tests/fixtures/sample_project/tests/test_helpers.py` 时，它试图导入它来收集测试，但由于这个 "模拟项目" 的 `src` 目录不在 `PYTHONPATH` 中，导入 `app` 模块失败了。

**解决方案**：我们必须明确地告诉 `pytest`：“不要进入 `tests/fixtures` 目录去寻找测试”。

## [WIP] fix(build): 配置 Pytest 以忽略 fixtures 目录

### 错误分析
`pytest` 在测试收集阶段，错误地将 `tests/fixtures/` 目录下的文件识别为 `stitcher-python` 项目自身的测试用例。这导致它尝试导入一个模拟项目中的测试文件 (`test_helpers.py`)，并因 `ModuleNotFoundError` 而失败。这个 fixture 项目是用于测试 `StitcherApp` 的**数据**，而不应被 `pytest` 执行。

### 用户需求
修复 `pytest` 配置，使其忽略 fixture 目录，从而让测试能够进入真正的执行阶段并报告预期的失败。

### 评论
这是一个关键的配置步骤，用以区分“测试代码”和“作为输入的测试数据”。通过使用 `norecursedirs`，我们可以精确地控制 `pytest` 的扫描范围，确保测试套件的稳定性和正确性。

### 目标
1.  修改根目录的 `pyproject.toml` 文件。
2.  在 `[tool.pytest.ini_options]` 部分添加 `norecursedirs` 配置项。
3.  确保 `tests/fixtures` 被添加到忽略列表中。

### 基本原理
`norecursedirs` 是 `pytest` 的一个标准配置，用于从测试发现过程中排除指定的目录。这是处理包含 Python 代码的测试数据目录的最佳实践。

### 标签
#intent/fix #flow/ready #priority/high
#comp/build #comp/tests #scope/dx #ai/instruct
#task/domain/infra #task/object/pytest-config #task/action/configure
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 更新 Pytest 配置以忽略 Fixtures
我们将 `norecursedirs` 添加到 `pyproject.toml` 中。

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~old
[tool.pytest.ini_options]
addopts = "-ra -q"
testpaths = ["tests", "packages"]
pythonpath = ["packages/stitcher-spec/src", "packages/stitcher-common/src", "packages/stitcher-scanner/src", "packages/stitcher-io/src", "packages/stitcher-config/src", "packages/stitcher-application/src", "packages/stitcher-cli/src"]
~~~~~
~~~~~new
[tool.pytest.ini_options]
addopts = "-ra -q"
testpaths = ["tests", "packages"]
norecursedirs = ["tests/fixtures"]
pythonpath = ["packages/stitcher-spec/src", "packages/stitcher-common/src", "packages/stitcher-scanner/src", "packages/stitcher-io/src", "packages/stitcher-config/src", "packages/stitcher-application/src", "packages/stitcher-cli/src"]
~~~~~

### 下一步建议
现在再次运行 `pytest`。测试收集错误应该会消失，取而代之的是我们真正期望看到的 `test_app_run_from_config` 测试失败（因为它还没有实现）。

一旦确认了这一点，我们将进入 **GREEN** 阶段，实现 `stitcher-config` 和 `StitcherApp` 的文件发现逻辑。
