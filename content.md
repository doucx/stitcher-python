# 📸 Snapshot Capture

### 💬 备注:
style: ruff and stitcher

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../src/stitcher/app/runners/check/protocols.json  | 32 +++++++++
 .../src/stitcher/app/runners/check/runner.json     |  4 +-
 .../src/stitcher/app/runners/pump/__init__.json    |  3 +
 .../src/stitcher/app/runners/pump/analyzer.json    | 22 ++++++
 .../src/stitcher/app/runners/pump/executor.json    | 32 +++++++++
 .../src/stitcher/app/runners/pump/protocols.json   | 18 +++++
 .../src/stitcher/app/runners/pump/runner.json      | 17 +++++
 .../src/stitcher/app/services/doc_manager.json     | 12 ++++
 .../stitcher/app/services/signature_manager.json   |  4 ++
 .../stitcher-index/src/stitcher/index/indexer.json |  4 +-
 .../stitcher-index/src/stitcher/index/store.json   |  5 ++
 .../stitcher-spec/src/stitcher/spec/managers.json  | 16 +++++
 .../stitcher-spec/src/stitcher/spec/storage.json   | 20 ++++++
 .../src/stitcher/app/runners/check/protocols.py    |  2 +-
 .../src/stitcher/app/runners/check/runner.py       |  1 -
 .../src/stitcher/app/runners/check/subject.py      |  3 +-
 .../src/stitcher/app/runners/pump/__init__.py      |  2 +-
 .../src/stitcher/app/runners/pump/analyzer.py      | 12 ++--
 .../src/stitcher/app/runners/pump/executor.py      | 80 ++++++++++++++++------
 .../src/stitcher/app/runners/pump/protocols.py     |  7 +-
 .../src/stitcher/app/runners/pump/runner.py        |  2 +-
 .../tests/unit/test_execution_planner.py           |  2 +-
 .../stitcher-index/src/stitcher/index/indexer.py   |  3 -
 23 files changed, 254 insertions(+), 49 deletions(-)
```