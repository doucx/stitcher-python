# 📸 Snapshot Capture

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../src/stitcher/app/__init__.py                   |  2 +-
 .../stitcher-application/src/stitcher/app/core.py  | 30 +++++-----
 packages/stitcher-cli/src/stitcher/cli/__init__.py |  2 +-
 packages/stitcher-cli/src/stitcher/cli/main.py     |  6 +-
 .../stitcher-cli/src/stitcher/cli/rendering.py     |  6 +-
 .../src/stitcher/common/__init__.py                |  2 +-
 .../src/stitcher/common/messaging/bus.py           | 15 +++--
 .../src/stitcher/common/messaging/protocols.py     |  5 +-
 .../src/stitcher/config/__init__.py                |  2 +-
 .../stitcher-config/src/stitcher/config/loader.py  | 10 ++--
 packages/stitcher-config/tests/test_loader.py      | 18 ++++--
 packages/stitcher-io/src/stitcher/io/__init__.py   |  2 +-
 .../stitcher-io/src/stitcher/io/stub_generator.py  | 58 ++++++++++---------
 packages/stitcher-io/tests/test_stub_generator.py  | 44 ++++++++++-----
 packages/stitcher-needle/src/stitcher/__init__.py  |  2 +-
 .../src/stitcher/needle/__init__.py                |  2 +-
 .../src/stitcher/needle/handlers.py                |  3 +-
 .../src/stitcher/needle/interfaces.py              |  2 +-
 .../stitcher-needle/src/stitcher/needle/loader.py  |  7 +--
 .../stitcher-needle/src/stitcher/needle/pointer.py |  3 +-
 .../stitcher-needle/src/stitcher/needle/runtime.py | 11 ++--
 packages/stitcher-needle/tests/test_pointer.py     |  9 ++-
 packages/stitcher-needle/tests/test_runtime.py     | 26 ++++-----
 .../src/stitcher/scanner/__init__.py               |  2 +-
 .../src/stitcher/scanner/inspector.py              | 34 ++++++-----
 .../src/stitcher/scanner/parser.py                 | 66 +++++++++++-----------
 packages/stitcher-scanner/tests/test_inspector.py  | 15 +++--
 .../stitcher-scanner/tests/test_parser_advanced.py | 38 +++++++------
 .../stitcher-scanner/tests/test_parser_basic.py    | 15 ++---
 .../stitcher-spec/src/stitcher/spec/__init__.py    |  2 +-
 ...
 35 files changed, 284 insertions(+), 236 deletions(-)
```