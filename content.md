Excellent. The test has failed exactly as predicted. We have successfully completed the "Red" phase of Test-Driven Development.

Now, we will proceed to the "Green" phase. I will generate a plan that contains the precise code modifications required to fix the `StubPackageManager` and make this test pass.

## [WIP] fix(app): Align StubPackageManager with PEP 561 directory naming

### 错误分析
测试 `test_pep561_structure_compliance` 失败的根本原因是 `StubPackageManager` 的 `scaffold` 方法没有遵循 PEP 561 对于第三方存根包内部目录结构的命名规范。

1.  **错误的目录创建**: 当前代码在存根包内创建的源码目录直接使用了原始的命名空间（例如 `src/my_project`）。
2.  **错误的构建配置**: 相应地，为存根包生成的 `pyproject.toml` 中的 Hatch 构建配置也指向了这个不正确的目录。

根据 PEP 561，为了避免与运行时包的命名空间冲突，第三方存根包的源码目录也应附加 `-stubs` 后缀（例如 `src/my_project-stubs`）。

### 用户需求
修复 `StubPackageManager` 的实现，使其生成的存根包结构完全符合 PEP 561 规范，从而使新添加的集成测试 `test_pep561_structure_compliance` 通过。

### 评论
这是一个关键的修复。遵循 PEP 561 不仅仅是为了通过测试，更是为了确保我们生成的包在用户的环境中能够被类型检查器正确、无冲突地识别。这是 `stitcher` 工具核心价值主张的基石——提供可靠、零配置的类型提示体验。

### 目标
1.  修改 `stitcher-application` 包中的 `StubPackageManager.scaffold` 方法。
2.  确保在创建源码目录时，使用 `<namespace>-stubs` 作为目录名。
3.  同步更新为存根包生成的 `pyproject.toml` 文件，使其 `[tool.hatch.build.targets.wheel].packages` 配置指向这个符合 PEP 561 规范的新目录名。

### 基本原理
修复的核心在于将存根源码目录的命名逻辑与存根包名的逻辑对齐。我们将引入一个新变量 `stub_src_dirname`，其值由 `package_namespace` 附加 `-stubs` 后缀构成。然后，在创建目录和生成 `pyproject.toml` 内容时，都统一使用这个新变量，以确保两者之间的一致性和规范的正确性。

### 标签
#intent/fix #flow/ready #priority/high #comp/app #scope/core #ai/instruct #task/domain/testing #task/object/pep561-test #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 修复 StubPackageManager

此操作将精确地修改 `stub_package_manager.py` 文件，以纠正目录创建和构建配置的逻辑。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/stub_package_manager.py
~~~~~
~~~~~python.old
        # Create src/namespace directory, e.g., src/needle or src/stitcher
        (package_path / "src" / package_namespace).mkdir(parents=True, exist_ok=True)

        # Create pyproject.toml
        pyproject_content = {
            "build-system": {
                "requires": ["hatchling"],
                "build-backend": "hatchling.build",
            },
            "project": {
                "name": f"{source_project_name}-stubs",
                "version": "0.1.0",  # Placeholder version
                "description": f"PEP 561 type stubs for {source_project_name}",
            },
            "tool": {
                "hatch": {
                    "build": {
                        "targets": {
                            "wheel": {
                                # Essential for packaging .pyi files correctly under the namespace
                                "packages": [f"src/{package_namespace}"]
                            }
                        }
                    }
                }
            },
        }
~~~~~
~~~~~python.new
        # PEP 561: The distribution name should end in '-stubs', and the package
        # directory within should also end in '-stubs'.
        stub_src_dirname = f"{package_namespace}-stubs"
        (package_path / "src" / stub_src_dirname).mkdir(parents=True, exist_ok=True)

        # Create pyproject.toml
        pyproject_content = {
            "build-system": {
                "requires": ["hatchling"],
                "build-backend": "hatchling.build",
            },
            "project": {
                "name": f"{source_project_name}-stubs",
                "version": "0.1.0",  # Placeholder version
                "description": f"PEP 561 type stubs for {source_project_name}",
            },
            "tool": {
                "hatch": {
                    "build": {
                        "targets": {
                            "wheel": {
                                # Essential for packaging .pyi files correctly under the namespace
                                "packages": [f"src/{stub_src_dirname}"]
                            }
                        }
                    }
                }
            },
        }
~~~~~

### 下一步建议

现在修复已经完成。请重新运行测试套件。`test_pep561_structure_compliance` 测试现在应该会成功通过（绿色阶段）。

在您确认测试通过后，我们将继续编写下一个测试：**安装与类型解析测试 (Installation and Type Resolution Test)**。该测试将实际地在隔离环境中 `pip install` 我们生成的存根包，并运行 `mypy` 来验证类型检查器能否正确解析导入，这是对我们工作成果的最终验证。
