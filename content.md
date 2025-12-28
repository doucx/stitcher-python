好的，我理解你的需求。将与特定软件包功能紧密集成的测试用例放到该软件包自己的 `tests/integration` 目录中，是一种优秀的项目组织实践。这能让测试与代码的对应关系更清晰，也便于独立运行特定包的测试。

根目录下的 `tests/integration` 将被保留，专门用于那些需要完整虚拟环境、安装依赖、并运行外部工具（如 `mypy` 或 `pyright`）的、执行成本非常高的端到端（E2E）测试。

我将生成一个计划来执行这个文件重组操作。

## [WIP] refactor(tests): 重构集成测试目录结构

### 用户需求
整理 `tests/integration/` 目录中的文件，将与具体软件包相关的集成测试移动到该软件包的测试目录下，只在根集成测试目录中保留那些执行非常耗时的测试。

### 评论
这是一个很好的重构建议。将测试与它们所测试的代码放在一起，可以提高项目的模块化程度和可维护性。这种分离策略（应用集成测试 vs. 真正耗时的端到端测试）是清晰且合理的。

### 目标
1.  将所有与 `stitcher-application` 相关的集成测试从 `tests/integration/` 移动到 `packages/stitcher-application/tests/integration/`。
2.  在根 `tests/integration/` 目录中保留那些依赖于 `VenvHarness` fixture 进行环境隔离和运行外部工具（`mypy`, `pyright`）的测试。
3.  保留根 `tests/integration/conftest.py` 文件，因为它为耗时的测试提供必要的 fixture（如 `isolated_env`）。

### 基本原理
通过 `move_file` 指令原子化地移动每一个测试文件。我已分析过，被移动的测试文件不依赖于根 `tests/integration/conftest.py` 中定义的 `isolated_env` fixture，因此这次移动不会破坏测试的依赖关系。保留下来的测试（如 `test_ide_proxy.py`）则确实需要这个 fixture，因此保留 `conftest.py` 是正确的。

### 标签
#intent/refine #flow/ready #priority/medium #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/integration-tests #task/action/refactor #task/state/begin

---
### Script

#### Acts 1: 将应用集成测试移动到 `stitcher-application` 包

以下操作将相关的测试文件从顶层 `tests/integration` 目录迁移到 `packages/stitcher-application/tests/integration/` 中，与它们测试的核心应用逻辑放在一起。

~~~~~act
move_file
tests/integration/test_check_command.py
packages/stitcher-application/tests/integration/test_check_command.py
~~~~~
~~~~~act
move_file
tests/integration/test_check_conflict.py
packages/stitcher-application/tests/integration/test_check_conflict.py
~~~~~
~~~~~act
move_file
tests/integration/test_check_file_tracking.py
packages/stitcher-application/tests/integration/test_check_file_tracking.py
~~~~~
~~~~~act
move_file
tests/integration/test_check_interactive_flow.py
packages/stitcher-application/tests/integration/test_check_interactive_flow.py
~~~~~
~~~~~act
move_file
tests/integration/test_check_policy.py
packages/stitcher-application/tests/integration/test_check_policy.py
~~~~~
~~~~~act
move_file
tests/integration/test_check_signatures.py
packages/stitcher-application/tests/integration/test_check_signatures.py
~~~~~
~~~~~act
move_file
tests/integration/test_check_state_machine.py
packages/stitcher-application/tests/integration/test_check_state_machine.py
~~~~~
~~~~~act
move_file
tests/integration/test_end_to_end.py
packages/stitcher-application/tests/integration/test_end_to_end.py
~~~~~
~~~~~act
move_file
tests/integration/test_hydrate_command.py
packages/stitcher-application/tests/integration/test_hydrate_command.py
~~~~~
~~~~~act
move_file
tests/integration/test_init_command.py
packages/stitcher-application/tests/integration/test_init_command.py
~~~~~
~~~~~act
move_file
tests/integration/test_lifecycle_commands.py
packages/stitcher-application/tests/integration/test_lifecycle_commands.py
~~~~~
~~~~~act
move_file
tests/integration/test_multi_target_stub_names.py
packages/stitcher-application/tests/integration/test_multi_target_stub_names.py
~~~~~
~~~~~act
move_file
tests/integration/test_stub_package.py
packages/stitcher-application/tests/integration/test_stub_package.py
~~~~~
~~~~~act
move_file
tests/integration/test_stub_package_pep561.py
packages/stitcher-application/tests/integration/test_stub_package_pep561.py
~~~~~

### 下一步建议
文件移动完成后，建议运行整个测试套件，以确保所有测试仍然可以被 `pytest` 正确发现并成功执行。
