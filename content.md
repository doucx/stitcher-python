# 📸 Snapshot Capture

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../src/stitcher/cli/commands/refactor.py          | 17 ++++++-----
 packages/stitcher-cli/src/stitcher/cli/main.py     |  4 ++-
 .../tests/integration/test_refactor_command.py     | 11 +++-----
 .../src/stitcher/refactor/engine/planner.py        |  2 +-
 .../src/stitcher/refactor/migration/__init__.py    |  2 +-
 .../src/stitcher/refactor/migration/exceptions.py  |  5 +++-
 .../src/stitcher/refactor/migration/loader.py      | 18 ++++++++----
 .../src/stitcher/refactor/migration/spec.py        |  7 ++---
 .../tests/unit/engine/test_planner.py              |  2 +-
 .../tests/unit/migration/__init__.py               |  2 +-
 .../tests/unit/migration/test_loader.py            |  2 +-
 .../tests/unit/migration/test_spec.py              | 33 +++++++++-------------
 12 files changed, 53 insertions(+), 52 deletions(-)
```