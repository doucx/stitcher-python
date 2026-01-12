好的，我们继续协议净化的工作，现在专注于 `IndexStoreProtocol`。

当前 `IndexStoreProtocol` 只定义了读操作，这使得依赖它的 Runner (如 `CheckRunner`) 得以解耦。然而，负责写操作的核心组件 `FileIndexer` 仍然直接依赖于具体的 `IndexStore` 类，这使得索引过程与 SQLite 实现紧密耦合。

我们的目标是扩展 `IndexStoreProtocol`，使其包含索引写入和同步所需的全部接口，然后将 `FileIndexer` 的依赖从具体类切换到此协议，从而完成整个索引子系统的依赖倒置。

## [WIP] refactor: 扩展 IndexStoreProtocol 以包含写和同步操作

### 用户需求
用户要求继续净化 `IndexStore` 相关的协议。目前的 `IndexStoreProtocol` 仅覆盖了数据读取的场景，而索引的写入/更新逻辑 (`FileIndexer`) 仍然紧密耦合于具体的 `IndexStore` SQLite 实现。需要将 `FileIndexer` 的依赖也切换到协议上，以实现完全的抽象。

### 评论
这是完成“阶段三：核心服务抽象化”的关键一步。将 `FileIndexer` 与具体的数据库实现解耦，将带来巨大的收益：首先，它使得测试复杂的索引逻辑成为可能，我们可以用一个内存中的 Mock Store 来代替真实的数据库进行单元测试，极大地提高了测试速度和隔离性；其次，它为未来替换索引后端（例如，使用其他数据库或文件格式）提供了架构上的可能性。

### 目标
1.  **扩展 `IndexStoreProtocol`**: 在 `stitcher-spec/src/stitcher/spec/storage.py` 中，为 `IndexStoreProtocol` 添加索引器所需的写、同步和元数据管理方法。
2.  **重构 `FileIndexer`**: 修改 `stitcher-index/src/stitcher/index/indexer.py`，使其 `__init__` 方法的 `store` 参数类型注解从具体的 `IndexStore` 更改为 `IndexStoreProtocol`。
3.  **确保兼容性**: 验证 `StitcherApp` (`core.py`) 中 `FileIndexer` 的实例化代码依然有效，因为具体的 `IndexStore` 实例满足扩展后的协议。

### 基本原理
此重构严格遵循依赖倒置原则（DIP）。高层策略（`FileIndexer` 的索引逻辑）不应依赖于底层细节（`IndexStore` 的 SQLite 实现），两者都应依赖于抽象 (`IndexStoreProtocol`)。通过扩展协议来满足 `FileIndexer` 的契约，我们完成了这一倒置，使得索引的核心逻辑与数据库实现完全分离。

### 标签
#intent/refine #flow/ready #priority/high #comp/interfaces #comp/index #scope/core #ai/instruct #task/domain/architecture #task/object/protocols #task/action/purify #task/state/continue

---

### Script

#### Acts 1: 扩展 IndexStoreProtocol

我们将向 `stitcher-spec` 中的 `IndexStoreProtocol` 添加 `FileIndexer` 所需的方法，使其成为一个完整的存储抽象。

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/storage.py
~~~~~
~~~~~python.old
from typing import Protocol, List, Optional, Tuple

from .index import SymbolRecord, ReferenceRecord


class IndexStoreProtocol(Protocol):
    def get_symbols_by_file_path(self, file_path: str) -> List[SymbolRecord]: ...

    def find_symbol_by_fqn(
        self, target_fqn: str
    ) -> Optional[Tuple[SymbolRecord, str]]: ...

    def find_references(self, target_fqn: str) -> List[Tuple[ReferenceRecord, str]]: ...
~~~~~
~~~~~python.new
from typing import Protocol, List, Optional, Tuple

from .index import FileRecord, SymbolRecord, ReferenceRecord


class IndexStoreProtocol(Protocol):
    # --- Read Operations ---
    def get_symbols_by_file_path(self, file_path: str) -> List[SymbolRecord]: ...

    def find_symbol_by_fqn(
        self, target_fqn: str
    ) -> Optional[Tuple[SymbolRecord, str]]: ...

    def find_references(self, target_fqn: str) -> List[Tuple[ReferenceRecord, str]]: ...

    def get_all_files_metadata(self) -> List[FileRecord]: ...

    # --- Write/Sync Operations ---
    def sync_file(
        self, path: str, content_hash: str, mtime: float, size: int
    ) -> Tuple[int, bool]: ...

    def update_analysis(
        self,
        file_id: int,
        symbols: List[SymbolRecord],
        references: List[ReferenceRecord],
    ) -> None: ...

    def delete_file(self, file_id: int) -> None: ...
~~~~~

#### Acts 2: 更新 FileIndexer 的依赖

现在，我们将 `FileIndexer` 对具体 `IndexStore` 类的依赖，切换为对 `IndexStoreProtocol` 协议的依赖。

~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/indexer.py
~~~~~
~~~~~python.old
from typing import Dict, Set, Any

from .store import IndexStore
from stitcher.spec.index import FileRecord
from stitcher.spec.registry import LanguageAdapter
from .linker import Linker

log = logging.getLogger(__name__)


class FileIndexer:
    def __init__(self, root_path: Path, store: IndexStore):
        self.root_path = root_path
        self.store = store
        self.adapters: Dict[str, LanguageAdapter] = {}
        self.linker = Linker(store.db)

    def register_adapter(self, extension: str, adapter: LanguageAdapter):
~~~~~
~~~~~python.new
import hashlib
import logging
from pathlib import Path
from typing import Dict, Set, Any

from stitcher.spec import IndexStoreProtocol
from stitcher.spec.index import FileRecord
from stitcher.spec.registry import LanguageAdapter
from .linker import Linker

log = logging.getLogger(__name__)


class FileIndexer:
    def __init__(self, root_path: Path, store: IndexStoreProtocol):
        self.root_path = root_path
        self.store = store
        self.adapters: Dict[str, LanguageAdapter] = {}
        # FIXME: Linker still depends on the concrete DB manager. This will be addressed
        # in a subsequent refactoring task. For now, we assume the provided store
        # has a 'db' attribute if it's the concrete IndexStore.
        self.linker = Linker(getattr(store, "db", None))

    def register_adapter(self, extension: str, adapter: LanguageAdapter):
~~~~~

### 下一步建议
我们已经成功地将 `FileIndexer` 的依赖切换到了协议。然而，在实现过程中我们发现了一个新的依赖泄漏：`FileIndexer` 内部的 `Linker` 组件仍然直接依赖于 `DatabaseManager`。

下一步，我们应该将 `Linker` 的逻辑也抽象出来，或者将其功能合并到 `IndexStoreProtocol` 中（例如，添加一个 `store.link_unresolved()` 方法），从而彻底消除 `stitcher-index` 内部对数据库连接对象的直接依赖。
