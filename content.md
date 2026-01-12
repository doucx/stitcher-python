# 📸 Snapshot Capture

### 💬 备注:
style: ruff and stitcher

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../src/stitcher/refactor/engine/intent.json       |  2 +
 .../src/stitcher/refactor/operations/base.json     |  4 +-
 .../stitcher-application/src/stitcher/app/core.py  |  4 +-
 .../src/stitcher/app/runners/coverage.py           |  4 --
 .../src/stitcher/refactor/engine/intent.py         |  2 +-
 .../src/stitcher/refactor/engine/planner.py        |  2 +-
 .../src/stitcher/refactor/operations/base.py       |  2 +-
 .../stitcher/refactor/operations/move_directory.py | 14 +++++--
 .../src/stitcher/refactor/operations/move_file.py  |  4 +-
 ...est_refactor_move_updates_suri_in_signatures.py | 23 ++++++-----
 scripts/profile_stitcher.py                        | 48 ++++++++++++++--------
 11 files changed, 67 insertions(+), 42 deletions(-)
```