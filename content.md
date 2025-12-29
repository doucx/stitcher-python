# 📸 Snapshot Capture

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../src/stitcher/cli/commands/pump.json            |  4 +-
 .../pyneedle-nexus/src/needle/nexus/__init__.py    |  2 +-
 .../pyneedle-nexus/src/needle/nexus/operators.py   |  5 +--
 .../pyneedle-nexus/tests/test_overlay_operator.py  | 43 +++++++++++-----------
 .../src/needle/operators/__init__.py               |  2 +-
 .../src/needle/operators/dict_operator.py          | 11 +++---
 .../src/needle/operators/fs_operator.py            |  5 +--
 .../src/needle/operators/i18n_factory.py           | 15 ++++----
 packages/pyneedle-runtime/tests/test_operators.py  | 17 +++++----
 .../tests/test_pipeline_integration.py             | 30 +++++++--------
 .../pyneedle-spec/src/needle/spec/protocols.py     |  4 +-
 .../stitcher-cli/src/stitcher/cli/commands/pump.py |  4 +-
 packages/stitcher-cli/src/stitcher/cli/main.py     |  4 +-
 .../src/stitcher/common/__init__.py                | 13 ++++---
 .../src/stitcher/common/messaging/bus.py           |  4 +-
 .../src/stitcher/test_utils/bus.py                 | 16 ++++----
 16 files changed, 84 insertions(+), 95 deletions(-)
```