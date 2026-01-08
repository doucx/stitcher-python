# 📸 Snapshot Capture

### 💬 备注:
style: ruff and stitcher

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../src/stitcher/app/core.json                     |  2 +
 .../src/stitcher/app/runners/check.json            |  5 +-
 .../src/stitcher/app/runners/pump.json             |  6 +-
 .../src/stitcher/app/services/differ.json          | 10 +++
 .../src/stitcher/app/services/doc_manager.json     | 47 ++++++++------
 .../src/stitcher/app/services/merger.json          | 10 +++
 .../src/stitcher/common/adapters/yaml_adapter.json | 12 ++--
 .../src/stitcher/common/interfaces.json            |  8 +--
 .../src/stitcher/config/loader.json                |  1 +
 .../stitcher-spec/src/stitcher/spec/docstring.json | 35 +++++++++++
 .../stitcher-spec/src/stitcher/spec/models.json    |  3 +
 .../stitcher-spec/src/stitcher/spec/protocols.json | 19 ++++++
 .../src/stitcher/app/runners/check.py              |  4 +-
 .../src/stitcher/app/runners/pump.py               | 27 ++++----
 .../src/stitcher/app/runners/transform.py          |  8 ++-
 .../src/stitcher/app/services/differ.py            | 10 +--
 .../src/stitcher/app/services/differ.stitcher.yaml |  4 +-
 .../src/stitcher/app/services/doc_manager.py       | 69 ++++++++++----------
 .../app/services/doc_manager.stitcher.yaml         | 15 ++---
 .../src/stitcher/app/services/merger.py            | 25 +-------
 .../src/stitcher/app/services/merger.stitcher.yaml | 16 ++++-
 .../tests/unit/test_docstring_hybrid.py            | 18 +++---
 .../stitcher/adapter/python/docstring/__init__.py  |  2 +-
 .../stitcher/adapter/python/docstring/factory.py   |  8 +--
 .../stitcher/adapter/python/docstring/parsers.py   | 14 +++--
 .../stitcher/adapter/python/docstring/renderers.py | 57 ++++++++---------
 .../adapter/python/docstring/serializers.py        | 73 ++++++++++++----------
 .../tests/unit/docstring/test_parsers.py           | 14 ++---
 .../tests/unit/docstring/test_renderers.py         | 52 +++++++--------
 .../tests/unit/docstring/test_serializers.py       |  8 ++-
 ...
 32 files changed, 343 insertions(+), 255 deletions(-)
```