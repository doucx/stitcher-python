简要回答
是的，我将执行“提案：引入纯净的应用层”的第一阶段：重构 `pump` 命令。

目前的 `StitcherApp.run_pump` 方法中包含了一段直接依赖 `typer` 的交互代码，这不仅违反了分层架构原则，还与 CLI 层中已存在的相同逻辑造成了冗余。

我将生成一个计划，从应用层核心逻辑中彻底移除这段代码，使其回归纯净。由于 CLI 层 (`stitcher-cli`) 已经具备了处理交互确认和后续调用的逻辑，此修改是安全的。

## [WIP] refactor(app): 移除 StitcherApp.run_pump 中的 UI 交互逻辑

### 用户需求
执行“引入纯净应用层”提案的第一阶段，清理 `stitcher-application` 包中泄露的 CLI 依赖，具体针对 `pump` 命令的执行流程。

### 评论
当前 `StitcherApp.run_pump` 方法中包含一段 `if ... import typer ...` 的逻辑。这部分代码不仅难以测试（需要 mock typer），而且在 `stitcher-cli` 中已经有重复实现。移除它将立即使应用层变得更纯净、可测试且可移植。

### 目标
1.  修改 `packages/stitcher-application/src/stitcher/app/core.py`。
2.  移除 `run_pump` 方法尾部的交互式确认（`typer.confirm`）和对 `self.run_strip` 的条件调用。
3.  确保 `run_pump` 仅负责执行 pump 逻辑并返回 `PumpResult` DTO。

### 基本原理
根据架构提案，应用层 (`stitcher-application`) 必须保持对表现层框架（如 `typer`）的无知（Oblivious）。所有的用户交互决策和流程编排（Orchestration）都应上移至 CLI 层。CLI 层目前已经包含了处理 `PumpResult` 并询问用户是否 strip 的逻辑，因此删除下层代码不会导致功能缺失。

### 标签
#intent/refine #flow/ready #priority/high
#comp/runtime #scope/core
#ai/instruct
#task/domain/architecture #task/object/application-layer #task/action/decouple-ui
#task/state/begin #task/status/active

---

### Script

#### Acts 1: 净化 StitcherApp.run_pump

移除 `run_pump` 中所有关于 `typer` 的导入和交互逻辑。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python
    def run_pump(
        self, strip: bool = False, force: bool = False, reconcile: bool = False
    ) -> PumpResult:
        # Pass-through all options to the dedicated runner
        result = self.pump_runner.run(strip=strip, force=force, reconcile=reconcile)

        # The secondary, interactive strip confirmation logic remains here for now,
        # as it's a cross-command concern (pump -> strip).
        # A more advanced implementation might use an event bus or a post-execution hook.
        if (
            self.pump_runner.interaction_handler
            and result.redundant_files
            and not strip
        ):
            import typer  # Lazy import for CLI-specific interaction

            typer.echo("")
            typer.secho(
                f"Found {len(result.redundant_files)} file(s) with redundant docstrings in source code.",
                fg=typer.colors.YELLOW,
            )
            if typer.confirm("Do you want to strip them now?", default=True):
                self.run_strip(files=result.redundant_files)

        return result

    def run_strip(self, files: Optional[List[Path]] = None) -> List[Path]:
~~~~~
~~~~~python
    def run_pump(
        self, strip: bool = False, force: bool = False, reconcile: bool = False
    ) -> PumpResult:
        # Pass-through all options to the dedicated runner
        return self.pump_runner.run(strip=strip, force=force, reconcile=reconcile)

    def run_strip(self, files: Optional[List[Path]] = None) -> List[Path]:
~~~~~

### 下一步建议

代码修改完成后，建议运行测试以确保重构未引入回归。
1.  运行 `pytest packages/stitcher-application/tests` 验证应用层逻辑。
2.  (可选) 手动验证或检查 CLI 层的测试，确保 `stitcher pump` 命令在发现冗余文件时仍能提示用户进行 strip 操作（由 CLI 层逻辑保证）。
