# 📸 Snapshot Capture

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../src/stitcher/analysis/semantic/graph.json      |  52 +++++++
 .../src/stitcher/refactor/engine/graph.json        |  52 -------
 .../src/stitcher/analysis/semantic/__init__.py     |   0
 .../src/stitcher/analysis/semantic/graph.py        | 165 +++++++++++++++++++++
 .../stitcher/analysis/semantic/graph.stitcher.yaml |  10 ++
 .../src/stitcher/refactor/engine/__init__.py       |   2 +-
 .../src/stitcher/refactor/engine/context.py        |   2 +-
 .../src/stitcher/refactor/engine/graph.py          | 165 ---------------------
 .../stitcher/refactor/engine/graph.stitcher.yaml   |  10 --
 .../stitcher/refactor/operations/rename_symbol.py  |   2 +-
 .../tests/integration/test_repro_sidecar_fqn.py    |   2 +-
 .../integration/test_bug_init_relative_import.py   |   2 +-
 .../test_bug_relative_import_refactor.py           |   2 +-
 .../tests/integration/test_debug_rename_failure.py |   2 +-
 .../test_fail_concurrent_move_and_rename.py        |   2 +-
 .../integration/test_monorepo_refactor_e2e.py      |   2 +-
 .../test_monorepo_refactor_with_tests_e2e.py       |   2 +-
 .../tests/integration/test_move_directory_e2e.py   |   2 +-
 .../test_move_directory_monorepo_e2e.py            |   2 +-
 .../tests/integration/test_move_file_e2e.py        |   2 +-
 .../integration/test_move_nested_directory_e2e.py  |   2 +-
 .../tests/integration/test_rename_e2e.py           |   2 +-
 .../test_rename_namespace_pkg_failure.py           |   2 +-
 .../integration/test_rename_symbol_definition.py   |   2 +-
 .../integration/test_rename_symbol_monorepo_e2e.py |   2 +-
 .../test_rename_transformer_advanced.py            |   2 +-
 .../tests/integration/test_semantic_graph.py       |   2 +-
 .../tests/integration/test_usage_registry.py       |   2 +-
 .../tests/unit/engine/test_graph.py                |   2 +-
 .../tests/unit/engine/test_planner_merging.py      |   2 +-
 ...
 32 files changed, 252 insertions(+), 252 deletions(-)
```