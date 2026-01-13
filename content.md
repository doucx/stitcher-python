我将立刻执行这个经过修正的、符合高保真工程公理的计划。首先，我们将修改数据库 Schema，这是解锁后续所有重构工作的关键第一步。

## [WIP] refactor: Evolve index schema to support identity-based references

### 用户需求

为了从根本上解决 Refactor 引擎与 Index 数据库之间的“阻抗失配”问题，需要修改 Index 的核心 Schema。具体而言，`references` 表必须支持“身份引用 (by-id)”（例如，通过 SURI），而不仅仅是“名称引用 (by-name)”（通过 FQN）。

### 评论

这是一个至关重要的架构简化。通过将 `references` 表中的 `target_fqn` 字段从强制（`NOT NULL`）修改为可选，我们承认了 SURI 本身就是一种合法的、一等公民的引用标识符。这一改动将允许我们消除脆弱且复杂的应用层逻辑（如 `SidecarUpdateMixin`），使重构引擎的查询模型更加统一、健壮和符合逻辑。

### 目标

1.  定位 `stitcher-index` 包中的 `schema.sql` 文件。
2.  修改 `references` 表的定义，将 `target_fqn` 列的 `NOT NULL` 约束移除。

### 基本原理

当前的 `NOT NULL` 约束强制所有引用都必须是基于名称的。然而，Sidecar 文件（特别是 Signature JSON）使用 SURI 作为键，这本质上是基于身份的引用。当索引这类文件时，我们应该直接存储 SURI (`target_id`) 而非强制反解一个可能不存在或不稳定的 FQN。将 `target_fqn` 设为可空（`NULLABLE`），可以使索引器能够原生存储这两种引用类型，从而统一数据模型，为后续真正基于身份的重构查询（`WHERE target_id = ?`）奠定基础。

### 标签

#intent/architect #intent/refine #flow/ready #priority/critical #comp/index #concept/state #scope/core #ai/brainstorm #task/domain/storage #task/object/db-schema #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: 修改 schema.sql

我们将修改 `references` 表定义，允许 `target_fqn` 字段为空。

~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/schema.sql
~~~~~
~~~~~text.old
    -- The logical FQN of the target, extracted by the parser.
    -- e.g., "os.path.join"
    target_fqn TEXT NOT NULL,
    
    -- The resolved SURI of the target symbol (FK to symbols.id).
~~~~~
~~~~~text.new
    -- The logical FQN of the target, extracted by the parser.
    -- e.g., "os.path.join"
    -- This can be NULL for references that are purely by ID (e.g. SURI in signatures).
    target_fqn TEXT,
    
    -- The resolved SURI of the target symbol (FK to symbols.id).
~~~~~

### 下一步建议

Schema 已经演进。现在，我们需要一个 Adapter 来利用这个新能力。

下一步是**创建一个新的语言适配器 `stitcher-lang-sidecar`**。这个适配器的唯一职责就是解析 `.stitcher.yaml` 和 `.json` (signature) 文件，并将它们的内容（特别是 Signature 文件中以 SURI 为键的条目）转换为 `SymbolRecord` 和 `ReferenceRecord`，然后送入索引。

这将是我们数据流入新模型的关键管道。如果你同意，我将开始制定创建这个新包的计划。
