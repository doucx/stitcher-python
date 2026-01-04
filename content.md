#### Acts 2: 修复 PumpRunner 的返回值

现在，我们修复 `PumpRunner.run` 方法，使其正确报告被修改的文件。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/pump.py
~~~~~
~~~~~python
        strip_jobs = defaultdict(list)
        total_updated_keys = 0
        total_reconciled_keys = 0
        unresolved_conflicts_count = 0

        for module in all_modules:
            file_plan = self._generate_execution_plan(module, decisions, strip)
~~~~~
~~~~~python
        strip_jobs = defaultdict(list)
        total_updated_keys = 0
        total_reconciled_keys = 0
        unresolved_conflicts_count = 0
        files_with_pumped_docs: List[Path] = []

        for module in all_modules:
            file_plan = self._generate_execution_plan(module, decisions, strip)
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/pump.py
~~~~~
~~~~~python
            if updated_keys_in_file:
                total_updated_keys += len(updated_keys_in_file)
                bus.success(
                    L.pump.file.success,
                    path=module.file_path,
                    count=len(updated_keys_in_file),
                )

            if reconciled_keys_in_file:
~~~~~
~~~~~python
            if updated_keys_in_file:
                total_updated_keys += len(updated_keys_in_file)
                files_with_pumped_docs.append(self.root_path / module.file_path)
                bus.success(
                    L.pump.file.success,
                    path=module.file_path,
                    count=len(updated_keys_in_file),
                )

            if reconciled_keys_in_file:
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/pump.py
~~~~~
~~~~~python
        if not has_activity:
            bus.info(L.pump.run.no_changes)
        else:
            bus.success(L.pump.run.complete, count=total_updated_keys)

        return PumpResult(success=True, redundant_files=[])
~~~~~
~~~~~python
        if not has_activity:
            bus.info(L.pump.run.no_changes)
        else:
            bus.success(L.pump.run.complete, count=total_updated_keys)

        redundant = []
        if not strip:
            redundant = files_with_pumped_docs

        return PumpResult(success=True, redundant_files=redundant)
~~~~~

### 下一步建议
现在，我们已经通过 TDD 修复了这个缺陷。请执行此计划。计划执行后，再次运行 `pytest packages/stitcher-cli`，新添加的测试应该会通过，证明问题已解决。

