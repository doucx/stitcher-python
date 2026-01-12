# 📸 Snapshot Capture

### 💬 备注:
style: ruff and stitcher

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../src/stitcher/analysis/schema/results.json      |  9 ++++++-
 .../src/stitcher/app/runners/check/resolver.json   |  8 +++----
 .../src/stitcher/app/runners/check/runner.json     | 28 ++++++++++++----------
 .../src/stitcher/analysis/schema/results.py        |  2 +-
 .../tests/unit/engines/test_pump_engine.py         |  2 +-
 .../tests/unit/rules/consistency/test_rules.py     |  1 -
 .../src/stitcher/app/runners/check/reporter.py     |  4 ++--
 .../src/stitcher/app/runners/check/resolver.py     | 16 ++++---------
 .../src/stitcher/app/runners/check/runner.py       |  2 +-
 .../tests/unit/runners/check/test_check_runner.py  | 14 ++++++-----
 .../tests/unit/runners/pump/test_pump_executor.py  |  6 +++--
 11 files changed, 50 insertions(+), 42 deletions(-)
```