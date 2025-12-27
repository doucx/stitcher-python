简要回答：
好的，我们将扩展 `test_pyright_resolves_types_from_stubs` 测试。通过剥离 Stub 中的类型并重新安装，断言 Pyright 的解析结果变为 `Unknown`。这利用了 Type Checker "Stub 遮蔽源码" (Stub shadows implementation) 的特性：如果 Stub 存在但无类型，检查器应报告未知，而不是回退读取源码中的类型。

## [WIP] test: 验证 Pyright 优先使用 Stub 而非源码

### 用户需求
在现有的 IDE Proxy 集成测试通过后，增加一个步骤：剥离生成的 `.pyi` 文件中的类型注解，重新安装，并验证 Pyright 不再能解析出类型。这将确凿地证明 Pyright 正在读取 Stub 文件，而不是源码。

### 评论
这是一个非常严谨且必要的验证步骤。它排除了 "Pyright 只是因为读取了源码中的类型才通过测试" 的假阳性可能性，确保了 Stitcher 生成的 Stub 包确实在起作用。

### 目标
1.  扩展 `tests/integration/test_ide_proxy.py`。
2.  在第一次成功断言后，修改生成的 `.pyi` 文件，移除 `-> int`。
3.  强制重新安装 Stub 包。
4.  再次运行 Pyright 并断言返回类型为 `Unknown`。

### 基本原理
根据 PEP 561 和主流类型检查器（如 Pyright/Mypy）的解析规则，如果一个包存在对应的 Stub 包（或者内部包含 `.pyi`），类型检查器将**只**查看 `.pyi` 文件中的定义。如果 `.pyi` 中没有类型注解（即使源码中有），检查器也应将其视为 `Any` 或 `Unknown`。这个行为特性正是我们验证 Stub 优先级的依据。

### 标签
#intent/test #flow/ready #priority/medium #comp/tests #concept/state #scope/dx #ai/instruct #task/domain/testing #task/object/ide-proxy-verification #task/action/extend-test #task/state/continue

---

### Script

#### Acts 1: 扩展测试用例

我们将在现有的断言之后追加逻辑：修改 `.pyi` 文件 -> 强制重新安装 -> 再次检查。

~~~~~act
patch_file
tests/integration/test_ide_proxy.py
~~~~~
~~~~~python.old
    assert (
        'Type of "instance.get_id()" is "int"' in result.stdout
    ), f"Pyright did not resolve the return type correctly.\n{diagnostic_info}"
~~~~~
~~~~~python.new
    assert (
        'Type of "instance.get_id()" is "int"' in result.stdout
    ), f"Pyright did not resolve the return type correctly.\n{diagnostic_info}"

    # --- Part 2: Verify Precedence (Stub > Source) ---

    # 8. Modify the stub file to remove the return type annotation.
    # We locate the generated .pyi file in the source stub package directory.
    # Namespace is "ide_proxy", so dir is "ide_proxy-stubs".
    pyi_path = stub_pkg_path / "src" / "ide_proxy-stubs" / "models.pyi"
    assert pyi_path.exists()

    # Replace "-> int" with "" (stripping type info)
    original_pyi_content = pyi_path.read_text()
    stripped_pyi_content = original_pyi_content.replace("-> int", "")
    pyi_path.write_text(stripped_pyi_content)

    # 9. Reinstall the modified stub package to update site-packages.
    # We use --force-reinstall to ensure pip updates the files.
    isolated_env.install("--force-reinstall", str(stub_pkg_path))

    # 10. Run Pyright again.
    # Now that the stub has no return type, Pyright should treat it as Unknown/Any,
    # IGNORING the source code which still has "-> int".
    # This proves Pyright is indeed reading the .pyi file, not the .py file.
    result_stripped = isolated_env.run_pyright_check(
        Path("."), verbose=True, cwd=client_project_dir
    )

    assert result_stripped.returncode == 0
    # Pyright default for unannotated return is Unknown
    assert 'Type of "instance.get_id()" is "Unknown"' in result_stripped.stdout, (
        f"Pyright should have fallen back to Unknown after stripping stubs.\n"
        f"This implies it might be reading source code instead of stubs.\n"
        f"STDOUT:\n{result_stripped.stdout}"
    )
~~~~~

### 下一步建议
运行此扩展后的测试。如果通过，我们就可以非常有信心地宣称 Stitcher 生成的 Stub 包能够正确地被 IDE/类型检查器消费，并且具有预期的优先级。
