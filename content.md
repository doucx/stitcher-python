# 📸 Snapshot Capture

### 💬 备注:
stitcher strip

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../stitcher-application/src/stitcher/app/core.py  | 14 ----------
 .../src/stitcher/app/services/doc_manager.py       | 28 --------------------
 .../src/stitcher/app/services/signature_manager.py | 24 -----------------
 .../stitcher-application/tests/test_doc_manager.py | 12 ---------
 .../stitcher-application/tests/test_doc_overlay.py |  6 -----
 .../tests/test_signature_manager.py                | 10 --------
 packages/stitcher-cli/src/stitcher/cli/main.py     |  5 ----
 .../stitcher-cli/src/stitcher/cli/rendering.py     |  4 ---
 .../src/stitcher/common/messaging/bus.py           |  1 -
 .../src/stitcher/common/messaging/protocols.py     | 15 +----------
 .../stitcher-config/src/stitcher/config/loader.py  |  3 ---
 packages/stitcher-config/tests/test_loader.py      |  5 ----
 .../src/stitcher/io/adapters/yaml_adapter.py       |  4 ---
 packages/stitcher-io/src/stitcher/io/interfaces.py | 30 ++--------------------
 .../stitcher-io/src/stitcher/io/stub_generator.py  |  3 ---
 packages/stitcher-io/tests/test_document_io.py     |  4 ---
 .../src/stitcher/needle/handlers.py                |  2 --
 .../src/stitcher/needle/interfaces.py              | 12 ++-------
 .../stitcher-needle/src/stitcher/needle/loader.py  |  4 ---
 .../stitcher-needle/src/stitcher/needle/pointer.py | 23 -----------------
 .../stitcher-needle/src/stitcher/needle/runtime.py | 16 ------------
 .../src/stitcher/scanner/inspector.py              | 17 ------------
 .../src/stitcher/scanner/parser.py                 |  9 -------
 .../src/stitcher/scanner/transformer.py            |  7 -----
 packages/stitcher-scanner/tests/test_inspector.py  |  5 ----
 .../stitcher-scanner/tests/test_parser_advanced.py |  4 ---
 .../stitcher-scanner/tests/test_parser_imports.py  |  4 ---
 .../stitcher-scanner/tests/test_transformer.py     |  1 -
 packages/stitcher-spec/src/stitcher/spec/models.py | 17 ------------
 .../src/stitcher/test_utils/bus.py                 | 11 --------
 ...
 32 files changed, 5 insertions(+), 316 deletions(-)
```