# 📸 Snapshot Capture

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../stitcher-application/src/stitcher/app/core.py  | 40 +++++-----
 .../src/stitcher/app/services/__init__.py          |  2 +-
 .../src/stitcher/app/services/doc_manager.py       | 85 +++++++++++-----------
 .../stitcher-application/tests/test_doc_manager.py | 27 +++----
 .../stitcher-application/tests/test_doc_overlay.py | 32 ++++----
 packages/stitcher-cli/src/stitcher/cli/main.py     |  1 -
 packages/stitcher-io/src/stitcher/io/__init__.py   |  2 +-
 .../src/stitcher/io/adapters/yaml_adapter.py       | 24 +++---
 packages/stitcher-io/src/stitcher/io/interfaces.py | 12 +--
 packages/stitcher-io/tests/test_document_io.py     | 17 ++---
 tests/integration/test_check_command.py            | 61 +++++++++-------
 tests/integration/test_init_command.py             | 41 ++++++-----
 12 files changed, 172 insertions(+), 172 deletions(-)
```