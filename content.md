好的，我来修复这个测试失败的问题。

这是一个典型的渲染器格式化错误。测试期望生成的 Google 风格文档字符串中的条目（如 `Args` 和 `Returns` 下的内容）需要有额外的缩进，但实际生成的代码缺少了这个缩进。

我将修改 `GoogleDocstringRenderer` 来添加正确的缩进。

## [WIP] fix: 修正 GoogleDocstringRenderer 中的缩进问题

### 错误分析

测试 `test_generate_with_google_style_renders_correctly` 失败，原因是 `GoogleDocstringRenderer` 在生成文档字符串时，没有为 `Args` 和 `Returns` 等节（section）中的条目（item）添加必要的 4 空格前缀缩进。

从 Pytest 的差异报告中可以看出：
-   **预期 (Expected)**: 条目行前有 8 个空格（4 来自 docstring 的整体缩进 + 4 来自条目自身的缩进）。
    ```
    Args:
        value (int): The input integer.
    ```
-   **实际 (Actual)**: 条目行前只有 4 个空格（仅 docstring 的整体缩进），导致其与节标题 `Args:` 左对齐，这不符合 Google 风格。
    ```
    Args:
    value (int): The input integer.
    ```
问题的根源在于 `packages/stitcher-python-adapter/src/stitcher/adapter/python/docstring/renderers.py` 文件中的 `_render_section` 方法，它在构建条目行时未添加前导空格。

### 用户需求

修复 `test_generate_with_google_style_renders_correctly` 测试，确保 `stitcher generate` 命令在 `docstring_style = "google"` 配置下能生成格式正确的 `.pyi` 文件。

### 评论

这是一个直接的 bug 修复。修正这个问题将确保生成的类型存根文件不仅在功能上正确，而且在格式上也符合标准，提高了代码的可读性和一致性。

### 目标

修改 `GoogleDocstringRenderer._render_section` 方法，为每个 `DocstringItem` 生成的行添加一个 4 空格的缩进。

### 基本原理

解决方案是在 `_render_section` 方法的 `elif isinstance(content, list):` 分支中，为每个生成的条目行（`line`）前置一个包含 4 个空格的 `indent` 字符串。这将使渲染后的输出与测试用例中 `dedent` 处理后的预期字符串完全匹配。

### 标签

#intent/fix #flow/ready #priority/high #comp/tests #task/domain/testing #task/object/docstring-renderer #task/action/bug-fix #task/state/begin

---

### Script

#### Acts 1: 修正 GoogleDocstringRenderer 的缩进逻辑

我将直接修改 `renderers.py` 文件，为 Google 风格文档字符串的条目添加所需的缩进。

~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/docstring/renderers.py
~~~~~
~~~~~python.old
        elif isinstance(content, list):
            for item in content:
                if not isinstance(item, DocstringItem): continue
                prefix = ""
                if item.name:
                    prefix = f"{item.name}"
                    if item.annotation: prefix += f" ({item.annotation})"
                elif item.annotation:
                    prefix = f"{item.annotation}"

                if prefix:
                    lines.append(f"{prefix}: {item.description}" if item.description else prefix)
                elif item.description:
                    lines.append(item.description)
~~~~~
~~~~~python.new
        elif isinstance(content, list):
            for item in content:
                if not isinstance(item, DocstringItem): continue
                prefix = ""
                if item.name:
                    prefix = f"{item.name}"
                    if item.annotation: prefix += f" ({item.annotation})"
                elif item.annotation:
                    prefix = f"{item.annotation}"

                indent = "    "
                if prefix:
                    line = f"{indent}{prefix}: {item.description}" if item.description else f"{indent}{prefix}"
                    lines.append(line)
                elif item.description:
                    lines.append(f"{indent}{item.description}")
~~~~~

### 下一步建议

代码修改已完成。现在，请运行测试套件以验证此修复是否解决了问题，并且没有引入新的回归。
