# 📸 Snapshot Capture

### 💬 备注:
style: ruff and stitcher

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../src/stitcher/app/core.json                     | 10 ++++++-
 .../src/stitcher/app/runners/index.json            | 13 ++++++++
 .../src/stitcher/cli/commands/index.json           |  6 ++++
 .../stitcher-cli/src/stitcher/cli/main.json        |  1 +
 .../src/stitcher/index/protocols.json              | 10 +++++++
 .../stitcher-index/src/stitcher/index/scanner.json | 31 +++++++++++++++++++
 .../stitcher-index/src/stitcher/index/store.json   | 10 +++++++
 .../src/stitcher/adapter/python/index_adapter.json | 22 ++++++++++++++
 .../src/stitcher/adapter/python/uri.json           | 20 +++++++++++++
 .../src/stitcher/test_utils/workspace.json         |  5 ++++
 .../stitcher-application/src/stitcher/app/core.py  |  4 +--
 .../src/stitcher/app/runners/index.py              |  4 +--
 .../src/stitcher/cli/commands/index.py             |  5 +---
 .../stitcher-index/src/stitcher/index/protocols.py | 15 +---------
 .../src/stitcher/index/protocols.stitcher.yaml     | 11 +++++++
 .../stitcher-index/src/stitcher/index/scanner.py   | 35 +++++++---------------
 .../src/stitcher/index/scanner.stitcher.yaml       | 12 ++++++++
 .../stitcher-index/src/stitcher/index/store.py     |  2 --
 .../src/stitcher/index/store.stitcher.yaml         |  4 +++
 packages/stitcher-index/tests/unit/test_scanner.py | 27 +++++++++--------
 .../src/stitcher/adapter/python/index_adapter.py   | 28 +++++++++--------
 .../src/stitcher/adapter/python/uri.py             | 17 +----------
 .../src/stitcher/adapter/python/uri.stitcher.yaml  | 12 ++++++++
 .../tests/test_index_adapter.py                    | 17 +++++------
 .../src/stitcher/test_utils/workspace.py           |  1 -
 .../stitcher/test_utils/workspace.stitcher.yaml    |  2 ++
 26 files changed, 223 insertions(+), 101 deletions(-)
```