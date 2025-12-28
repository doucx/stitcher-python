简要回答：
这是一个严重的核心逻辑 Bug：在 `run_check` 的多目标（Multi-target）或配置循环中，`modules` 变量因作用域问题只保留了最后一批扫描的模块，导致之前的模块在“自动调和阶段”无法被找到，从而静默跳过了保存操作。这解释了为什么文档更新提示反复出现（因为从未真正持久化）。

我将生成一个 Fix 计划来修复此作用域问题，并全面汉化相关的反馈信息。

## [WIP] fix: 修复 check 命令无法持久化自动更新及汉化缺失问题

### 用户需求
1.  **修复持久化失效**: 解决 `stitcher check` 在遇到错误或多目标配置时，无法将“文档更新 (Doc Updated)”的哈希变更保存到磁盘的问题。
2.  **汉化反馈信息**: 将 `stitcher check` 输出的所有状态信息（如 Signature Drift, Co-evolution 等）汉化为中文。

### 评论
该 Bug 的根源在于 Python 循环变量的作用域特性。在 Phase 1 (Analysis) 循环结束后，`modules` 变量仅指向最后一次迭代的结果。Phase 2 (Execution) 试图复用该变量来查找所有模块，导致前面的模块查找失败 (`module_def` 为 `None`) 并静默跳过保存。这是多目标架构下的典型隐患。

### 目标
1.  在 `StitcherApp.run_check` 中引入 `all_modules` 列表，在分析阶段收集所有扫描到的模块定义。
2.  在 Phase 2 (Execution Phase) 中使用 `all_modules` 进行查找，确保所有文件的变更都能被正确持久化。
3.  更新 `stitcher-common` 中的 `zh/check/state.json`，提供完整的中文翻译。
4.  添加一个回归测试，模拟多目标场景，验证非最后一批文件的更新是否能被持久化。

### 基本原理
通过将所有扫描到的 `ModuleDef` 对象收集到一个列表 `all_modules` 中，延长其生命周期至整个 `run_check` 执行过程，确保后续的调和逻辑能访问到任意文件的元数据。同时，通过修改资源文件实现零代码变动的国际化修复。

### 标签
#intent/fix #flow/ready #priority/high #comp/runtime #comp/common #scope/core #scope/i18n #task/domain/testing #task/object/check-command #task/action/fix #task/state/begin

---

### Script

#### Acts 1: 修复 `StitcherApp.run_check` 中的模块作用域 Bug

引入 `all_modules` 并在 Phase 1 累积所有模块，供 Phase 2 使用。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
    def run_check(self, force_relink: bool = False, reconcile: bool = False) -> bool:
        configs, _ = load_config_from_path(self.root_path)
        
        all_results: list[FileCheckResult] = []
        all_conflicts: list[InteractionContext] = []

        # 1. Analysis Phase
        for config in configs:
            if config.name != "default":
                bus.info(L.generate.target.processing, name=config.name)
            unique_files = self._get_files_from_config(config)
            modules = self._scan_files(unique_files)
            for module in modules:
                result, conflicts = self._analyze_file(module)
                all_results.append(result)
                all_conflicts.extend(conflicts)
        
        # 2. Execution Phase (Auto-reconciliation for doc improvements)
        for res in all_results:
            if res.infos["doc_improvement"]:
                module_def = next((m for m in modules if m.file_path == res.path), None)
                if not module_def: continue
                
                stored_hashes = self.sig_manager.load_composite_hashes(module_def)
~~~~~
~~~~~python.new
    def run_check(self, force_relink: bool = False, reconcile: bool = False) -> bool:
        configs, _ = load_config_from_path(self.root_path)
        
        all_results: list[FileCheckResult] = []
        all_conflicts: list[InteractionContext] = []
        all_modules: list[ModuleDef] = []

        # 1. Analysis Phase
        for config in configs:
            if config.name != "default":
                bus.info(L.generate.target.processing, name=config.name)
            unique_files = self._get_files_from_config(config)
            modules = self._scan_files(unique_files)
            all_modules.extend(modules)
            for module in modules:
                result, conflicts = self._analyze_file(module)
                all_results.append(result)
                all_conflicts.extend(conflicts)
        
        # 2. Execution Phase (Auto-reconciliation for doc improvements)
        for res in all_results:
            if res.infos["doc_improvement"]:
                module_def = next((m for m in all_modules if m.file_path == res.path), None)
                if not module_def: continue
                
                stored_hashes = self.sig_manager.load_composite_hashes(module_def)
~~~~~

#### Acts 2: 汉化 `check` 命令的状态反馈信息

