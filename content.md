# 📸 Snapshot Capture

### 💬 备注:
chore: Bootstrap stitcher with its own documentation

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../stitcher-io/tests/test_document_io.json        |  1 +
 .../src/stitcher/app/core.stitcher.yaml            |  6 ++--
 .../app/services/doc_manager.stitcher.yaml         | 40 ++++++++++------------
 .../app/services/signature_manager.stitcher.yaml   | 32 ++++++++---------
 .../tests/test_doc_manager.stitcher.yaml           | 14 ++++++--
 .../common/messaging/protocols.stitcher.yaml       | 13 ++++---
 .../tests/test_loader.stitcher.yaml                |  7 ++--
 .../src/stitcher/io/interfaces.stitcher.yaml       | 27 +++++++++------
 .../tests/test_document_io.stitcher.yaml           |  2 ++
 .../src/stitcher/needle/loader.stitcher.yaml       |  7 ++--
 .../src/stitcher/needle/pointer.stitcher.yaml      | 19 ++++------
 .../src/stitcher/needle/runtime.stitcher.yaml      | 16 ++++-----
 .../src/stitcher/scanner/inspector.stitcher.yaml   | 17 ++++++---
 .../tests/test_inspector.stitcher.yaml             |  7 ++--
 .../src/stitcher/spec/models.stitcher.yaml         |  8 ++---
 .../src/stitcher/test_utils/bus.stitcher.yaml      |  6 ++--
 .../src/stitcher/test_utils/needle.stitcher.yaml   |  9 +++--
 17 files changed, 120 insertions(+), 111 deletions(-)
```