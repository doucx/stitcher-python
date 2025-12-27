# 📸 Snapshot Capture

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../pyneedle-nexus/src/needle/nexus/loaders.py     |  17 ---
 .../src/needle/nexus/loaders.stitcher.yaml         |  13 ++
 packages/pyneedle-nexus/src/needle/nexus/nexus.py  |  28 ----
 .../src/needle/nexus/nexus.stitcher.yaml           |  21 +++
 packages/pyneedle-nexus/tests/test_nexus.py        |   7 -
 .../pyneedle-nexus/tests/test_nexus.stitcher.yaml  |  14 ++
 .../pyneedle-pointer/src/needle/pointer/core.py    |  37 -----
 .../src/needle/pointer/core.stitcher.yaml          |  28 ++++
 .../pyneedle-pointer/src/needle/pointer/set.py     |  20 ---
 .../src/needle/pointer/set.stitcher.yaml           |  15 ++
 .../pyneedle-pointer/tests/test_pointer_algebra.py |   9 --
 .../tests/test_pointer_algebra.stitcher.yaml       |  18 +++
 .../pyneedle-spec/src/needle/spec/protocols.py     | 151 ++++-----------------
 .../src/needle/spec/protocols.stitcher.yaml        |  67 +++++++++
 packages/pyneedle/src/needle/loaders/fs_loader.py  |  13 --
 .../src/needle/loaders/fs_loader.stitcher.yaml     |  12 ++
 .../pyneedle/src/needle/loaders/json_handler.py    |   2 -
 .../src/needle/loaders/json_handler.stitcher.yaml  |   2 +
 packages/pyneedle/src/needle/loaders/protocols.py  |  12 +-
 .../src/needle/loaders/protocols.stitcher.yaml     |   6 +
 packages/pyneedle/src/needle/runtime.py            |   2 -
 packages/pyneedle/tests/test_assembly.py           |   9 --
 .../pyneedle/tests/test_assembly.stitcher.yaml     |   7 +
 23 files changed, 229 insertions(+), 281 deletions(-)
```