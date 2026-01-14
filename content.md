好的，分析非常清晰。性能瓶颈确实在于重复的 I/O 和 YAML 解析，而根本原因在于我们将 Sidecar 文件视为被动数据而非主动的“文档源代码”。将其纳入增量索引是解决此问题的正确架构方向。

循环依赖问题也暴露了导入路径不够严谨，需要修正。

我将生成一个计划来解决这两个问题：
1.  **修复循环依赖**：通过将 `indexer.py` 中的绝对导入更改为相对导入来打破循环。
2.  **验证索引缓存**：创建一个新的集成测试，明确验证在文件未更改的情况下，后续的 `check` 命令会命中索引缓存，从而跳过昂贵的 YAML 文件解析。

## [WIP] test: 修复循环依赖并验证索引缓存

### 用户需求

1.  修复 `stitcher-lang-sidecar` 包中 `__init__.py` -> `indexer.py` -> `parser.py` 之间因不当的绝对导入而引起的循环依赖问题。
2.  创建一个新的集成测试，以验证将 Sidecar 文件纳入索引后，缓存机制能够按预期工作，避免在文件未变更时重复解析 YAML 文件。

### 评论

这是一个关键的架构重构和验证步骤。修复循环依赖保证了系统的健壮性。而添加缓存命中测试则为我们“将 Sidecar 视为一等语言公民”这一重大架构决策的性能收益提供了明确的、可自动验证的证据。这个测试将成为未来性能回归的重要护栏。

### 目标

1.  修改 `packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/indexer.py`，将对 `parser` 的导入从绝对路径改为相对路径。
2.  在 `packages/stitcher-application/tests/integration/` 目录下创建一个新的测试文件 `test_check_cache.py`。
3.  在新测试文件中，设计一个测试用例，该用例：
    *   第一次运行 `app.run_check()` 来填充索引。
    *   第二次运行时，通过 `monkeypatch` 监视底层的文件 I/O 函数 (`SidecarAdapter.load_doc_irs`)，并断言其**未被调用**（缓存命中）。
    *   （可选增强）修改一个 sidecar 文件后，第三次运行 `app.run_check()`，并断言 I/O 函数**被调用**（缓存失效）。

### 基本原理

*   **循环依赖修复**：在 Python 中，同一个包内的模块间应优先使用相对导入 (`from . import ...`)。这可以避免在导入子模块时意外触发并重新执行包的 `__init__.py`，从而有效规避循环依赖问题。
*   **缓存验证**：我们的增量索引系统基于文件的 `mtime` 和 `hash`。如果文件未变，`FileIndexer` 会跳过它。我们的测试将通过 `monkeypatch` 监视一个位于索引流程下游、且只有在文件需要被重新解析时才会触发的函数。如果第二次运行时此函数未被调用，则证明了整个增量索引链条（从文件系统状态检测到数据库查询）是有效的。

### 标签

#intent/fix #intent/tooling #flow/ready #priority/critical #comp/tests #comp/lang-sidecar #concept/state #scope/dx #ai/instruct #task/domain/testing #task/object/cache-validation #task/action/implementation #task/state/begin

---

### Script

#### Acts 1: 修复循环依赖

我们将 `indexer.py` 中的绝对导入改为相对导入，以打破循环。

~~~~~act
patch_file
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/indexer.py
~~~~~
~~~~~python.old
from stitcher.spec import URIGeneratorProtocol, DocstringSerializerProtocol
from stitcher.spec.registry import LanguageAdapter
from stitcher.spec.index import SymbolRecord, ReferenceRecord
from stitcher.lang.sidecar.parser import parse_doc_references
from stitcher.lang.python.analysis.models import ReferenceType
from stitcher.lang.python.analysis.utils import path_to_logical_fqn
~~~~~
~~~~~python.new
from stitcher.spec import URIGeneratorProtocol, DocstringSerializerProtocol
from stitcher.spec.registry import LanguageAdapter
from stitcher.spec.index import SymbolRecord, ReferenceRecord
from .parser import parse_doc_references
from stitcher.lang.python.analysis.models import ReferenceType
from stitcher.lang.python.analysis.utils import path_to_logical_fqn
~~~~~

#### Acts 2: 编写缓存验证测试

现在，我们添加新的集成测试来验证索引缓存是否按预期工作。

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_check_cache.py
~~~~~
~~~~~python
from unittest.mock import MagicMock
from stitcher.test_utils import WorkspaceFactory, create_test_app


def test_check_hits_index_cache_on_second_run(tmp_path, monkeypatch):
    """
    Verifies that a second 'check' run without file changes hits the index cache
    and avoids re-parsing YAML files.
    """
    # 1. Arrange: A standard workspace
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", "def func(): pass")
        .with_docs("src/main.stitcher.yaml", {"func": "doc"})
        .build()
    )
    app = create_test_app(project_root)

    # 2. Act (First Run): Populate the index
    # We don't need to check the result, just warm up the index.
    app.run_check()

    # 3. Arrange (Spying): Patch the expensive IO/parsing method
    # This method is downstream of the indexer and should only be called on a cache miss.
    from stitcher.lang.sidecar.adapter import SidecarAdapter

    mock_load_irs = MagicMock(wraps=SidecarAdapter.load_doc_irs)
    monkeypatch.setattr(
        "stitcher.lang.sidecar.adapter.SidecarAdapter.load_doc_irs", mock_load_irs
    )

    # 4. Act (Second Run): This run should hit the cache
    app.run_check()

    # 5. Assert (Cache Hit): The expensive method was NOT called
    mock_load_irs.assert_not_called()

    # 6. Act (Third Run - Cache Miss): Modify a file to invalidate the cache
    (project_root / "src/main.stitcher.yaml").write_text(
        'func: "updated doc"', encoding="utf-8"
    )
    app.run_check()

    # 7. Assert (Cache Miss): The expensive method was called this time
    mock_load_irs.assert_called_once()
~~~~~

### 下一步建议

我们已经修复了循环依赖并添加了验证缓存的关键测试。现在，我们可以继续优化 `CheckSubjectAdapter` 和 `DocumentManager`，确保它们完全利用索引数据，从而彻底消除 I/O 瓶颈。

下一步，我建议修改 `DocumentManager` 的 `load_docs_for_path` 方法，使其优先从注入的 `IndexStore` 中读取数据，只有在索引缺失时才回退到文件 I/O。
