You've caught the bug perfectly. My apologies, the last refactoring plan correctly updated the runtime logic but failed to update the corresponding test, creating a mismatch. The test is now testing the old reality against the new code.

Your analysis is spot on. The test failed because:
1.  I refactored the `Needle` runtime to look for locales in a path like `<root_path>/locales/<lang>/`.
2.  The test `test_needle_loading_and_fallback` is still creating a mock directory at `<root_path>/stitcher/needle/<lang>/`.
3.  Consequently, the `Needle` instance running in the test scans an empty directory, finds no keys, and correctly falls back to identity (`'cli.hello'`), causing the assertion to fail.

The fix is to update the test to build the correct mock file structure that the new runtime expects.

## [WIP] fix: Align Needle runtime test with new SST structure

### 错误分析
测试 `test_needle_loading_and_fallback` 失败的根本原因是，它所构建的模拟文件系统结构已经过时。在之前的重构中，`Needle` 运行时的资源加载路径被修改为 `.../locales/<lang>/`，以适应在 `stitcher-common` 中的新位置。然而，测试用例仍然在 `.../stitcher/needle/<lang>/` 路径下创建模拟文件。这导致运行时在测试期间扫描了一个空目录，未能加载任何消息，因此所有 `get()` 调用都触发了“身份回退”机制，返回了键本身。

### 用户需求
修复失败的单元测试，使其能够正确验证 `Needle` 运行时的加载和三级降级逻辑。

### 评论
这是一个典型的重构后遗症，也是测试驱动开发价值的体现。测试的失败准确地指出了实现与规范之间的脱节。通过修复测试，我们不仅能让CI通过，更能确保我们的测试套件与最新的架构设计保持一致，成为可靠的质量保障。

### 目标
1.  修改 `packages/stitcher-needle/tests/test_runtime.py`。
2.  更新测试中的 mock 文件系统布局，使其从 `stitcher/needle/` 结构变为 `locales/` 结构。
3.  调整测试中的 JSON 文件名和内容，以匹配上一步中定义的、基于 FQN 的新 SST 规范。

### 基本原理
我们将直接修改测试代码，使其与 `Needle` 运行时的当前实现保持同步。修复必须在测试端，因为运行时的代码是符合新架构的正确实现。这次修复将使测试用例重新成为 `Needle` 功能的有效验证工具。

### 标签
#intent/fix #flow/ready #priority/high #comp/runtime #comp/tests #scope/core #ai/instruct #task/domain/runtime #task/object/sst-migration #task/action/implementation #task/state/continue

---
### Script

#### Acts 1: 更新 `test_runtime.py` 以匹配新架构

我们将修改测试，使其创建 `locales/` 目录结构，并使用 FQN 作为 JSON 文件的键。

~~~~~act
patch_file
packages/stitcher-needle/tests/test_runtime.py
~~~~~
~~~~~python.old
def test_needle_loading_and_fallback(tmp_path: Path):
    # 1. Setup SST structure
    root = tmp_path
    needle_dir = root / "stitcher" / "needle"
    
    # English (Default)
    en_dir = needle_dir / "en"
    en_dir.mkdir(parents=True)
    
    # en/cli.json
    (en_dir / "cli.json").write_text(json.dumps({
        "hello": "Hello World",
        "only_en": "I am English"
    }))
    
    # en/auth/login.json
    (en_dir / "auth").mkdir()
    (en_dir / "auth" / "login.json").write_text(json.dumps({
        "fail": "Login Failed"
    }))

    # Chinese (Target)
    zh_dir = needle_dir / "zh"
    zh_dir.mkdir(parents=True)
    
    # zh/cli.json
    (zh_dir / "cli.json").write_text(json.dumps({
        "hello": "你好世界"
    }))

    # 2. Initialize Runtime
    rt = Needle(root_path=root, default_lang="en")

    # 3. Test: Target Language Hit
    # L.cli.hello -> "你好世界" (in zh)
    assert rt.get(L.cli.hello, lang="zh") == "你好世界"

    # 4. Test: Fallback to Default Language
    # L.cli.only_en -> "I am English" (missing in zh, fallback to en)
    assert rt.get(L.cli.only_en, lang="zh") == "I am English"

    # 5. Test: Namespace Flattening
    # L.auth.login.fail -> "Login Failed"
    assert rt.get(L.auth.login.fail) == "Login Failed"

    # 6. Test: Ultimate Identity Fallback
    # L.unknown.key -> "unknown.key"
    assert rt.get(L.unknown.key) == "unknown.key"
~~~~~
~~~~~python.new
def test_needle_loading_and_fallback(tmp_path: Path):
    # 1. Setup SST structure according to the NEW specification
    root = tmp_path
    locales_dir = root / "locales"
    
    # English (Default)
    en_dir = locales_dir / "en"
    (en_dir / "cli").mkdir(parents=True)
    (en_dir / "auth").mkdir()

    (en_dir / "cli" / "main.json").write_text(json.dumps({
        "cli.hello": "Hello World",
        "cli.only_en": "I am English"
    }))
    
    (en_dir / "auth" / "login.json").write_text(json.dumps({
        "auth.login.fail": "Login Failed"
    }))

    # Chinese (Target)
    zh_dir = locales_dir / "zh"
    (zh_dir / "cli").mkdir(parents=True)
    
    (zh_dir / "cli" / "main.json").write_text(json.dumps({
        "cli.hello": "你好世界"
    }))

    # 2. Initialize Runtime
    # The runtime will look for a `locales` dir inside the provided root_path
    rt = Needle(root_path=root, default_lang="en")

    # 3. Test: Target Language Hit
    # L.cli.hello should be found in zh's cli/main.json
    assert rt.get(L.cli.hello, lang="zh") == "你好世界"

    # 4. Test: Fallback to Default Language
    # L.cli.only_en is missing in zh, should fallback to en
    assert rt.get(L.cli.only_en, lang="zh") == "I am English"

    # 5. Test: FQN loading from subdirectories
    # L.auth.login.fail should be found in en's auth/login.json
    assert rt.get(L.auth.login.fail) == "Login Failed"

    # 6. Test: Ultimate Identity Fallback
    # L.unknown.key is not in any file
    assert rt.get(L.unknown.key) == "unknown.key"
~~~~~
