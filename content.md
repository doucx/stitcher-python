Excellent. The test failed exactly as predicted, confirming the bug's location.

The error lies in the application's core logic, where it iterates through multiple targets but repeatedly uses the single, global project name for scaffolding each target's stub package.

Here is the plan to fix this logical flaw.

## [WIP] fix: Use target name for stub package scaffolding in multi-target mode

### 错误分析
测试失败的原因正如我们所料：`StitcherApp.run_from_config` 方法在循环处理多个构建目标（targets）时，错误地将全局的 `project_name` (`monorepo-project`) 传递给了 `_scaffold_stub_package` 方法。因此，无论是处理 `app-a` 还是 `app-b`，脚手架逻辑都尝试创建名为 `monorepo-project-stubs` 的包，导致了断言失败 `config_a["project"]["name"] == "app-a-stubs"`。

### 用户需求
修复此 bug，确保在多目标模式下，为每个目标生成的存根包都使用其各自的 `target` 名称（例如 `app-a`）作为基础名称，而不是全局的项目名称。

### 评论
这是一个典型的状态管理错误，修复它对于确保 Stitcher 在 Monorepo 环境下的健壮性和可预测性至关重要。这个修复将使每个 target 的构建过程完全独立。

### 目标
1.  修改 `stitcher.app.core.StitcherApp.run_from_config` 方法。
2.  在循环内部，添加逻辑来判断当前处理的 `config` 对象是具名目标还是默认目标。
3.  如果它是一个具名目标（`config.name != "default"`），则使用 `config.name` 作为存根包的基础名称。
4.  否则（对于单目标或遗留配置），回退到使用全局的 `project_name`。
5.  将这个正确决定的基础名称传递给 `_scaffold_stub_package` 方法。

### 基本原理
我们将只对 `run_from_config` 方法中的一行代码进行精确修改。通过在调用 `_scaffold_stub_package` 之前插入一个三元表达式 `stub_base_name = config.name if config.name != "default" else project_name`，我们可以动态地为每个循环选择正确的名称上下文。这既修复了多目标模式的 bug，又保持了对单目标模式的向后兼容性。

### 标签
#intent/fix #flow/ready #priority/high #comp/application #concept/config #scope/core #ai/instruct #task/domain/testing #task/object/multi-target #task/action/bug-fix #task/state/continue

---
### Script

#### Acts 1: 修正 `run_from_config` 中的名称传递逻辑

我将修改 `stitcher-application/src/stitcher/app/core.py` 文件，确保在处理多目标时，将正确的 `target` 名称传递给存根包脚手架函数。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
            # 0. Scaffold stub package if configured
            if config.stub_package:
                self._scaffold_stub_package(config, project_name)
~~~~~
~~~~~python.new
            # 0. Scaffold stub package if configured
            if config.stub_package:
                stub_base_name = config.name if config.name != "default" else project_name
                self._scaffold_stub_package(config, stub_base_name)
~~~~~

### 下一步建议

这个补丁应该已经修复了问题。请执行它，然后重新运行测试套件。我们新增的测试用例 `test_multi_target_scaffolds_correct_stub_package_names` 现在应该会通过。
