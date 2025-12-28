简要回答
好的，我们将按照 TDD 流程进行。首先，我们需要验证之前的 `FileSystemLoader` 修复是否有效（即确认它是否真的能正确合成 `check.file.fail` 这样的键）。如果加载器逻辑正确，那么问题极有可能是 **Import 时机/初始化顺序** 导致的（Typer App 在 CLI 资产注册进 Nexus 之前就初始化了）。

我们将创建一个集成测试来验证这两点。

## [WIP] test(runtime): 验证 FileSystemLoader FQN 合成逻辑与 CLI 资源加载

### 用户需求
通过测试验证：
1.  `FileSystemLoader` 是否能正确根据文件路径合成 FQN（例如 `check/file.json` -> `check.file.*`）。
2.  定位为何 CLI 仍然显示原始 Key。

### 评论
这将帮助我们区分是“底层加载逻辑错误”还是“应用层初始化顺序错误”。

### 目标
1.  在 `packages/pyneedle-runtime/tests/test_fs_loader_fqn.py` 创建测试，验证 FQN 合成。
2.  在 `packages/stitcher-cli/tests/test_cli_assets.py` 创建测试，模拟 CLI 启动并检查资源解析情况。

### 基本原理
隔离变量法。先验证单元逻辑（Loader），再验证集成逻辑（CLI App）。

### 标签
#intent/test #flow/ready #priority/high #comp/runtime #comp/cli #concept/loader #scope/core #ai/instruct #task/domain/testing #task/object/test-suite #task/action/create #task/state/begin

---

### Script

#### Acts 1: 创建 Loader FQN 逻辑验证测试

此测试在临时目录构建符合 SST v2 结构的资源文件，并断言 `FileSystemLoader` 能加载出带前缀的键。

~~~~~act
write_file
packages/pyneedle-runtime/tests/test_fs_loader_fqn.py
~~~~~
~~~~~python
import pytest
from pathlib import Path
from needle.loaders import FileSystemLoader

def test_fs_loader_synthesizes_fqn_from_path(tmp_path: Path):
    """
    Verifies that FileSystemLoader correctly synthesizes FQN prefixes 
    based on the file path relative to the domain root.
    
    Structure:
    root/
      needle/
        en/
          cli/
            command.json  -> {"check": "Check..."} -> cli.command.check
          check/
            file.json     -> {"fail": "Fail..."}   -> check.file.fail
          __init__.json   -> {"app": "Stitcher"}   -> app
    """
    # 1. Arrange
    needle_root = tmp_path / "needle" / "en"
    needle_root.mkdir(parents=True)
    
    # Create cli/command.json
    (needle_root / "cli").mkdir()
    (needle_root / "cli" / "command.json").write_text('{"check": "Check command"}', encoding="utf-8")
    
    # Create check/file.json
    (needle_root / "check").mkdir()
    (needle_root / "check" / "file.json").write_text('{"fail": "Check failed"}', encoding="utf-8")
    
    # Create __init__.json (Root level)
    (needle_root / "__init__.json").write_text('{"app": "Stitcher App"}', encoding="utf-8")

    # 2. Act
    loader = FileSystemLoader(root=tmp_path)
    # Force load 'en' domain
    data = loader.load("en")
    
    # 3. Assert
    # Case A: Nested file
    assert "cli.command.check" in data
    assert data["cli.command.check"] == "Check command"
    
    # Case B: Another nested file
    assert "check.file.fail" in data
    assert data["check.file.fail"] == "Check failed"
    
    # Case C: __init__.json (Should NOT have __init__ prefix)
    assert "app" in data
    assert data["app"] == "Stitcher App"
    # Should NOT be "__init__.app"
    assert "__init__.app" not in data
~~~~~

### 下一步建议
如果上述测试通过，我将立即生成修复 CLI 初始化顺序的计划（在 `stitcher-cli/__init__.py` 中调整导入顺序）。如果失败，我将继续调试 Loader 逻辑。