更新中文资源文件，提供准确的术语翻译。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/check/state.json
~~~~~
~~~~~json
{
  "check.state.relinked": "已重链接 '{path}' 中 '{key}' 的签名。",
  "check.state.reconciled": "已调和 '{path}' 中 '{key}' 的变更。",
  "check.state.auto_reconciled": "自动更新了 '{path}' 中 {count} 个文档哈希。",
  "check.issue.extra": "悬空文档: '{key}' 在文档中存在但在代码中缺失。",
  "check.state.signature_drift": "签名漂移: '{key}' 代码已变更，文档可能已过时。",
  "check.state.co_evolution": "协同演进: '{key}' 代码和文档均已变更，意图不明确。",
  "check.state.doc_updated": "文档更新: '{key}' 的文档已改进。",
  "check.state.untracked_code": "未追踪代码: '{key}' 是新的公开 API 且无文档。"
}
~~~~~

#### Acts 3: 创建回归测试

创建一个测试用例，使用两个 Target 模拟多批次扫描，验证第一个 Target 中的文件更新是否能被正确持久化。

~~~~~act
write_file
packages/stitcher-application/tests/test_check_regression.py
~~~~~
~~~~~python
from textwrap import dedent
from pathlib import Path
from stitcher.app import StitcherApp
from stitcher.test_utils import WorkspaceFactory, SpyBus, get_stored_hashes
from needle.pointer import L


def test_check_persists_updates_in_multi_target_scan(tmp_path: Path, monkeypatch):
    """
    Regression Test: Ensures that 'doc_improvement' updates are persisted for ALL files,
    not just those in the last scanned batch.
    
    This simulates a bug where 'modules' variable scope in the loop caused early batches
    to be ignored during the execution phase.
    """
    # 1. Setup a workspace with two targets (pkg1 and pkg2)
    # pkg1 will be scanned FIRST. pkg2 SECOND.
    # We will trigger a doc improvement in pkg1.
    
    factory = WorkspaceFactory(tmp_path)
    
    # pkg1: Has a function with matching code/doc initially
    factory.with_source("src/pkg1/mod.py", """
def func():
    \"\"\"Doc.\"\"\"
    pass
""")
    factory.with_docs("src/pkg1/mod.stitcher.yaml", {"func": "Doc."}) # Initial state matches
    
    # pkg2: Just a dummy file
    factory.with_source("src/pkg2/mod.py", "def other(): pass")
    
    # Config: Define two targets
    factory.build()
    (tmp_path / "pyproject.toml").write_text(dedent("""
    [project]
    name = "test-proj"
    
    [tool.stitcher.targets.t1]
    scan_paths = ["src/pkg1"]
    
    [tool.stitcher.targets.t2]
    scan_paths = ["src/pkg2"]
    """), encoding="utf-8")
    
    # 2. Initialize signatures (Run init)
    app = StitcherApp(tmp_path)
    app.run_init()
    
    # Verify init happened
    hashes_initial = get_stored_hashes(tmp_path, "src/pkg1/mod.py")
    assert hashes_initial["func"]["baseline_yaml_content_hash"] is not None
    
    # 3. Modify Docs in YAML (Simulate Doc Improvement)
    # This creates a state: Code Hash matches, YAML Hash differs -> Doc Improvement
    (tmp_path / "src/pkg1/mod.stitcher.yaml").write_text('"func": |-\n  Better Doc.', encoding="utf-8")
    
    # 4. Run Check
    # This should detect the improvement and update the signature file
    spy = SpyBus()
    with spy.patch(monkeypatch, "stitcher.app.core.bus"):
        app.run_check()
    
    # 5. Assertions
    
    # A. Check that the bus reported the update (Phase 4 reporting works even with the bug)
    spy.assert_id_called(L.check.state.doc_updated)
    
    # B. Check PERMANENCE (The critical part)
    # If the bug exists, this file was NOT updated because pkg1 was not in the 'modules'
    # list when the loop finished (pkg2 was).
    hashes_after = get_stored_hashes(tmp_path, "src/pkg1/mod.py")
    
    # The stored hash should now reflect "Better Doc."
    # We don't check the hash value specifically, but it must differ from initial.
    assert hashes_after["func"]["baseline_yaml_content_hash"] != hashes_initial["func"]["baseline_yaml_content_hash"]
~~~~~

### 下一步建议
运行 `pytest packages/stitcher-application/tests/test_check_regression.py` 验证修复效果。验证通过后，再次运行 `stitcher check --non-interactive` 确认汉化效果和持久化行为。
