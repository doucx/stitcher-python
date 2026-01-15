简要回答
发现了。由于在 `def` 行末尾直接写了文档字符串（一写多）后，下一行又出现了缩进的 `pass`，导致 Python 解释器（及 Griffe 解析器）判定为 `unexpected indent` 语法错误。

这导致文件未能被正确解析，进而导致 `pump` 流程直接跳过，最终 `stored_yaml_hash` 为 `None`。我将修正测试中的源码模板。

## [WIP] fix: 修正测试用例中的 Python 源码语法错误

### 错误分析
测试中使用的源码字符串：
```python
'def f(): """Source Doc"""\n    pass'
```
在 Python 中，如果函数定义在同一行包含了语句（如 docstring），则该语句块已结束。下一行带有缩进的 `pass` 会触发 `IndentationError: unexpected indent`。

解析失败导致 `ScannerService` 无法生成 `ModuleDef`，`StitcherApp.run_init()` 因此没有执行任何实际的 `pump` 逻辑，也没有更新 `stitcher.lock`。

### 用户需求
修正 `packages/stitcher-application/tests/integration/test_init_sidecar_idempotency.py` 中的语法错误。

### 评论
这类语法错误在动态生成代码的测试中很常见。将文档字符串移至新行是标准且安全的做法。

### 目标
1.  修正 `test_init_respects_existing_sidecar_baseline` 中的源码字符串。
2.  修正 `test_index_stats_should_distinguish_sidecars` 中的源码字符串。
3.  移除调试用的 `print` 语句。

### 基本原理
通过将 docstring 放置在缩进块内，确保源码符合 PEP 8 规范且能被 AST 解析器正确处理。

### 标签
#intent/fix #flow/ready #priority/high #comp/tests #task/domain/testing #task/object/test-syntax #task/action/fix #task/state/continue

---

### Script

#### Acts 1: 修正测试文件中的语法错误及清理调试代码

我们将修正测试中的 Python 源码定义，并移除之前为了排查错误添加的 `print` 语句。

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_init_sidecar_idempotency.py
~~~~~
~~~~~python
from stitcher.test_utils import (
    create_test_app,
    SpyBus,
    WorkspaceFactory,
    get_stored_hashes,
)
from needle.pointer import L


def test_init_respects_existing_sidecar_baseline(tmp_path, monkeypatch):
    """
    验证 init 不会破坏已存在的 Sidecar 基线。
    场景：
    - 源码中函数 f 的 doc 为 "Source Doc"
    - Sidecar 文件中 f 的内容为 "Sidecar Doc"
    - 执行 init 后，lock 文件中的基线哈希应当对应 "Sidecar Doc"
    """
    factory = WorkspaceFactory(tmp_path)
    # 准备环境
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/lib.py", 'def f():\n    """Source Doc"""\n    pass')
        .with_docs("src/lib.stitcher.yaml", {"f": "Sidecar Doc"})
        .build()
    )

    app = create_test_app(root_path=project_root)
    spy_bus = SpyBus()

    # 执行 init (现在等于 pump --reconcile)
    with spy_bus.patch(monkeypatch):
        app.run_init()

    # 获取 Lock 文件中记录的哈希
    hashes = get_stored_hashes(project_root, "src/lib.py")
    stored_yaml_hash = hashes.get("f", {}).get("baseline_yaml_content_hash")

    # 计算预期哈希（Sidecar 的内容）
    doc_manager = app.doc_manager
    ir = doc_manager.serializer.from_view_data("Sidecar Doc")
    expected_hash = doc_manager.compute_ir_hash(ir)

    # 验证 pump --reconcile 正确保留了 Sidecar 内容作为基线
    assert stored_yaml_hash == expected_hash, (
        f"Expected baseline to match Sidecar Doc ({expected_hash}), but got {stored_yaml_hash}"
    )

    # 验证输出消息（应该包含 Reconciled 信息）
    spy_bus.assert_id_called(L.pump.info.reconciled, level="info")


def test_index_stats_should_distinguish_sidecars(tmp_path, monkeypatch):
    """
    验证索引统计信息应当区分 Sidecar 文件。
    """
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/lib.py", 'def f():\n    """Doc"""\n    pass')
        .with_docs("src/lib.stitcher.yaml", {"f": "Doc"})
        .build()
    )

    app = create_test_app(root_path=project_root)
    spy_bus = SpyBus()

    with spy_bus.patch(monkeypatch):
        app.run_index_build()

    # 验证消息中是否包含 sidecars 统计字段
    messages = spy_bus.get_messages()
    index_complete_msg = next(
        m for m in messages if m["id"] == str(L.index.run.complete)
    )

    assert "sidecars" in index_complete_msg["params"], (
        "Index summary should include sidecar count"
    )
    assert index_complete_msg["params"]["sidecars"] == 1
~~~~~

### 下一步建议
语法修正后，解析器应当能正确识别 `lib.py` 中的函数 `f`。请再次运行测试。如果仍然失败，请检查 `LockSession` 在处理 `RECONCILE` 动作时是否确实调用了 `record_fresh_state`。
