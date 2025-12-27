# 📸 Snapshot Capture

### 💬 备注:
chore

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../stitcher-application/src/stitcher/app/core.py  |  5 ++-
 .../stitcher/app/services/stub_package_manager.py  |  1 -
 .../services/stub_package_manager.stitcher.yaml    |  2 +
 .../src/stitcher/test_utils/harness.py             | 44 ---------------------
 .../src/stitcher/test_utils/harness.stitcher.yaml  | 45 ++++++++++++++++++++++
 tests/integration/conftest.py                      |  2 +-
 tests/integration/test_ide_proxy.py                | 19 ++++-----
 tests/integration/test_multi_target_stub_names.py  | 12 +++---
 tests/integration/test_stub_package.py             |  2 +-
 tests/integration/test_stub_package_namespace.py   |  2 +-
 tests/integration/test_stub_package_pep561.py      | 12 +++---
 tests/integration/test_stub_package_resolution.py  |  2 +-
 12 files changed, 75 insertions(+), 73 deletions(-)
```