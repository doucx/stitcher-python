根据分析，将 `Linker` 的职责下沉到 `IndexStore` 是最符合依赖倒置原则的方案。

**分析结论**:
1.  **领域归属**: “链接（Linking）”本质上是索引数据的一致性维护操作。具体的存储后端（如 SQLite）最知道如何高效地执行这种批量更新（如使用 SQL JOIN 更新）。因此，这是 `IndexStore` 的一种固有能力，而非外部逻辑。
2.  **解耦收益**: 将链接逻辑隐藏在 `IndexStoreProtocol` 之后，`FileIndexer` 就不再需要知道“链接器”的存在，也不需要持有数据库连接。这使得我们可以在单元测试中轻松 Mock 掉整个存储层，而无需模拟复杂的 SQL 链接过程。

**实施方案**:
1.  **协议层**: 在 `IndexStoreProtocol` 中增加 `resolve_missing_links()` 方法。
2.  **实现层**: 在 `IndexStore` 中实现该方法，由它在内部调用 `Linker`（或直接执行 SQL）。
3.  **调用层**: 修改 `FileIndexer`，移除 `Linker` 属性，改为调用 `self.store.resolve_missing_links()`。

## [WIP] refactor: 将 Linker 职责下沉至 IndexStore 以实现完全解耦

### 用户需求
目前 `FileIndexer` 直接实例化并使用 `Linker`，这导致它必须访问底层的 `DatabaseManager` (通过 `getattr(store, "db")` 这种临时 hack)。用户希望消除这种对实现细节的依赖，将链接逻辑抽象为 `IndexStore` 的一部分。

### 评论
这是一个非常清晰的重构。通过这次修改，`FileIndexer` 将变成一个纯粹的编排器：它读取文件 -> 解析 -> 传给 Store -> 要求 Store 整理数据。它不再关心数据是如何存储或如何建立关联的。这使得 `FileIndexer` 变得极易测试且完全符合 DIP 原则。

### 目标
1.  **更新 Protocol**: 在 `IndexStoreProtocol` 中添加 `resolve_missing_links` 接口。
2.  **增强 Store**: 在 `IndexStore` 中实现该接口，封装 `Linker` 的调用。
3.  **净化 Indexer**: 从 `FileIndexer` 中彻底移除 `Linker` 和 `DatabaseManager` 的痕迹。

### 基本原理
**单一职责原则 (SRP)** 和 **高内聚**: 数据的一致性维护（链接）应与数据存储紧密结合。
**依赖倒置原则 (DIP)**: `FileIndexer` 只应依赖于抽象的存储能力，而不是具体的 SQL 维护工具。

### 标签
#intent/refine #flow/ready #priority/high #comp/interfaces #comp/index #scope/core #ai/instruct #task/domain/architecture #task/object/linker #task/action/absorb #task/state/continue

---

### Script

#### Acts 1: 更新 IndexStoreProtocol

在协议中增加链接能力。

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/storage.py
~~~~~
~~~~~python.old
    def update_analysis(
        self,
        file_id: int,
        symbols: List[SymbolRecord],
        references: List[ReferenceRecord],
    ) -> None: ...

    def delete_file(self, file_id: int) -> None: ...
~~~~~
~~~~~python.new
    def update_analysis(
        self,
        file_id: int,
        symbols: List[SymbolRecord],
        references: List[ReferenceRecord],
    ) -> None: ...

    def delete_file(self, file_id: int) -> None: ...

    def resolve_missing_links(self) -> None: ...
~~~~~

#### Acts 2: 在 IndexStore 中实现链接逻辑

我们将 `Linker` 作为 `IndexStore` 的内部实现细节使用。

~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/store.py
~~~~~
~~~~~python.old
from typing import Optional, List, Tuple
from .db import DatabaseManager
from stitcher.spec.index import FileRecord, SymbolRecord, ReferenceRecord


class IndexStore:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def sync_file(
        self, path: str, content_hash: str, mtime: float, size: int
~~~~~
~~~~~python.new
from typing import Optional, List, Tuple
from .db import DatabaseManager
from .linker import Linker
from stitcher.spec.index import FileRecord, SymbolRecord, ReferenceRecord


class IndexStore:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self._linker = Linker(db_manager)

    def resolve_missing_links(self) -> None:
        self._linker.link()

    def sync_file(
        self, path: str, content_hash: str, mtime: float, size: int
~~~~~

#### Acts 3: 净化 FileIndexer

移除 `Linker` 的实例化和 Hack 代码，改用 `store` 的方法。

~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/indexer.py
~~~~~
~~~~~python.old
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
        self.adapters[extension] = adapter

    def index_files(self, discovered_paths: Set[str]) -> Dict[str, Any]:
        stats: Dict[str, Any] = {
~~~~~
~~~~~python.new
from stitcher.spec import IndexStoreProtocol
from stitcher.spec.index import FileRecord
from stitcher.spec.registry import LanguageAdapter

log = logging.getLogger(__name__)


class FileIndexer:
    def __init__(self, root_path: Path, store: IndexStoreProtocol):
        self.root_path = root_path
        self.store = store
        self.adapters: Dict[str, LanguageAdapter] = {}

    def register_adapter(self, extension: str, adapter: LanguageAdapter):
        self.adapters[extension] = adapter

    def index_files(self, discovered_paths: Set[str]) -> Dict[str, Any]:
        stats: Dict[str, Any] = {
~~~~~

~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/indexer.py
~~~~~
~~~~~python.old
                stats["errors"] += 1
                stats["error_details"].append((str(abs_path), str(e)))

        # --- Linking ---
        self.linker.link()
        return stats

    def _process_file_content(
        self, file_id: int, abs_path: Path, content_bytes: bytes
    ) -> None:
~~~~~
~~~~~python.new
                stats["errors"] += 1
                stats["error_details"].append((str(abs_path), str(e)))

        # --- Linking ---
        self.store.resolve_missing_links()
        return stats

    def _process_file_content(
        self, file_id: int, abs_path: Path, content_bytes: bytes
    ) -> None:
~~~~~

### 下一步建议
现在 `FileIndexer` 已经完全与 SQLite 解耦。接下来的工作是解决“组合根”问题，即 Runner 内部硬编码实例化子组件的问题（如 `CheckRunner` 内部的 `CheckAnalyzer` 和 `CheckResolver`），将其改为通过构造函数注入或工厂模式创建。这将完成服务抽象化的最后一块拼图。
