## [WIP] 对齐 pyrefly 的配置

你的怀疑完全正确！IDE 没问题了，这恰恰证明了我们上一轮的策略是**根本上正确**的：**Stitcher 生成的 `typings/` 存根目录解决了静态分析问题**。

IDE 中的 Pyright/Pylance 扩展正确地读取了 `pyproject.toml` 中的 `[tool.pyright]` 部分，找到了 `stubPath = "typings"`，所以它不再报错。

那么，为什么 `pyrefly check` 命令行工具仍然失败呢？

### 错误分析
你的怀疑一针见血：“我怀疑它没有理 pyright”。

问题在于配置的隔离性。`pyproject.toml` 中同时存在 `[tool.pyright]` 和 `[tool.pyrefly]` 两个部分。
-   **IDE (Pylance)**: 读取 `[tool.pyright]` 部分，我们在这里添加了 `stubPath = "typings"`，所以它能找到存根文件，工作正常。
-   **CLI (`pyrefly`)**: 当 `pyrefly` 启动时，它发现了专门为它准备的 `[tool.pyrefly]` 部分，于是它**只读取这个部分**，完全忽略了 `[tool.pyright]` 的内容。

我们上一轮的修改只给 `[tool.pyright]` 添加了 `stubPath`，而 `[tool.pyrefly]` 部分却被遗漏了。因此，命令行工具根本不知道 `typings/` 目录的存在，导致它依然像以前一样在分散的源文件中尝试解析，最终失败。

### 用户需求
让 `pyrefly check` 命令行工具的行为与 IDE 保持一致，使其能够识别并使用 `typings/` 目录下的存根文件，从而成功通过检查。

### 评论
这是一个典型的工具链配置陷阱。虽然 `pyrefly` 和 IDE 中的 Pyright 共享同一个核心引擎，但它们作为不同的前端工具，却读取了不同的配置块。解决方案就是确保两个配置块的意图保持同步。

### 目标
-   在 `pyproject.toml` 的 `[tool.pyrefly]` 部分中，添加 `stubPath = "typings"` 配置。

### 基本原理
通过在 `pyrefly` 自己的配置块中明确指定 `stubPath`，我们确保了无论通过哪个前端（IDE 或 CLI）调用 Pyright 引擎，它都能获得相同的、完整的信息，即“请在 `typings/` 目录中寻找类型存根”。这样，两个工具的行为就会完全统一。

### 标签
#intent/fix #flow/ready #priority/high
#comp/build #concept/config #scope/dx
#ai/instruct
#task/domain/testing #task/object/static-analysis #task/action/fix-config
#task/state/end #task/status/completed

---

### Script

#### Acts 1: 对齐 `pyrefly` 的配置
我们将 `stubPath` 添加到 `[tool.pyrefly]` 部分，使其与 `[tool.pyright]` 保持一致。

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml
[tool.pyrefly]
extraPaths = [
    "packages/stitcher-spec/src",
    "packages/stitcher-common/src",
    "packages/stitcher-scanner/src",
    "packages/stitcher-io/src",
    "packages/stitcher-config/src",
    "packages/stitcher-application/src",
    "packages/stitcher-cli/src",
    "packages/stitcher-test-utils/src",
    "packages/pyneedle-spec/src",
    "packages/pyneedle-pointer/src",
    "packages/pyneedle-nexus/src",
    "packages/pyneedle/src"
]
~~~~~
~~~~~toml
[tool.pyrefly]
stubPath = "typings"
extraPaths = [
    "packages/stitcher-spec/src",
    "packages-stitcher-common/src",
    "packages/stitcher-scanner/src",
    "packages/stitcher-io/src",
    "packages/stitcher-config/src",
    "packages/stitcher-application/src",
    "packages/stitcher-cli/src",
    "packages/stitcher-test-utils/src",
    "packages/pyneedle-spec/src",
    "packages/pyneedle-pointer/src",
    "packages/pyneedle-nexus/src",
    "packages/pyneedle/src"
]
~~~~~

### 下一步建议
这次修改应该能彻底解决问题。请再次运行 `pyrefly check`。

**长期建议**: 考虑将 `[tool.pyright]` 和 `[tool.pyrefly]` 的内容完全统一，甚至可以研究一下 `pyrefly` 是否有办法直接继承 `pyright` 的配置，以避免未来配置再次不同步。但目前，上述修改是最直接有效的。
