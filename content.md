# 📸 Snapshot Capture

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../src/stitcher/app/core.json                     | 26 +++++++----
 .../src/stitcher/app/handlers/noop_handler.json    |  3 +-
 .../src/stitcher/app/protocols.json                | 23 +++++++---
 .../src/stitcher/app/services/differ.json          |  3 +-
 .../src/stitcher/app/services/doc_manager.json     | 50 +++++++++++++++-------
 .../src/stitcher/app/services/merger.json          |  3 +-
 .../stitcher/app/services/signature_manager.json   | 13 ++++--
 .../src/stitcher/cli/commands/basics.json          | 12 ++++--
 .../src/stitcher/cli/commands/check.json           |  3 +-
 .../src/stitcher/cli/commands/pump.json            |  3 +-
 .../src/stitcher/cli/commands/refactor.json        |  3 +-
 .../stitcher-cli/src/stitcher/cli/factories.json   |  9 ++--
 .../stitcher-cli/src/stitcher/cli/handlers.json    |  7 ++-
 .../stitcher-cli/src/stitcher/cli/interactive.json | 29 +++++++++----
 .../stitcher-cli/src/stitcher/cli/main.json        |  7 ++-
 .../stitcher-cli/src/stitcher/cli/rendering.json   |  7 ++-
 .../src/stitcher/common/__init__.json              | 10 +++--
 .../src/stitcher/common/adapters/yaml_adapter.json |  9 ++--
 .../src/stitcher/common/formatting.json            |  6 ++-
 .../src/stitcher/common/interfaces.json            |  6 ++-
 .../src/stitcher/common/messaging/bus.json         | 24 +++++++----
 .../src/stitcher/common/messaging/protocols.json   |  3 +-
 .../common/services/asset_path_resolver.json       |  6 ++-
 .../src/stitcher/common/transaction.json           |  3 +-
 .../src/stitcher/config/loader.json                | 29 +++++++++----
 .../stitcher-index/src/stitcher/index/db.json      |  6 ++-
 .../stitcher-index/src/stitcher/index/linker.json  |  3 +-
 .../src/stitcher/index/protocols.json              |  3 +-
 .../stitcher-index/src/stitcher/index/store.json   | 18 +++++---
 .../stitcher/adapter/python/docstring/factory.json |  6 ++-
 ...
 54 files changed, 518 insertions(+), 220 deletions(-)
```