# 📸 Snapshot Capture

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../src/stitcher/app/core.stitcher.yaml            | 13 -------------
 .../app/services/doc_manager.stitcher.yaml         | 22 ----------------------
 .../app/services/signature_manager.stitcher.yaml   | 17 -----------------
 .../tests/test_doc_manager.stitcher.yaml           | 11 -----------
 .../tests/test_doc_overlay.stitcher.yaml           |  4 ----
 .../tests/test_signature_manager.stitcher.yaml     |  7 -------
 .../src/stitcher/cli/main.stitcher.yaml            |  5 -----
 .../src/stitcher/cli/rendering.stitcher.yaml       |  1 -
 .../stitcher/common/messaging/bus.stitcher.yaml    |  2 --
 .../common/messaging/protocols.stitcher.yaml       |  9 ---------
 .../src/stitcher/config/loader.stitcher.yaml       |  4 ----
 .../tests/test_loader.stitcher.yaml                |  4 ----
 .../io/adapters/yaml_adapter.stitcher.yaml         |  1 -
 .../src/stitcher/io/interfaces.stitcher.yaml       | 20 --------------------
 .../src/stitcher/io/stub_generator.stitcher.yaml   |  1 -
 .../tests/test_document_io.stitcher.yaml           |  2 --
 .../src/stitcher/needle/handlers.stitcher.yaml     |  1 -
 .../src/stitcher/needle/interfaces.stitcher.yaml   |  3 ---
 .../src/stitcher/needle/loader.stitcher.yaml       |  3 ---
 .../src/stitcher/needle/pointer.stitcher.yaml      | 17 -----------------
 .../src/stitcher/needle/runtime.stitcher.yaml      | 11 -----------
 .../src/stitcher/scanner/inspector.stitcher.yaml   | 15 ---------------
 .../src/stitcher/scanner/parser.stitcher.yaml      |  4 ----
 .../src/stitcher/scanner/transformer.stitcher.yaml |  7 -------
 .../tests/test_inspector.stitcher.yaml             |  4 ----
 .../tests/test_parser_advanced.stitcher.yaml       |  4 ----
 .../tests/test_parser_imports.stitcher.yaml        |  6 ------
 .../tests/test_transformer.stitcher.yaml           |  2 --
 .../src/stitcher/spec/models.stitcher.yaml         | 10 ----------
 .../src/stitcher/test_utils/bus.stitcher.yaml      |  7 -------
 ...
 32 files changed, 232 deletions(-)
```