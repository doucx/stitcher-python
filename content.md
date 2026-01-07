你说得完全正确。固定宽度的列在面对不同长度的文件路径时，确实会破坏对齐，导致输出难以阅读。这是我的疏忽。

为了解决这个问题，我将修改报告生成逻辑，使其动态计算“Name”列所需的宽度，确保无论路径多长，所有列都能完美对齐。这才是专业命令行工具应有的表现。

我将生成一个计划来修正这个问题。

## [WIP] fix: 动态调整 `cov` 命令的输出列宽以确保对齐

### 错误分析

当前 `CoverageRunner` 中的 `_render_report` 方法使用了固定的列宽（`f"{'Name':<35}"`）来格式化输出。当文件路径的长度超过35个字符时，f-string 不会截断它，而是会使用实际的长度，这导致后续的列被向右推移，从而破坏了整个表格的对齐。

### 用户需求

用户要求 `stitcher cov` 的输出表格必须是完美对齐的，就像 `pytest-cov` 一样，无论文件名有多长。

### 评论

这是一个非常合理的对齐和用户体验（UX）改进。动态计算列宽是解决此类问题的标准方法，可以确保输出的专业性和可读性。

### 目标

1.  修改 `CoverageRunner._render_report` 方法。
2.  在打印报告之前，先遍历一次所有结果，找出最长的文件路径长度。
3.  使用这个动态计算出的最大长度作为“Name”列的宽度来格式化表头和每一行数据。
4.  同时，动态计算并更新用于分隔线的横线长度，以适应新的表格宽度。

### 基本原理

我将对 `_render_report` 方法进行如下修改：
1.  在函数开头，通过 `max()` 函数计算出所有 `result.path` 字符串中的最大长度，并与表头 "Name" 和 "TOTAL" 的长度比较，取最大值作为 `name_col_width`。
2.  将所有 `typer.secho` 调用中的 f-string 格式化字符串从硬编码的宽度（如 `:<35`）修改为使用这个动态计算出的变量（如 `:<{name_col_width}`）。
3.  重新计算分隔线的总长度，并用它来生成横线。

这样就能确保无论文件路径多长，整个报告的表格都保持整洁对齐。

### 标签

#intent/fix #flow/ready #priority/medium #comp/application #concept/ui #scope/ux #task/domain/cli #task/object/coverage-report #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 修正 `CoverageRunner` 的报告渲染逻辑

这是唯一的修改。我们将重写 `_render_report` 方法以实现动态列宽。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/coverage.py
~~~~~
~~~~~python.old
    def _render_report(self, results: List[CoverageResult]):
        typer.echo("\n" + ("-" * 65))
        typer.secho(
            f"{'Name':<35} {'Stmts':>7} {'Miss':>7} {'Cover':>10}", bold=True
        )
        typer.echo("-" * 65)

        total_stmts = 0
        total_miss = 0

        for res in sorted(results, key=lambda r: r.path):
            if res.total_symbols == 0:
                continue

            total_stmts += res.total_symbols
            total_miss += res.missing_symbols
            
            cover_str = f"{res.coverage:.1f}%"
            
            color = typer.colors.GREEN
            if res.coverage < 50:
                color = typer.colors.RED
            elif res.coverage < 90:
                color = typer.colors.YELLOW

            typer.secho(
                f"{res.path:<35} {res.total_symbols:>7} {res.missing_symbols:>7} {cover_str:>10}",
                fg=color,
            )

        typer.echo("-" * 65)

        total_coverage = (
            ((total_stmts - total_miss) / total_stmts * 100) if total_stmts > 0 else 100.0
        )
        cover_str = f"{total_coverage:.1f}%"
        typer.secho(
            f"{'TOTAL':<35} {total_stmts:>7} {total_miss:>7} {cover_str:>10}",
            bold=True,
        )
        typer.echo("")
~~~~~
~~~~~python.new
    def _render_report(self, results: List[CoverageResult]):
        if not results:
            return

        # Dynamically determine column width
        paths = [r.path for r in results if r.total_symbols > 0]
        max_path_len = max(len(p) for p in paths) if paths else 0
        name_col_width = max(len("Name"), len("TOTAL"), max_path_len)

        # Define other column widths
        stmts_col_width = 7
        miss_col_width = 7
        cover_col_width = 10
        
        # Calculate total width for the horizontal rule
        total_width = name_col_width + stmts_col_width + miss_col_width + cover_col_width + 3 # For spaces

        typer.echo("\n" + ("-" * total_width))
        typer.secho(
            f"{'Name':<{name_col_width}} {'Stmts':>{stmts_col_width}} {'Miss':>{miss_col_width}} {'Cover':>{cover_col_width}}",
            bold=True,
        )
        typer.echo("-" * total_width)

        total_stmts = 0
        total_miss = 0

        for res in sorted(results, key=lambda r: r.path):
            if res.total_symbols == 0:
                continue

            total_stmts += res.total_symbols
            total_miss += res.missing_symbols

            cover_str = f"{res.coverage:.1f}%"

            color = typer.colors.GREEN
            if res.coverage < 50:
                color = typer.colors.RED
            elif res.coverage < 90:
                color = typer.colors.YELLOW

            typer.secho(
                (
                    f"{res.path:<{name_col_width}} "
                    f"{res.total_symbols:>{stmts_col_width}} "
                    f"{res.missing_symbols:>{miss_col_width}} "
                    f"{cover_str:>{cover_col_width}}"
                ),
                fg=color,
            )

        typer.echo("-" * total_width)

        total_coverage = (
            ((total_stmts - total_miss) / total_stmts * 100)
            if total_stmts > 0
            else 100.0
        )
        cover_str = f"{total_coverage:.1f}%"
        typer.secho(
            (
                f"{'TOTAL':<{name_col_width}} "
                f"{total_stmts:>{stmts_col_width}} "
                f"{total_miss:>{miss_col_width}} "
                f"{cover_str:>{cover_col_width}}"
            ),
            bold=True,
        )
        typer.echo("")
~~~~~

### 下一步建议

现在格式化问题已经解决。我们可以再次运行 `stitcher cov` 来确认输出是否完美对齐。确认后，我建议我们继续进行之前提到的测试计划，为这个功能添加健壮的集成测试。
