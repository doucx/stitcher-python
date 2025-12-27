简要回答：
是的，需要修改。目前根目录的 `pyproject.toml` 中 `extraPaths` 的配置存在两处不一致：
1.  **路径不匹配**：`needle` 目标的 `stub_package` 定义为 `packages/needle-stubs`，但 `extraPaths` 中写成了 `packages/pyneedle-stubs/src`。
2.  **结构适应**：随着我们引入了 `src/<namespace>-stubs` 的结构，将 `packages/xxx-stubs/src` 加入 `extraPaths` 是正确的，因为 Pyright 会在其中发现 `xxx-stubs` 目录并将其识别为 `xxx` 命名空间的类型源。

我将更新计划，包含对 `pyproject.toml` 的修正，然后完成提交。

## [COMMIT] fix: align root pyproject.toml with new stub structure and naming

### 用户需求
修正根目录 `pyproject.toml` 中的 `extraPaths` 配置，确保 IDE (Pyright/Pyrefly) 能够正确识别新生成的符合 PEP 561 规范的存根包。

### 评论
在 Monorepo 开发中，`extraPaths` 是 IDE 能够跨越包边界进行代码跳转和类型推断的关键。将 `pyneedle-stubs` 修正为 `needle-stubs` 解决了路径失效的问题。同时，保留指向 `src` 的路径是正确的，这符合检查器寻找 `X-stubs` 文件夹的逻辑。

### 目标
1.  修正 `tool.pyright.extraPaths` 中的 `pyneedle-stubs` 路径。
2.  修正 `tool.pyrefly.extraPaths` 中的 `pyneedle-stubs` 路径。
3.  完成所有变更的 Git 提交。

### 标签
#intent/tune #flow/ready #priority/medium #comp/build #scope/dx #ai/instruct #task/domain/build-system #task/object/root-pyproject #task/action/align-paths #task/state/end #task/status/completed

---

### Script

#### Acts 1: 修正根目录 pyproject.toml

将 `pyneedle-stubs` 统一更正为 `needle-stubs`。

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~python.old
    # Add the new stub packages' source directories
    "packages/stitcher-stubs/src",
    "packages/pyneedle-stubs/src",
]

[tool.pyrefly]
~~~~~
~~~~~python.new
    # Add the new stub packages' source directories
    "packages/stitcher-stubs/src",
    "packages/needle-stubs/src",
]

[tool.pyrefly]
~~~~~
~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~python.old
    # Add the new stub packages' source directories
    "packages/stitcher-stubs/src",
    "packages/pyneedle-stubs/src",
]
~~~~~
~~~~~python.new
    # Add the new stub packages' source directories
    "packages/stitcher-stubs/src",
    "packages/needle-stubs/src",
]
~~~~~

#### Acts 2: 暂存并提交所有变更

现在我们将所有修改过的文件和新创建的测试文件一并提交。

~~~~~act
git_add
pyproject.toml
packages/stitcher-application/src/stitcher/app/core.py
packages/stitcher-application/src/stitcher/app/services/stub_package_manager.py
packages/stitcher-test-utils/src/stitcher/test_utils/__init__.py
packages/stitcher-test-utils/src/stitcher/test_utils/harness.py
tests/integration/conftest.py
tests/integration/test_ide_proxy.py
tests/integration/test_stub_package_namespace.py
tests/integration/test_stub_package_pep561.py
tests/integration/test_stub_package_resolution.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
feat(stub): implement PEP 561 compliance and add integration test suite

This commit completes the transition to PEP 561 compliant stub packages and 
establishes a robust testing infrastructure.

Core changes:
- Logic: Renamed internal stub directories to `<namespace>-stubs` to support 
  shadowing without namespace pollution.
- Tooling: Introduced `VenvHarness` for automated environment isolation tests.
- Testing: Added E2E tests for stub resolution, namespace coexistence, 
  and IDE precedence verification (Stub > Source).
- DX: Updated root pyproject.toml extraPaths to ensure IDEs correctly 
  resolve the new stub package structure.
~~~~~

### 下一步建议
我们已经完成了存根包的核心逻辑和验证。下一步可以考虑：
- **版本自动化**：目前存根包的版本硬编码为 `0.1.0`。在生产环境中，我们通常希望存根包的版本与源包保持同步（或带上特定的后缀）。
- **CI/CD 验证**：在 GitHub Actions 中引入一个步骤，运行这些集成测试，确保未来的修改不会破坏存根包的兼容性。
