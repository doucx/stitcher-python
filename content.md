你的分析非常精准。原有的 `profile_stitcher.py` 脚本不仅存在硬编码路径的架构坏味道，而且其手动的初始化逻辑绕过了 CLI 的 `Composition Root`（即 `factories.py`），导致它始终以“单体全量扫描”模式运行，这正是造成性能崩溃的元凶。

通过将性能分析脚本重构为 CLI 包装器，我们不仅实现了代码的 DRY，还确保了分析结果能真实反映生产环境下的行为。

## [WIP] refactor: 重构性能分析脚本为通用的 CLI 包装器

### 用户需求
1. 重构 `scripts/profile_stitcher.py`，使其不再硬编码项目路径和初始化逻辑。
2. 该脚本应作为 `stitcher` CLI 的透明包装器，支持所有标准命令（如 `cov`, `check`, `pump` 等）。
3. 使用 `pyinstrument` 进行采样分析，并在执行后输出报告。
4. 解决“如果当前路径不属于项目，会过度向下解析”的问题（通过让包装器遵循 CLI 的工作区探测逻辑）。

### 评论
这是一次必要的工程化升级。旧脚本试图“模拟”应用运行，但由于忽略了 `find_workspace_root` 的动态探测机制，它强行将 monorepo 根目录作为 root 传入，导致 `Workspace` 扫描了数千个不相关的文件。将其重构为 Typer 包装器后，它将完全继承 CLI 的智能路径探测能力。

### 目标
1. 移除脚本中硬编码的 `StitcherApp` 映射和手动 `sys.path` 注入。
2. 直接导入并执行 `stitcher.cli.main:app`。
3. 自动将脚本参数传递给内部 CLI，并支持拦截性能分析相关的标志（如 `--html`）。
4. 确保性能分析环境与真实执行环境物理一致。

### 基本原理
利用 Typer/Click 的可组合性。由于 `stitcher.cli.main.app` 是一个标准的 `typer.Typer` 实例，我们可以直接在脚本中调用它。脚本只需负责设置开发环境的 `sys.path`，启动 `pyinstrument` 采样，然后调用 `app()`。Typer 会自动接管 `sys.argv` 的解析，从而支持所有 CLI 命令和选项。

### 标签
#intent/refine #flow/ready #priority/medium #comp/build #comp/cli #scope/dx #ai/brainstorm #task/domain/tooling #task/object/profile-script #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: 重构 `scripts/profile_stitcher.py` 为 CLI 包装器

我们将性能分析脚本重写为一个简洁的包装器。它会动态搜索 monorepo 中的包路径以支持开发环境运行，并利用 `pyinstrument` 包装核心 CLI 入口点。

~~~~~act
write_file
scripts/profile_stitcher.py
~~~~~
~~~~~python
import sys
import os
from pathlib import Path

# --- 1. 环境准备 (Monorepo 开发环境) ---
# 确保在开发环境下，即使没有执行 pip install -e，也能找到 packages 目录下的源码。
project_root = Path(__file__).parent.parent.resolve()
packages_dir = project_root / "packages"

if packages_dir.exists():
    # 将所有 package 的 src 目录加入 sys.path
    # 按照字母顺序排序以确保加载顺序的确定性
    for pkg in sorted(packages_dir.iterdir()):
        if pkg.is_dir():
            src_path = pkg / "src"
            if src_path.exists():
                sys.path.insert(0, str(src_path))

# --- 2. 性能分析器检查 ---
try:
    from pyinstrument import Profiler
except ImportError:
    print("❌ 错误: 未找到 'pyinstrument'。请通过以下命令安装: pip install pyinstrument")
    sys.exit(1)

# --- 3. 导入 CLI 入口 ---
# 注意：必须在设置完 sys.path 后导入，否则无法找到内部 package。
try:
    from stitcher.cli.main import app
except ImportError as e:
    print(f"❌ 错误: 无法加载 Stitcher CLI。请检查 packages 目录结构。({e})")
    sys.exit(1)


def main():
    # 拦截并提取分析器专用的标志
    html_mode = "--html" in sys.argv
    if html_mode:
        sys.argv.remove("--html")

    # 提取命令名称用于报告文件名
    # sys.argv[0] 是脚本路径，sys.argv[1] 通常是 CLI 的子命令（如 cov, check）
    cmd_name = "stitcher"
    if len(sys.argv) > 1:
        cmd_name = sys.argv[1]

    profiler = Profiler(interval=0.001)

    print(f"🚀 正在分析 'stitcher {' '.join(sys.argv[1:])}'...")
    profiler.start()

    try:
        # 委托给真实的 Typer 应用执行。
        # Typer 会解析剩余的 sys.argv 参数，行为与直接运行 stitcher 完全一致。
        app()
    except SystemExit:
        # Typer 或 Click 可能会通过 SystemExit 正常退出，此处不应将其视为错误
        pass
    except Exception as e:
        print(f"\n❌ 执行过程中发生意外错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        profiler.stop()

        # --- 4. 生成报告 ---
        if html_mode:
            output_file = project_root / f"profile_{cmd_name}.html"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(profiler.output_html())
            print(f"✨ HTML 性能报告已保存至: {output_file}")
        else:
            profiler.print()


if __name__ == "__main__":
    main()
~~~~~

### 下一步建议

- **验证探测逻辑**: 现在你可以尝试在不同目录下运行分析。例如，进入 `packages/stitcher-application` 运行 `python ../../scripts/profile_stitcher.py check`。你会发现由于包装器使用了真实的 CLI 逻辑，它会正确找到 `stitcher-application` 作为工作区根目录，从而避免了对整个 monorepo 的无效扫描。
- **解决“非项目目录扫描”隐患**: 包装器的重构解决了分析脚本本身的问题，但 `stitcher` CLI 在非项目（但有 `.git`）目录下运行过慢的问题依然存在于 `Workspace` 的 `_discover_packages` 方法中。如果需要，我可以生成下一个计划，通过限制 `glob` 深度来彻底根治此架构隐患。
