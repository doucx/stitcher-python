我将首先创建一个集成测试来捕捉这个“基线破坏”行为和索引统计不透明的问题。

## [WIP] test: 捕捉 Init 指令破坏现有 Sidecar 基线及索引统计不透明的问题

### 用户需求
1.  `stitcher init` 应当是幂等的，如果 Sidecar 已存在，它不应将其基线哈希强制改为源码内容。
2.  `stitcher index build` 的输出应当区分源码文件和 Sidecar 文件。

### 评论
当前的 `InitRunner` 逻辑过于简化，它假设初始化总是“从无到有”的。但在实际工程中，用户可能先创建了 Sidecar，或者希望在不改变现有 Sidecar 的情况下重新同步 Lock 文件。忽略已存在的 Sidecar 会导致基线漂移，这是架构上的不严谨。

### 目标
1.  创建一个集成测试 `test_init_respects_existing_sidecar_baseline`，验证 `init` 后 Lock 文件中的 `baseline_yaml_content_hash` 是否指向 Sidecar 的内容而非源码内容。
2.  创建一个集成测试 `test_index_stats_reports_sidecars`，验证索引输出是否包含 Sidecar 的统计信息。

### 基本原理
通过 `WorkspaceFactory` 构建一个包含“不一致”状态的初始环境（源码 doc 与 Sidecar 内容不同），执行 `init` 或 `index`，然后通过断言 `SpyBus` 捕获的消息内容和 `stitcher.lock` 的实际存储值来验证故障。

### 标签
#intent/test #flow/ready #priority/high #comp/application #comp/index #concept/state #scope/dx #ai/delegate #task/domain/testing #task/object/init-idempotency #task/action/reproduce #task/state/begin

---

### Script

#### Acts 1: 创建复现测试用例

我们将创建一个新的集成测试文件，专门用于验证 `init` 的幂等性和 Sidecar 基线保护。

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_init_sidecar_idempotency.py
~~~~~
~~~~~python
import hashlib
from stitcher.test_utils import create_test_app, SpyBus, WorkspaceFactory, get_stored_hashes
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
        .with_source("src/lib.py", 'def f(): """Source Doc"""\n    pass')
        .with_docs("src/lib.stitcher.yaml", {"f": "Sidecar Doc"})
        .build()
    )

    app = create_test_app(root_path=project_root)
    spy_bus = SpyBus()

    # 执行 init
    with spy_bus.patch(monkeypatch):
        app.run_init()

    # 获取 Lock 文件中记录的哈希
    hashes = get_stored_hashes(project_root, "src/lib.py")
    stored_yaml_hash = hashes.get("f", {}).get("baseline_yaml_content_hash")
    
    # 计算预期哈希（Sidecar 的内容）
    expected_hash = hashlib.sha256("Sidecar Doc".encode("utf-8")).hexdigest()
    
    # 预期失败：目前的实现会使用 "Source Doc" 的哈希
    assert stored_yaml_hash == expected_hash, f"Expected baseline to match Sidecar Doc ({expected_hash}), but got {stored_yaml_hash}"

def test_index_stats_should_distinguish_sidecars(tmp_path, monkeypatch):
    """
    验证索引统计信息应当区分 Sidecar 文件。
    """
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/lib.py", 'def f(): """Doc"""\n    pass')
        .with_docs("src/lib.stitcher.yaml", {"f": "Doc"})
        .build()
    )

    app = create_test_app(root_path=project_root)
    spy_bus = SpyBus()

    with spy_bus.patch(monkeypatch):
        app.run_index_build()

    # 验证消息中是否包含 sidecars 统计字段
    # 预期失败：目前 L.index.run.complete 可能不支持 sidecars 参数，或者参数为 0
    messages = spy_bus.get_messages()
    index_complete_msg = next(m for m in messages if m["id"] == str(L.index.run.complete))
    
    assert "sidecars" in index_complete_msg["params"], "Index summary should include sidecar count"
    assert index_complete_msg["params"]["sidecars"] == 1
~~~~~

### 下一步建议
1.  运行测试：执行 `pytest packages/stitcher-application/tests/integration/test_init_sidecar_idempotency.py`，确认测试失败。
2.  修改 `FileIndexer`：增强其 `stats` 结构，使其能够区分通过 `SidecarIndexerAdapter` 解析的文件。
3.  修改 `InitRunner`：在执行 `init` 时，优先从 `doc_manager.load_docs_for_module` 加载已有的磁盘文档作为基线，如果磁盘不存在，再退回到源码提取。
4.  更新 I18N 资产：为 `L.index.run.complete` 增加 `sidecars` 参数的显示。
