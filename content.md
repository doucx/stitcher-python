# 📸 Snapshot Capture

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../pyneedle-pointer/src/needle/pointer/core.json  | 14 ++++----
 .../pyneedle-pointer/src/needle/pointer/set.json   |  6 ++--
 .../src/needle/operators/dict_operator.json        |  2 +-
 .../src/needle/operators/helpers/json_handler.json |  2 +-
 .../pyneedle-spec/src/needle/spec/protocols.json   | 14 ++++----
 .../src/stitcher/app/services/doc_manager.json     |  8 ++---
 .../src/stitcher/cli/commands/check.json           |  4 +--
 .../src/stitcher/cli/commands/pump.json            |  4 +--
 .../stitcher-cli/src/stitcher/cli/factories.json   |  5 +--
 .../stitcher-cli/src/stitcher/cli/interactive.json |  2 +-
 .../stitcher-cli/src/stitcher/cli/main.json        |  2 +-
 .../src/stitcher/common/adapters/yaml_adapter.json |  6 ++--
 .../src/stitcher/common/interfaces.json            |  6 ++--
 .../src/stitcher/common/messaging/bus.json         | 15 ++++----
 .../src/stitcher/spec/fingerprint.json             |  2 +-
 .../stitcher-spec/src/stitcher/spec/protocols.json |  2 +-
 .../src/stitcher/test_utils/bus.json               |  2 +-
 .../src/stitcher/test_utils/harness.json           |  2 +-
 .../src/stitcher/test_utils/workspace.json         | 10 +++---
 .../src/stitcher/adapter/python/griffe_parser.py   | 42 ++++++++++++++++------
 .../adapter/python/internal/stub_generator.py      |  4 +--
 .../tests/integration/test_griffe_resolution.py    | 26 +++++++-------
 .../tests/unit/test_griffe_parser.py               | 32 +++++++++--------
 .../tests/unit/test_stub_generator.py              | 10 +++---
 24 files changed, 124 insertions(+), 98 deletions(-)
```