Excellent. Your revised SURI-driven approach is architecturally superior. I will now generate the plan to update the database schema as the first step in implementing this Zero-IO architecture.

## [WIP] feat: Extend database schema with doc_entries table

### 用户需求

The user requires an update to the `index.db` schema to include a new table, `doc_entries`, for indexing the content of `.stitcher.yaml` (Sidecar) files. This table must use the symbol's SURI (`symbol_id`) as the primary link to the `symbols` table, avoiding the use of FQNs for this purpose.

### 评论

This is a critical and correct architectural decision. By indexing Sidecar content and linking it via the stable SURI, we establish the foundation for a 'Zero-IO' read path for commands like `stitcher check`. This moves the expensive YAML parsing to the infrequent write path (indexing) and leverages the high performance of SQLite for the frequent read path (checking), directly addressing the identified performance bottleneck.

### 目标

Modify the `packages/stitcher-index/src/stitcher/index/schema.sql` file to add the new `doc_entries` table and its associated index, as per the agreed-upon SURI-driven design.

### 基本原理

The most direct and atomic way to achieve this is by using `patch_file` to append the new table definition to the existing `schema.sql`. This ensures the change is explicit and contained within a single operation. The new table definition includes a foreign key to `files(id)` for physical location tracking and a `TEXT` key (`symbol_id`) for linking to `symbols(id)`, preparing for high-performance JOINs.

### 标签

#intent/build #flow/ready #priority/high #comp/index #concept/state #scope/core #ai/brainstorm #task/domain/storage #task/object/sidecar-index #task/action/implementation #task/state/begin #task/status/active

---

### Script

#### Acts 1: Append doc_entries table definition to schema.sql

We will append the new table and index definitions to the end of the schema file.

~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/schema.sql
~~~~~
~~~~~sql.old
CREATE INDEX IF NOT EXISTS idx_references_source_file_id ON 'references'(source_file_id);
CREATE INDEX IF NOT EXISTS idx_references_target_id ON 'references'(target_id);
~~~~~
~~~~~sql.new
CREATE INDEX IF NOT EXISTS idx_references_source_file_id ON 'references'(source_file_id);
CREATE INDEX IF NOT EXISTS idx_references_target_id ON 'references'(target_id);


-- Document Entries from Sidecar (.stitcher.yaml) files
CREATE TABLE IF NOT EXISTS doc_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,          -- FK to the .stitcher.yaml file in the 'files' table
    symbol_id TEXT NOT NULL,           -- The SURI of the symbol this doc belongs to (e.g., 'py://path/to/file.py#symbol')
    content_hash TEXT NOT NULL,        -- Hash of the DocstringIR content for quick comparisons
    ir_data_json TEXT,                 -- The full DocstringIR, serialized as JSON for fast hydration
    lineno INTEGER,                    -- Line number in the YAML file for error reporting
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_doc_entries_symbol_id ON doc_entries(symbol_id);
~~~~~

### 下一步建议

The database schema is now prepared. The next logical step is to create a `SidecarAdapter` within the `stitcher-lang-sidecar` package. This adapter will be responsible for:

1.  Recognizing `.stitcher.yaml` files.
2.  Parsing them using `ruamel.yaml`.
3.  Generating the SURI for each documentation entry by combining the source file's path with the YAML key (fragment).
4.  Producing a list of records ready to be inserted into the new `doc_entries` table.

Once this adapter is built, we can integrate it into the main `FileIndexer`.
