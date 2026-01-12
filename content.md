# 📸 Snapshot Capture

### 💬 备注:
style: ruff and stitcher

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../src/stitcher/app/runners/check/analyzer.json   |  4 +-
 .../src/stitcher/app/runners/check/resolver.json   |  4 +-
 .../src/stitcher/app/runners/check/runner.json     |  4 +-
 .../src/stitcher/app/runners/check/subject.json    |  8 +--
 .../src/stitcher/app/runners/coverage.json         |  4 +-
 .../src/stitcher/app/runners/init.json             |  4 +-
 .../src/stitcher/app/runners/pump.json             |  4 +-
 .../src/stitcher/app/runners/refactor.json         |  4 +-
 .../src/stitcher/app/runners/transform.json        |  4 +-
 .../src/stitcher/refactor/engine/graph.json        |  4 +-
 .../stitcher-spec/src/stitcher/spec/managers.json  | 67 ++++++++++++++++++++++
 .../stitcher-spec/src/stitcher/spec/protocols.json | 16 ++++++
 .../stitcher-spec/src/stitcher/spec/storage.json   | 22 +++++++
 .../stitcher-spec/src/stitcher/spec/managers.py    |  8 ++-
 .../stitcher-spec/src/stitcher/spec/protocols.py   |  4 +-
 .../stitcher-spec/src/stitcher/spec/storage.py     | 26 ++-------
 .../src/stitcher/spec/storage.stitcher.yaml        | 12 ++++
 17 files changed, 152 insertions(+), 47 deletions(-)
```