# 📸 Snapshot Capture

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../pyneedle-nexus/src/needle/nexus/base.json      |  5 +++++
 .../pyneedle-nexus/src/needle/nexus/loaders.json   |  3 +++
 .../pyneedle-nexus/src/needle/nexus/nexus.json     |  8 ++++++++
 .../pyneedle-pointer/src/needle/pointer/core.json  | 11 +++++++++++
 .../pyneedle-pointer/src/needle/pointer/set.json   |  3 +++
 .../src/needle/loaders/fs_loader.json              | 10 ++++++++++
 .../src/needle/loaders/json_handler.json           |  5 +++++
 .../src/needle/loaders/protocols.json              |  3 +++
 .../pyneedle-runtime/src/needle/runtime.json       |  1 +
 .../pyneedle-spec/src/needle/spec/protocols.json   | 18 +++++++++++++++++
 .../src/stitcher/app/core.json                     | 23 ++++++++++++++++++++++
 .../src/stitcher/app/handlers/noop_handler.json    |  2 ++
 .../src/stitcher/app/protocols.json                |  1 +
 .../src/stitcher/app/services/doc_manager.json     | 14 +++++++++++++
 .../stitcher/app/services/signature_manager.json   |  9 +++++++++
 .../app/services/stub_package_manager.json         |  2 ++
 .../src/stitcher/cli/commands/basics.json          | 18 +++++++++++++++++
 .../src/stitcher/cli/commands/check.json           |  6 ++++++
 .../src/stitcher/cli/commands/pump.json            |  6 ++++++
 .../stitcher-cli/src/stitcher/cli/factories.json   | 16 +++++++++++++++
 .../stitcher-cli/src/stitcher/cli/handlers.json    |  2 ++
 .../stitcher-cli/src/stitcher/cli/interactive.json |  4 ++++
 .../stitcher-cli/src/stitcher/cli/main.json        |  7 +------
 .../stitcher-cli/src/stitcher/cli/rendering.json   |  2 ++
 .../src/stitcher/common/formatting.json            |  2 ++
 .../src/stitcher/common/messaging/bus.json         |  9 +++++++++
 .../src/stitcher/common/messaging/protocols.json   |  1 +
 .../src/stitcher/config/loader.json                |  3 +++
 .../src/stitcher/io/adapters/yaml_adapter.json     |  2 ++
 .../stitcher-io/src/stitcher/io/interfaces.json    |  2 ++
 ...
 45 files changed, 288 insertions(+), 18 deletions(-)
```