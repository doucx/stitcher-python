# 📸 Snapshot Capture

### 💬 备注:
remove cache under .stitcher

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../stitcher-application/src/stitcher/app/core.json   | 12 ------------
 .../src/stitcher/app/services/doc_manager.json        | 13 -------------
 .../src/stitcher/app/services/signature_manager.json  |  8 --------
 .../stitcher-application/tests/test_doc_manager.json  |  8 --------
 .../stitcher-application/tests/test_doc_overlay.json  |  4 ----
 .../tests/test_signature_manager.json                 |  6 ------
 .../packages/stitcher-cli/src/stitcher/cli/main.json  |  8 --------
 .../stitcher-cli/src/stitcher/cli/rendering.json      |  3 ---
 .../src/stitcher/common/messaging/bus.json            | 10 ----------
 .../src/stitcher/common/messaging/protocols.json      |  3 ---
 .../stitcher-common/tests/test_message_bus.json       |  8 --------
 .../stitcher-config/src/stitcher/config/loader.json   |  5 -----
 .../packages/stitcher-config/tests/test_loader.json   |  4 ----
 .../src/stitcher/io/adapters/yaml_adapter.json        |  4 ----
 .../stitcher-io/src/stitcher/io/interfaces.json       |  4 ----
 .../stitcher-io/src/stitcher/io/stub_generator.json   | 10 ----------
 .../packages/stitcher-io/tests/test_document_io.json  |  6 ------
 .../stitcher-io/tests/test_stub_generator.json        |  3 ---
 .../stitcher-needle/src/stitcher/needle/handlers.json |  4 ----
 .../src/stitcher/needle/interfaces.json               |  4 ----
 .../stitcher-needle/src/stitcher/needle/loader.json   |  5 -----
 .../stitcher-needle/src/stitcher/needle/pointer.json  |  8 --------
 .../stitcher-needle/src/stitcher/needle/runtime.json  |  6 ------
 .../packages/stitcher-needle/tests/test_pointer.json  |  9 ---------
 .../packages/stitcher-needle/tests/test_runtime.json  |  3 ---
 .../src/stitcher/scanner/inspector.json               |  5 -----
 .../stitcher-scanner/src/stitcher/scanner/parser.json | 15 ---------------
 .../src/stitcher/scanner/transformer.json             | 19 -------------------
 .../stitcher-scanner/tests/test_inspector.json        |  4 ----
 .../stitcher-scanner/tests/test_parser_advanced.json  |  6 ------
 ...
 37 files changed, 253 deletions(-)
```