# 📸 Snapshot Capture

### 💬 备注:
style: ruff and stitcher

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../packages/stitcher-common/src/stitcher/common/__init__.json   | 2 +-
 .../stitcher-refactor/src/stitcher/refactor/operations/base.json | 9 +++++++++
 .../src/stitcher/refactor/operations/rename_symbol.json          | 4 ++++
 .../stitcher-refactor/src/stitcher/refactor/operations/base.py   | 5 ++---
 .../src/stitcher/refactor/operations/move_file.py                | 8 ++++++--
 .../src/stitcher/refactor/operations/move_file.stitcher.yaml     | 3 ---
 .../src/stitcher/refactor/operations/rename_symbol.py            | 6 ++----
 .../src/stitcher/refactor/operations/rename_symbol.stitcher.yaml | 4 ----
 .../tests/unit/operations/test_sidecar_update_mixin.py           | 2 +-
 packages/stitcher-refactor/tests/unit/test_rename_operation.py   | 2 +-
 10 files changed, 26 insertions(+), 19 deletions(-)
```