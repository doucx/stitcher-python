# 📸 Snapshot Capture

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../pyneedle-nexus/src/needle/nexus/operators.json | 15 ++++++++
 .../src/needle/operators/dict_operator.json        | 19 ++++++++++
 .../src/needle/operators/fs_operator.json          | 23 ++++++++++++
 .../src/needle/operators/helpers/json_handler.json | 22 ++++++++++++
 .../src/needle/operators/helpers/protocols.json    | 14 ++++++++
 .../src/needle/operators/i18n_factory.json         | 15 ++++++++
 .../pyneedle-spec/src/needle/spec/protocols.json   | 41 ++++------------------
 .../stitcher/app/services/signature_manager.json   |  3 --
 .../src/stitcher/cli/commands/pump.json            |  4 +--
 .../stitcher-cli/src/stitcher/cli/interactive.json |  4 +--
 .../stitcher-cli/src/stitcher/cli/main.json        |  4 +--
 .../src/stitcher/common/__init__.json              | 16 ++++++---
 .../src/stitcher/common/messaging/bus.json         |  6 ++--
 .../stitcher-spec/src/stitcher/spec/models.json    |  6 ----
 .../pyneedle-nexus/src/needle/nexus/operators.py   |  4 ---
 .../src/needle/nexus/operators.stitcher.yaml       |  8 ++---
 .../src/needle/operators/dict_operator.py          |  4 ---
 .../needle/operators/dict_operator.stitcher.yaml   |  7 ++--
 .../src/needle/operators/fs_operator.py            |  8 -----
 .../src/needle/operators/fs_operator.stitcher.yaml | 11 +++---
 .../src/needle/operators/i18n_factory.py           |  6 ----
 .../needle/operators/i18n_factory.stitcher.yaml    | 11 +++---
 .../pyneedle-spec/src/needle/spec/protocols.py     |  5 ---
 .../src/needle/spec/protocols.stitcher.yaml        | 13 +++----
 .../src/stitcher/common/__init__.py                |  4 ---
 .../src/stitcher/common/__init__.stitcher.yaml     |  5 ++-
 26 files changed, 160 insertions(+), 118 deletions(-)
```