# 📸 Snapshot Capture

### 💬 备注:
style: ruff and stitcher

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../src/needle/pointer/__init__.json               |  4 +-
 .../pyneedle-pointer/src/needle/pointer/core.json  | 25 ++----
 .../pyneedle-pointer/src/needle/pointer/set.json   | 13 +--
 .../src/needle/operators/dict_operator.json        | 10 +--
 .../src/needle/operators/fs_operator.json          | 10 +--
 .../src/needle/operators/i18n_factory.json         | 10 +--
 .../src/needle/operators/overlay_operator.json     | 10 +--
 .../pyneedle-runtime/src/needle/runtime.json       |  4 +-
 .../pyneedle-spec/src/needle/spec/protocols.json   | 55 ++++--------
 .../src/stitcher/app/core.json                     | 98 ++--------------------
 .../src/stitcher/app/handlers/noop_handler.json    |  7 +-
 .../src/stitcher/app/protocols.json                | 31 ++-----
 .../src/stitcher/app/runners/check.json            | 28 +++----
 .../src/stitcher/app/runners/coverage.json         |  9 --
 .../src/stitcher/app/runners/index.json            |  2 -
 .../src/stitcher/app/runners/init.json             |  5 --
 .../src/stitcher/app/runners/pump.json             | 10 ---
 .../src/stitcher/app/runners/transform.json        |  5 --
 .../src/stitcher/app/services/differ.json          |  7 +-
 .../src/stitcher/app/services/doc_manager.json     | 57 ++++---------
 .../src/stitcher/app/services/merger.json          |  7 +-
 .../stitcher/app/services/signature_manager.json   | 35 ++------
 .../src/stitcher/cli/commands/basics.json          | 12 +--
 .../src/stitcher/cli/commands/check.json           |  3 +-
 .../src/stitcher/cli/commands/pump.json            |  3 +-
 .../src/stitcher/cli/commands/refactor.json        |  3 +-
 .../stitcher-cli/src/stitcher/cli/factories.json   |  9 +-
 .../stitcher-cli/src/stitcher/cli/handlers.json    | 11 +--
 .../stitcher-cli/src/stitcher/cli/interactive.json | 37 +++-----
 .../stitcher-cli/src/stitcher/cli/main.json        |  7 +-
 ...
 85 files changed, 363 insertions(+), 1193 deletions(-)
```