# 📸 Snapshot Capture

检测到工作区发生变更。

### 📝 变更文件摘要:
```
packages/stitcher-analysis/pyproject.toml          |  2 +-
 .../rules/architecture/circular_dependency.py      |  8 ++---
 packages/stitcher-application/pyproject.toml       |  2 +-
 .../stitcher-application/src/stitcher/app/core.py  |  2 +-
 .../src/stitcher/app/runners/check/reporter.py     |  2 +-
 .../src/stitcher/app/runners/check/resolver.py     |  2 +-
 .../src/stitcher/app/runners/index.py              |  2 +-
 .../src/stitcher/app/runners/pump/executor.py      |  2 +-
 .../src/stitcher/app/runners/pump/runner.py        |  2 +-
 .../src/stitcher/app/runners/refactor.py           |  2 +-
 .../src/stitcher/app/runners/transform.py          |  2 +-
 .../src/stitcher/services/scanner.py               |  2 +-
 packages/stitcher-bus/pyproject.toml               | 17 ----------
 packages/stitcher-bus/src/stitcher/__init__.py     |  2 --
 packages/stitcher-bus/src/stitcher/bus/__init__.py |  7 -----
 .../bus/assets/needle/en/check/architecture.json   |  4 ---
 .../stitcher/bus/assets/needle/en/check/file.json  |  7 -----
 .../stitcher/bus/assets/needle/en/check/issue.json |  8 -----
 .../stitcher/bus/assets/needle/en/check/run.json   |  6 ----
 .../stitcher/bus/assets/needle/en/check/state.json |  8 -----
 .../src/stitcher/bus/assets/needle/en/cli/app.json |  3 --
 .../stitcher/bus/assets/needle/en/cli/command.json | 36 ----------------------
 .../stitcher/bus/assets/needle/en/cli/option.json  | 32 -------------------
 .../stitcher/bus/assets/needle/en/debug/log.json   | 11 -------
 .../bus/assets/needle/en/error/__init__.json       |  3 --
 .../stitcher/bus/assets/needle/en/error/cli.json   |  3 --
 .../bus/assets/needle/en/error/config.json         |  3 --
 .../bus/assets/needle/en/error/plugin.json         |  3 --
 .../bus/assets/needle/en/error/workspace.json      |  3 --
 .../bus/assets/needle/en/generate/file.json        |  3 --
 ...
 180 files changed, 846 insertions(+), 1143 deletions(-)
```