# 📸 Snapshot Capture

### 💬 备注:
style: ruff and stitcher

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../src/stitcher/refactor/__init__.json            |  3 +
 .../src/stitcher/refactor/engine/__init__.json     |  3 +
 .../src/stitcher/refactor/engine/context.json      |  4 +
 .../src/stitcher/refactor/engine/graph.json        | 86 ++++++++++++++++++++
 .../src/stitcher/refactor/engine/transaction.json  | 91 ++++++++++++++++++++++
 .../src/stitcher/refactor/operations/base.json     |  8 ++
 .../refactor/operations/rename_symbol.json         | 17 ++++
 .../operations/transforms/rename_transformer.json  | 27 +++++++
 .../src/stitcher/refactor/sidecar/updater.json     | 28 +++++++
 .../src/stitcher/refactor/__init__.py              |  2 +-
 .../src/stitcher/refactor/engine/__init__.py       |  2 +-
 .../src/stitcher/refactor/engine/context.py        |  2 +-
 .../src/stitcher/refactor/engine/graph.py          | 77 +++++++++---------
 .../stitcher/refactor/engine/graph.stitcher.yaml   |  8 ++
 .../src/stitcher/refactor/engine/transaction.py    |  4 +-
 .../src/stitcher/refactor/operations/base.py       |  6 +-
 .../refactor/operations/base.stitcher.yaml         |  3 +
 .../stitcher/refactor/operations/rename_symbol.py  | 56 ++++++++-----
 .../operations/transforms/rename_transformer.py    | 41 ++++------
 .../transforms/rename_transformer.stitcher.yaml    | 13 ++++
 .../src/stitcher/refactor/sidecar/updater.py       | 10 ++-
 .../tests/integration/test_rename_e2e.py           | 54 +++++++------
 .../test_rename_transformer_advanced.py            | 34 ++++----
 .../tests/integration/test_semantic_graph.py       | 11 ++-
 .../tests/integration/test_transaction_fs.py       |  2 +-
 .../tests/integration/test_usage_registry.py       | 41 +++++-----
 .../tests/unit/test_rename_operation.py            | 33 ++++----
 .../tests/unit/test_rename_transformer.py          | 24 +++---
 .../tests/unit/test_transaction.py                 |  4 +-
 29 files changed, 495 insertions(+), 199 deletions(-)
```