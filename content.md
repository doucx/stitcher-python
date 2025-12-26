简要回答
测试失败是由于重构时文件路径结构与原始 Fixture 不一致导致的。原始测试将 `tests` 目录放在 `src` 之外以验证扫描范围，而重构后的代码将其放到了 `src/app/tests` 内，导致被意外扫描。我将修正路径结构以匹配预期行为。

## [WIP] fix(tests): 修正端到端测试中的文件结构

### 错误分析
在 `test_app_run_from_config_with_source_files` 测试中，断言失败（预期 3 条成功消息，实际收到 4 条）。这是因为在重构测试时，我错误地将测试文件放置在 `src/app/tests/test_helpers.py`。由于配置的 `scan_paths` 为 `["src/app"]`，系统正确地递归扫描并处理了该文件，导致生成了额外的 Stub 文件。

原始 Fixture 的结构是将 `tests` 目录置于项目根目录，与 `src` 平级，旨在验证扫描器不会越界处理未配置的路径。

### 用户需求
修复集成测试失败，确保测试逻辑正确验证“仅扫描指定路径”的行为。

### 评论
这是一个典型的迁移错误，但也从侧面验证了 `rglob` 扫描逻辑的正确性（即它确实扫描了子目录）。修正此路径将恢复测试的原始意图。

### 目标
修改 `tests/integration/test_end_to_end.py`，将干扰测试文件移出扫描范围。

### 基本原理
将 `test_helpers.py` 移动到 `tests/` 目录（根目录下），使其位于 `src/app` 之外。这将确保它不被 `scan_paths = ["src/app"]` 捕获，从而使生成的 Stub 文件数量回归到预期的 2 个（`main.py` 和 `helpers.py`），总成功消息数为 3。

### 标签
#intent/fix #flow/ready #priority/high #comp/tests #task/domain/testing #task/object/integration-tests #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 修正测试文件路径

~~~~~act
patch_file
tests/integration/test_end_to_end.py
~~~~~
~~~~~python.old
        .with_source(
            "src/app/utils/helpers.py",
            """
            def assist():
                \"\"\"Provides assistance.\"\"\"
                pass
            """,
        )
        # This file should remain untouched/unscanned
        .with_source("src/app/tests/test_helpers.py", "def test_assist(): pass")
        .build()
    )

    app = StitcherApp(root_path=project_root)
~~~~~
~~~~~python.new
        .with_source(
            "src/app/utils/helpers.py",
            """
            def assist():
                \"\"\"Provides assistance.\"\"\"
                pass
            """,
        )
        # This file should remain untouched/unscanned
        .with_source("tests/test_helpers.py", "def test_assist(): pass")
        .build()
    )

    app = StitcherApp(root_path=project_root)
~~~~~

### 下一步建议
测试通过后，可以安全地删除旧的 `tests/fixtures` 目录。
