# 📸 Snapshot Capture

### 💬 备注:
ruff and stitcher

检测到工作区发生变更。

### 📝 变更文件摘要:
```
conftest.py                                        |  2 +-
 .../stitcher-application/src/stitcher/app/core.py  |  4 --
 .../src/stitcher/app/core.stitcher.yaml            |  5 +-
 .../src/stitcher/app/runners/check/resolver.py     | 20 ++----
 .../app/runners/check/resolver.stitcher.yaml       |  1 +
 .../src/stitcher/app/runners/pump/executor.py      |  5 +-
 .../src/stitcher/app/services/lock_session.py      | 33 ---------
 .../app/services/lock_session.stitcher.yaml        |  7 ++
 packages/stitcher-application/stitcher.lock        | 80 +++++++++++++++++-----
 .../integration/test_check_ignores_imports.py      |  5 +-
 .../integration/test_check_ignores_reexports.py    |  5 +-
 .../integration/test_init_sidecar_idempotency.py   |  2 +-
 .../tests/integration/test_loglevel_option.py      |  2 +-
 .../tests/integration/test_indexer_aliases.py      |  4 +-
 ...est_refactor_move_updates_suri_in_signatures.py |  5 +-
 15 files changed, 95 insertions(+), 85 deletions(-)
```