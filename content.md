# 📸 Snapshot Capture

### 💬 备注:
style: ruff and stitcher

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../src/stitcher/common/adapters/yaml_adapter.json |  5 +++
 .../src/stitcher/refactor/engine/intent.json       | 38 ++++++++++++++++++++++
 .../src/stitcher/refactor/engine/renamer.json      | 13 ++++++++
 .../src/stitcher/refactor/engine/transaction.json  |  5 +++
 .../src/stitcher/refactor/operations/base.json     |  5 +++
 .../refactor/operations/move_directory.json        |  8 +++++
 .../stitcher/refactor/operations/move_file.json    |  8 +++++
 .../refactor/operations/rename_symbol.json         |  4 +++
 .../operations/transforms/rename_transformer.json  |  4 +++
 .../common/adapters/yaml_adapter.stitcher.yaml     |  2 +-
 .../src/stitcher/refactor/engine/graph.py          |  2 +-
 .../src/stitcher/refactor/engine/intent.py         | 20 ------------
 .../stitcher/refactor/engine/intent.stitcher.yaml  | 17 ++++++++++
 .../src/stitcher/refactor/engine/transaction.py    |  4 ---
 .../refactor/engine/transaction.stitcher.yaml      |  3 ++
 .../src/stitcher/refactor/operations/base.py       |  4 ---
 .../refactor/operations/base.stitcher.yaml         |  6 ++--
 .../operations/move_directory.stitcher.yaml        |  4 ---
 18 files changed, 115 insertions(+), 37 deletions(-)
```