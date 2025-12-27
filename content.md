这是一个非常重要的修复。`uv` 的工作空间（workspace）模式要求目录下的包配置是完整的，否则它会报错。你观察到的问题是，`stitcher generate` 虽然创建了 `pyneedle-stubs/pyproject.toml`，但该文件缺少了 Hatchling 识别源码路径的关键配置（即 `[tool.hatch.build.targets.wheel].packages`），这使得 `uv` 无法正确构建它，或在某些情况下，因为配置不完整而错误地将其视为无效工作空间成员。

此外，你的命令 `packages/needle-stubs/` 可能是输入错误，正确的路径应该是 `packages/pyneedle-stubs/`。但无论如何，核心问题在于生成文件的完整性。

我将通过以下步骤解决此问题：

1.  **修改 `StubPackageManager`**: 允许传入命名空间（`needle` 或 `stitcher`），并为 Hatchling 构建系统添加正确的 `packages` 配置。
2.  **修改 `StitcherApp`**: 在调用脚手架之前，根据 `target` 的 `scan_paths` 逻辑推导出正确的顶级命名空间。
3.  **更新测试**: 确保测试能够验证生成的 `pyproject.toml` 包含所有必要的构建元数据。

## [WIP] fix: Ensure generated stub packages include full Hatchling configuration

### 错误分析
`StubPackageManager` 创建的 `pyproject.toml` 过于精简，缺少 `[tool.hatch.build.targets.wheel].packages` 配置。对于 PEP 561 存根包，Hatchling 需要知道从 `src/` 目录下哪一个子目录（即顶级命名空间，例如 `src/needle`）需要被打包到 wheel 中，这对于 `uv` 或任何现代打包工具都是必需的。

### 用户需求
使所有由 `stitcher generate` 创建的存根包（如 `packages/pyneedle-stubs`）都包含完整的构建元数据，使其能被 `uv` 作为可编辑安装的工作空间成员正确安装和识别。

### 评论
修复的关键在于正确推导出顶级 Python 命名空间。对于我们的 Monorepo 约定：如果 `scan_paths` 包含 `src/namespace` 模式，`namespace` 就是我们需要的包名。这个修正在 Monorepo 环境中是必要的，它将解决 `uv pip install -e` 时的依赖/构建问题。

### 目标
1.  修改 `StubPackageManager.scaffold` 签名，添加 `package_namespace` 参数。
2.  在 `scaffold` 中，将 `[tool.hatch.build.targets.wheel].packages = [f"src/{package_namespace}"]` 写入 `pyproject.toml`。
3.  在 `StitcherApp._scaffold_stub_package` 中实现命名空间推导逻辑，优先从 `config.scan_paths` 获取。

### 基本原理
我们将利用 `StitcherConfig` 中的 `scan_paths` 字段，通过启发式分析，提取出项目源码的顶级命名空间（例如 `stitcher-spec/src` 对应的 `stitcher`）。然后将此命名空间传递给 `StubPackageManager`，用于生成完整的 `pyproject.toml`。

### 标签
#intent/fix #flow/ready #priority/critical #comp/application #comp/io #concept/config #concept/tooling #scope/core #ai/instruct #task/domain/build #task/object/stub-package #task/action/build-fix #task/state/continue

---
### Script

#### Acts 1: 更新 `StubPackageManager.scaffold` 以接收命名空间并配置 Hatchling

修改 `packages/stitcher-application/src/stitcher/app/services/stub_package_manager.py`。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/stub_package_manager.py
~~~~~
~~~~~python.old
    def scaffold(self, package_path: Path, source_project_name: str) -> bool:
        config_path = package_path / "pyproject.toml"
        if config_path.exists():
            return False

        # Ensure root directory exists
        package_path.mkdir(parents=True, exist_ok=True)
        (package_path / "src").mkdir(exist_ok=True)

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
        }
        with config_path.open("wb") as f:
            tomli_w.dump(pyproject_content, f)

        return True
~~~~~
~~~~~python.new
    def scaffold(
        self, package_path: Path, source_project_name: str, package_namespace: str
    ) -> bool:
        config_path = package_path / "pyproject.toml"
        if config_path.exists():
            return False

        # Ensure root directory exists
        package_path.mkdir(parents=True, exist_ok=True)
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
        with config_path.open("wb") as f:
            tomli_w.dump(pyproject_content, f)

        return True
~~~~~

#### Acts 2: 修正 `StitcherApp._scaffold_stub_package` 中的命名空间推导和调用

