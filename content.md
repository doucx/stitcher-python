这个 Profiling 结果揭示了一个严重的**计算冗余**问题，以及一个潜在的**索引未命中**问题。

1.  **3倍冗余计算 (Redundant Computation)**:
    *   `IndexCheckSubjectAdapter.get_all_symbol_states` 被调用了 **3次**（分别由 `SignatureRule`, `ExistenceRule`, `ContentRule` 触发）。
    *   每次调用都完整执行了 `load_docs_for_path` 和 `LockFileManager.load`。
    *   这导致了昂贵的 IO 操作（无论是读文件还是查库）被重复执行了 3 次。
    *   **影响**: 占据了总耗时的绝大部分（约 1.0s / 1.34s）。

2.  **索引回退 (Index Fallback)**:
    *   Profiling 明确显示调用栈进入了 `ruamel.yaml` 的解析逻辑 (`YAML.load`)。
    *   这意味着 `DocumentManager.load_docs_for_path` 中的 `if self.index_store` 检查虽然执行了，但未能从索引中获取到数据，因此回退到了文件系统读取。
    *   这说明尽管我们已经实施了“Sidecar 进索引”的架构，但在实际运行时，索引可能因为某种原因（如文件未被发现、解析失败或查询路径不匹配）未能提供服务。

为了立即解决性能瓶颈，我们将采取**两步走**策略：

1.  **第一步（即时止血）：在 Adapter 层增加缓存**。
    *   `IndexCheckSubjectAdapter` 在一次分析生命周期内，其状态是不变的。
    *   我们将使用 `functools.cached_property` 或手动缓存来确保 `get_all_symbol_states` 只执行一次。
    *   这将直接消除 2/3 的开销，立竿见影。

2.  **第二步（根本原因）：诊断并修复索引未命中**。
    *   虽然缓存能减少 IO 次数，但单次 IO 仍然走的是慢速的文件系统路径。
    *   我们需要确保 `.stitcher.yaml` 被正确索引并能被查询到。

以下计划将首先实施**缓存优化**。

## [WIP] perf: 为 CheckSubjectAdapter 增加状态缓存以消除冗余 IO

### 用户需求
根据 Profiling 报告，`stitcher check` 的大部分时间消耗在重复加载文档和 Lock 文件上。用户需要通过消除这些冗余操作来提升 CLI 响应速度。

### 评论
这是一个典型的“以空间换时间”优化。在 `ConsistencyEngine` 的设计中，一个 Subject 会被多个 Rule 访问。Subject 应当保证其数据获取是幂等的且高效的。引入缓存不仅能解决当前的性能问题，还能使系统对未来的 Rule 扩展更具鲁棒性。

### 目标
1.  修改 `IndexCheckSubjectAdapter`，缓存 `get_all_symbol_states` 的结果。
2.  修改 `ASTCheckSubjectAdapter`，同样增加缓存机制。

### 基本原理
利用 Python 的 `@functools.lru_cache(maxsize=1)` 或手动 `self._cached_states` 变量，确保昂贵的数据加载逻辑在对象生命周期内只执行一次。

### 标签
#intent/refine #intent/perf #flow/ready #priority/high #comp/application #comp/analysis #concept/caching #scope/core #ai/instruct #task/domain/performance #task/object/adapter #task/action/cache #task/state/begin

---

### Script

#### Acts 1: Cache `IndexCheckSubjectAdapter` states
I will add caching to the index-based adapter. Since `get_all_symbol_states` is a method that might be called multiple times, caching its return value is crucial.

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/subject.py
~~~~~
~~~~~python.old
    def __init__(
        self,
        file_path: str,
        index_store: IndexStoreProtocol,
        doc_manager: DocumentManagerProtocol,
        lock_manager: LockManagerProtocol,
        uri_generator: URIGeneratorProtocol,
        workspace: Workspace,
        root_path: Path,
    ):
        self._file_path = file_path
        self._index_store = index_store
        self._doc_manager = doc_manager
        self._lock_manager = lock_manager
        self._uri_generator = uri_generator
        self._workspace = workspace
        self._root_path = root_path

    @property
