# 📸 Snapshot Capture

### 💬 备注:
style: ruff and stitcher

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../src/stitcher/cli/commands/refactor.json        |  7 ++++++
 .../stitcher-cli/src/stitcher/cli/main.json        |  3 ++-
 .../src/stitcher/refactor/engine/planner.json      |  8 +++++++
 .../src/stitcher/refactor/migration/__init__.json  |  3 +++
 .../stitcher/refactor/migration/exceptions.json    |  8 +++++++
 .../src/stitcher/refactor/migration/loader.json    |  8 +++++++
 .../src/stitcher/refactor/migration/spec.json      | 26 ++++++++++++++++++++++
 .../src/stitcher/cli/commands/refactor.py          |  3 ---
 .../stitcher/cli/commands/refactor.stitcher.yaml   |  2 ++
 .../src/stitcher/refactor/engine/planner.py        |  3 ---
 .../stitcher/refactor/engine/planner.stitcher.yaml |  2 ++
 .../src/stitcher/refactor/migration/exceptions.py  |  4 ----
 .../refactor/migration/exceptions.stitcher.yaml    |  4 ++++
 .../src/stitcher/refactor/migration/loader.py      |  3 ---
 .../refactor/migration/loader.stitcher.yaml        |  2 ++
 .../src/stitcher/refactor/migration/spec.py        | 17 --------------
 .../stitcher/refactor/migration/spec.stitcher.yaml | 12 ++++++++++
 17 files changed, 84 insertions(+), 31 deletions(-)
```