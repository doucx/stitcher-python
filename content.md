# 📸 Snapshot Capture

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../src/needle/pointer/__init__.json               |  2 ++
 .../pyneedle-pointer/src/needle/pointer/core.json  |  8 ++++-
 .../pyneedle-pointer/src/needle/pointer/set.json   |  9 +++++-
 .../src/needle/operators/__init__.json             |  4 +++
 .../src/needle/operators/dict_operator.json        |  7 +++-
 .../src/needle/operators/fs_operator.json          | 10 +++++-
 .../src/needle/operators/helpers/json_handler.json |  7 +++-
 .../src/needle/operators/helpers/protocols.json    |  6 +++-
 .../src/needle/operators/i18n_factory.json         |  7 +++-
 .../src/needle/operators/overlay_operator.json     |  7 +++-
 .../pyneedle-runtime/src/needle/runtime.json       |  6 ++++
 .../pyneedle-spec/src/needle/spec/__init__.json    |  3 ++
 .../pyneedle-spec/src/needle/spec/protocols.json   |  7 +++-
 .../src/stitcher/app/__init__.json                 |  1 +
 .../src/stitcher/app/core.json                     | 37 +++++++++++++++++++++-
 .../src/stitcher/app/handlers/noop_handler.json    |  7 +++-
 .../src/stitcher/app/protocols.json                |  8 ++++-
 .../src/stitcher/app/runners/__init__.json         |  7 ++++
 .../src/stitcher/app/runners/check.json            | 21 +++++++++++-
 .../src/stitcher/app/runners/coverage.json         |  8 ++++-
 .../src/stitcher/app/runners/index.json            |  6 +++-
 .../src/stitcher/app/runners/init.json             | 11 ++++++-
 .../src/stitcher/app/runners/pump.json             | 26 ++++++++++++++-
 .../src/stitcher/app/runners/refactor.json         | 16 +++++++++-
 .../src/stitcher/app/runners/transform.json        | 10 +++++-
 .../src/stitcher/app/services/__init__.json        |  5 +++
 .../src/stitcher/app/services/differ.json          |  3 +-
 .../src/stitcher/app/services/doc_manager.json     | 20 +++++++++++-
 .../src/stitcher/app/services/merger.json          |  5 ++-
 .../src/stitcher/app/services/scanner.json         | 13 +++++++-
 ...
 114 files changed, 989 insertions(+), 99 deletions(-)
```