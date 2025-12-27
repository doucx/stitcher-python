You've found another excellent point. My apologies again. The traceback indicates a mismatch between the file opening mode and what the `tomli_w` library expects. I opened the file in text mode, but the library wants to write bytes.

I will correct this now.

## [WIP] fix(application): Use binary mode for writing TOML files

### 错误分析
测试 `test_generate_with_stub_package_creates_correct_structure` 失败的根本原因是 `tomli_w.dump` 函数期望接收一个以二进制写模式 (`"wb"`) 打开的文件句柄，但我的实现 (`StubPackageManager` 和 `WorkspaceFactory`) 都使用了文本写模式 (`"w"`)。

`tomli_w` 库内部会自行处理字符串到 UTF-8 字节的编码，因此它需要一个接受字节的流。当它尝试将编码后的字节写入一个只接受字符串的文本流时，Python 解释器正确地抛出了 `TypeError`。

### 用户需求
修复在写入 `pyproject.toml` 文件时发生的 `TypeError`，确保所有 TOML 文件的生成都使用正确的二进制文件模式。

### 评论
这是一个常见的 I/O 错误，即文件打开模式与写入的数据类型不匹配。此修复将使我们的文件处理逻辑与所依赖的库（`tomli_w`）的行为保持一致，确保了工具的健壮性。

### 目标
1.  修改 `stitcher.app.services.stub_package_manager.StubPackageManager.scaffold`，使用二进制写模式 (`"wb"`) 创建存根包的 `pyproject.toml`。
2.  修改 `stitcher.test_utils.workspace.WorkspaceFactory.build`，同样使用二进制写模式 (`"wb"`) 创建测试工作区中的 `pyproject.toml`。

### 基本原理
`tomli_w.dump` 函数负责将 Python 字典序列化为符合 TOML 规范的 UTF-8 字节流。因此，调用该函数的代码必须提供一个以二进制模式打开的文件句柄，以允许其直接写入字节。我们将修改所有 `tomli_w.dump` 的调用点，确保文件以 `"wb"` 模式打开。

### 标签
#intent/fix #flow/ready #priority/high #comp/application #comp/tests #scope/core #ai/instruct #task/domain/testing #task/object/broken-tests #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 修正 `StubPackageManager`

首先，我们修复存根包管理器的文件写入模式。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/stub_package_manager.py
~~~~~
~~~~~python.old
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
        }
        with config_path.open("w", encoding="utf-8") as f:
            tomli_w.dump(pyproject_content, f)

        return True
~~~~~
~~~~~python.new
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
        }
        with config_path.open("wb") as f:
            tomli_w.dump(pyproject_content, f)

        return True
~~~~~

#### Acts 2: 修正 `WorkspaceFactory`

接着，我们修复测试工具 `WorkspaceFactory` 中相应的逻辑，以防止此问题在其他测试中出现。

~~~~~act
patch_file
packages/stitcher-test-utils/src/stitcher/test_utils/workspace.py
~~~~~
~~~~~python.old
            content = file_spec["content"]

            if fmt == "toml":
                content_to_write = tomli_w.dumps(content)
            elif fmt == "yaml":
                content_to_write = yaml.dump(content, indent=2)
            else:  # raw
                content_to_write = content

            output_path.write_text(content_to_write, encoding="utf-8")

        return self.root_path
~~~~~
~~~~~python.new
            content = file_spec["content"]
            fmt = file_spec["format"]

            if fmt == "toml":
                with output_path.open("wb") as f:
                    tomli_w.dump(content, f)
            else:
                content_to_write = ""
                if fmt == "yaml":
                    content_to_write = yaml.dump(content, indent=2)
                else:  # raw
                    content_to_write = content
                output_path.write_text(content_to_write, encoding="utf-8")

        return self.root_path
~~~~~
