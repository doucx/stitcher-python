# 📸 Snapshot Capture

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../stitcher-application/src/stitcher/app/core.py  | 20 --------------
 .../src/stitcher/app/core.stitcher.yaml            | 24 ++++++++++++++++
 .../src/stitcher/app/services/doc_manager.py       | 32 ----------------------
 .../app/services/doc_manager.stitcher.yaml         | 27 ++++++++++++++++++
 .../src/stitcher/app/services/signature_manager.py | 24 ----------------
 .../app/services/signature_manager.stitcher.yaml   | 17 ++++++++++++
 .../stitcher-application/tests/test_doc_manager.py | 12 --------
 .../tests/test_doc_manager.stitcher.yaml           | 11 ++++++++
 .../stitcher-application/tests/test_doc_overlay.py |  6 ----
 .../tests/test_doc_overlay.stitcher.yaml           |  4 +++
 .../tests/test_signature_manager.py                | 10 -------
 .../tests/test_signature_manager.stitcher.yaml     |  8 ++++++
 packages/stitcher-cli/src/stitcher/cli/main.py     |  8 ------
 .../src/stitcher/cli/main.stitcher.yaml            | 12 ++++++++
 .../stitcher-cli/src/stitcher/cli/rendering.py     |  4 ---
 .../src/stitcher/cli/rendering.stitcher.yaml       |  2 ++
 .../src/stitcher/common/messaging/bus.py           |  1 -
 .../stitcher/common/messaging/bus.stitcher.yaml    |  2 ++
 .../src/stitcher/common/messaging/protocols.py     | 15 +---------
 .../common/messaging/protocols.stitcher.yaml       |  9 ++++++
 .../stitcher-config/src/stitcher/config/loader.py  |  3 --
 .../src/stitcher/config/loader.stitcher.yaml       |  6 ++++
 packages/stitcher-config/tests/test_loader.py      |  5 ----
 .../tests/test_loader.stitcher.yaml                |  5 ++++
 .../src/stitcher/io/adapters/yaml_adapter.py       |  4 ---
 .../io/adapters/yaml_adapter.stitcher.yaml         |  2 ++
 packages/stitcher-io/src/stitcher/io/interfaces.py | 30 ++------------------
 .../src/stitcher/io/interfaces.stitcher.yaml       | 20 ++++++++++++++
 .../stitcher-io/src/stitcher/io/stub_generator.py  |  3 --
 .../src/stitcher/io/stub_generator.stitcher.yaml   |  2 ++
 ...
 66 files changed, 324 insertions(+), 346 deletions(-)
```