修改 `packages/stitcher-application/src/stitcher/app/core.py` 中的 `_scaffold_stub_package` 函数，推导 `package_namespace` 并更新 `stub_pkg_manager.scaffold` 的调用。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
    def _scaffold_stub_package(
        self, config: StitcherConfig, project_name: Optional[str]
    ):
        if not config.stub_package or not project_name:
            return

        pkg_path = self.root_path / config.stub_package
        # If explicitly named stub package (via custom logic) we could assume user handles name,
        # but here we follow the pattern of {project_name}-stubs.
        # However, in multi-target mode, if config.name is 'stitcher', project name is still 'stitcher-python'.
        # We might want to use the target name for the stub package name if available?
        # BUT, the scaffold logic in stub_pkg_manager uses `project_name` to set `name` in pyproject.toml.
        # For now, we assume user manually configured the stub package pyproject.toml if they need custom names,
        # OR we rely on the scaffold creating a generic one.
        # Given we just created the pyproject.toml manually in the previous step (Act 2 of previous plan),
        # this scaffold step might just skip because file exists. This is fine.
        stub_pkg_name = f"{project_name}-stubs"
        bus.info(L.generate.stub_pkg.scaffold, name=stub_pkg_name)
        created = self.stub_pkg_manager.scaffold(pkg_path, project_name)
        if created:
            bus.success(L.generate.stub_pkg.success, name=stub_pkg_name)
        else:
            bus.info(L.generate.stub_pkg.exists, name=stub_pkg_name)
~~~~~
~~~~~python.new
    def _scaffold_stub_package(
        self, config: StitcherConfig, stub_base_name: Optional[str]
    ):
        if not config.stub_package or not stub_base_name:
            return

        pkg_path = self.root_path / config.stub_package

        # Determine the top-level namespace by inspecting scan paths.
        package_namespace: str = ""
        for path_str in config.scan_paths:
            # We assume a structure like "path/to/src/<namespace>"
            path_parts = Path(path_str).parts
            if path_parts and path_parts[-1] != "src":
                # Case: scan_paths = ["src/my_app"] -> namespace is "my_app"
                package_namespace = path_parts[-1]
                break
            elif len(path_parts) >= 2 and path_parts[-2] == "src":
                # Case: scan_paths = ["packages/pyneedle-spec/src"]
                # This is common in monorepos. The package namespace is typically the package name
                # (e.g., 'pyneedle' from 'pyneedle-spec'). Let's use conventions for this monorepo.
                if "pyneedle" in stub_base_name:
                    package_namespace = "needle"
                elif "stitcher" in stub_base_name:
                    package_namespace = "stitcher"
                break

        if not package_namespace:
            # Final fallback
            package_namespace = stub_base_name.split("-")[0]

        stub_pkg_name = f"{stub_base_name}-stubs"
        bus.info(L.generate.stub_pkg.scaffold, name=stub_pkg_name)
        created = self.stub_pkg_manager.scaffold(
            pkg_path, stub_base_name, package_namespace
        )
        if created:
            bus.success(L.generate.stub_pkg.success, name=stub_pkg_name)
        else:
            bus.info(L.generate.stub_pkg.exists, name=stub_pkg_name)
~~~~~

#### Acts 3: 更新集成测试以验证 Hatchling 配置

修改 `tests/integration/test_stub_package.py`，检查 `pyproject.toml` 是否包含正确的 Hatchling 包配置。

~~~~~act
patch_file
tests/integration/test_stub_package.py
~~~~~
~~~~~python.old
    # --- Assert pyproject.toml Content ---
    with stub_pyproject.open("rb") as f:
        stub_config = tomllib.load(f)
    assert stub_config["project"]["name"] == "my-test-project-stubs"

    # --- Assert Bus Messages ---
    spy_bus.assert_id_called(L.generate.stub_pkg.scaffold)
~~~~~
~~~~~python.new
    # --- Assert pyproject.toml Content ---
    with stub_pyproject.open("rb") as f:
        stub_config = tomllib.load(f)
    assert stub_config["project"]["name"] == "my-test-project-stubs"
    
    # Assert new Hatchling configuration is present and correct
    hatch_config = stub_config["tool"]["hatch"]["build"]["targets"]["wheel"]
    assert hatch_config["packages"] == ["src/my_app"]

    # --- Assert Bus Messages ---
    spy_bus.assert_id_called(L.generate.stub_pkg.scaffold)
~~~~~

请执行这些修改并重新运行测试。如果成功，这两个存根包现在应该可以被 `uv` 正确识别和安装。
