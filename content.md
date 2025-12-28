# 📸 Snapshot Capture

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../pyneedle-nexus/src/needle/nexus/loaders.json   |  13 ++
 .../pyneedle-nexus/src/needle/nexus/nexus.json     |  40 +++++
 .../src/needle/pointer/__init__.json               |   5 +
 .../pyneedle-pointer/src/needle/pointer/core.json  |  45 ++++++
 .../pyneedle-pointer/src/needle/pointer/set.json   |  17 ++
 .../pyneedle-spec/src/needle/spec/protocols.json   |  88 +++++++++++
 .../src/stitcher/app/core.json                     |  86 ++++++++++
 .../src/stitcher/app/handlers/noop_handler.json    |  11 ++
 .../src/stitcher/app/protocols.json                |  12 ++
 .../src/stitcher/app/services/doc_manager.json     |  58 +++++++
 .../stitcher/app/services/signature_manager.json   |  24 +++
 .../app/services/stub_package_manager.json         |  13 ++
 .../stitcher-cli/src/stitcher/cli/handlers.json    |   8 +
 .../stitcher-cli/src/stitcher/cli/main.json        |  32 ++++
 .../stitcher-cli/src/stitcher/cli/rendering.json   |   9 ++
 .../src/stitcher/common/__init__.json              |  11 ++
 .../src/stitcher/common/formatting.json            |  10 ++
 .../src/stitcher/common/messaging/bus.json         |  36 +++++
 .../src/stitcher/common/messaging/protocols.json   |   9 ++
 .../src/stitcher/config/loader.json                |  32 ++++
 .../src/stitcher/io/adapters/yaml_adapter.json     |  13 ++
 .../stitcher-io/src/stitcher/io/interfaces.json    |  13 ++
 .../src/stitcher/io/stub_generator.json            |  27 ++++
 .../src/stitcher/scanner/inspector.json            |  17 ++
 .../src/stitcher/scanner/parser.json               |  58 +++++++
 .../src/stitcher/scanner/transformer.json          |  71 +++++++++
 .../src/stitcher/spec/fingerprint.json             |  40 +++++
 .../stitcher-spec/src/stitcher/spec/models.json    | 176 +++++++++++++++++++++
 .../src/stitcher/test_utils/bus.json               |  40 +++++
 .../src/stitcher/test_utils/harness.json           |  45 ++++++
 ...
 39 files changed, 1155 insertions(+), 41 deletions(-)
```