# 📸 Snapshot Capture

检测到工作区发生变更。

### 📝 变更文件摘要:
```
migrations/005_update_bus_fqn_references.py                 |  9 ++++++---
 packages/stitcher-bus/src/stitcher/bus/__init__.py          |  3 ++-
 packages/stitcher-bus/src/stitcher/bus/bus.py               |  2 +-
 packages/stitcher-bus/src/stitcher/bus/factory.py           |  2 +-
 packages/stitcher-bus/stitcher.lock                         | 12 ++++++++++++
 packages/stitcher-common/src/stitcher/common/__init__.py    |  2 +-
 .../src/stitcher/common/__init__.stitcher.yaml              |  7 -------
 .../src/stitcher/common/adapters/yaml_adapter.stitcher.yaml | 10 ----------
 packages/stitcher-common/stitcher.lock                      | 13 -------------
 packages/stitcher-test-utils/stitcher.lock                  |  4 ++--
 10 files changed, 25 insertions(+), 39 deletions(-)
```