~~~~~
~~~~~python.new
    def __init__(
        self,
        file_path: str,
        index_store: IndexStoreProtocol,
        doc_manager: DocumentManagerProtocol,
        lock_manager: LockManagerProtocol,
        uri_generator: URIGeneratorProtocol,
        workspace: Workspace,
        root_path: Path,
    ):
        self._file_path = file_path
        self._index_store = index_store
        self._doc_manager = doc_manager
        self._lock_manager = lock_manager
        self._uri_generator = uri_generator
        self._workspace = workspace
        self._root_path = root_path
        self._cached_states: Optional[Dict[str, SymbolState]] = None

    @property
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/subject.py
~~~~~
~~~~~python.old
    def get_all_symbol_states(self) -> Dict[str, SymbolState]:
        # 1. Load data from all sources
        symbols_from_db = self._index_store.get_symbols_by_file_path(self.file_path)
        yaml_docs = self._doc_manager.load_docs_for_path(self.file_path)

        # Load Lock Data
~~~~~
~~~~~python.new
    def get_all_symbol_states(self) -> Dict[str, SymbolState]:
        if self._cached_states is not None:
            return self._cached_states

        # 1. Load data from all sources
        symbols_from_db = self._index_store.get_symbols_by_file_path(self.file_path)
        yaml_docs = self._doc_manager.load_docs_for_path(self.file_path)

        # Load Lock Data
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/subject.py
~~~~~
~~~~~python.old
                baseline_yaml_content_hash=stored_fp.get("baseline_yaml_content_hash"),
            )

        return states


class ASTCheckSubjectAdapter(CheckSubject):
~~~~~
~~~~~python.new
                baseline_yaml_content_hash=stored_fp.get("baseline_yaml_content_hash"),
            )

        self._cached_states = states
        return states


class ASTCheckSubjectAdapter(CheckSubject):
~~~~~

#### Acts 2: Cache `ASTCheckSubjectAdapter` states
Apply the same optimization to the AST-based adapter for consistency and performance in virtual/plugin scenarios.

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/subject.py
~~~~~
~~~~~python.old
        self._workspace = workspace
        self._fingerprint_strategy = fingerprint_strategy
        self._root_path = root_path

    @property
    def file_path(self) -> str:
~~~~~
~~~~~python.new
        self._workspace = workspace
        self._fingerprint_strategy = fingerprint_strategy
        self._root_path = root_path
        self._cached_states: Optional[Dict[str, SymbolState]] = None

    @property
    def file_path(self) -> str:
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/subject.py
~~~~~
~~~~~python.old
    def get_all_symbol_states(self) -> Dict[str, SymbolState]:
        # 1. Load all necessary data from various sources
        source_docs = self._doc_manager.flatten_module_docs(self._module)
        yaml_docs = self._doc_manager.load_docs_for_module(self._module)
~~~~~
~~~~~python.new
    def get_all_symbol_states(self) -> Dict[str, SymbolState]:
        if self._cached_states is not None:
            return self._cached_states

        # 1. Load all necessary data from various sources
        source_docs = self._doc_manager.flatten_module_docs(self._module)
        yaml_docs = self._doc_manager.load_docs_for_module(self._module)
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/subject.py
~~~~~
~~~~~python.old
                baseline_yaml_content_hash=stored_fp.get("baseline_yaml_content_hash"),
            )

        return states
~~~~~
~~~~~python.new
                baseline_yaml_content_hash=stored_fp.get("baseline_yaml_content_hash"),
            )

        self._cached_states = states
        return states
~~~~~

### 下一步建议
实施缓存后，Profiling 中的重复调用应该会消失。如果系统仍然慢，那就要集中精力解决“索引回退”的问题，即为什么 `load_docs_for_path` 没有命中 DB。建议在这次优化后再次运行 Profile 或测试。
