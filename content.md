# 📸 Snapshot Capture

### 💬 备注:
style: ruff and stitcher

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../src/stitcher/common/messaging/bus.json         | 24 +++++++--------
 .../src/stitcher/refactor/engine/graph.json        | 12 ++++++--
 .../refactor/operations/rename_symbol.json         |  9 ++++++
 001_rename_message_bus.py                          |  3 +-
 .../src/stitcher/cli/commands/refactor.py          |  4 +--
 .../src/stitcher/common/__init__.py                |  4 +--
 .../src/stitcher/common/messaging/bus.py           |  2 +-
 .../stitcher/common/messaging/bus.stitcher.yaml    | 18 +++++------
 .../stitcher/refactor/operations/rename_symbol.py  |  7 +----
 .../operations/rename_symbol.stitcher.yaml         |  4 +++
 .../src/stitcher/refactor/workspace.py             | 10 +++++--
 .../tests/integration/test_debug_rename_failure.py | 35 +++++++++-------------
 .../test_rename_namespace_pkg_failure.py           | 33 ++++++++++----------
 .../integration/test_rename_symbol_definition.py   |  8 +++--
 .../tests/unit/refactor/test_pep420_discovery.py   | 22 +++++++++-----
 .../unit/refactor/test_workspace_filtering.py      | 25 +++++-----------
 16 files changed, 119 insertions(+), 101 deletions(-)
```