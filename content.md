好的，我们开始执行路线图中的阶段 2.1：增强配置模型。

根据路线图的描述，我们需要在 `StitcherConfig` 中增加一个 `peripheral_paths` 字段，并更新配置加载逻辑以支持它。这将为后续统一 `refactor` 和 `scanner` 的文件发现机制奠定基础。

我将生成一个计划来执行这些修改。

## [WIP] feat: Add peripheral_paths to StitcherConfig

### 用户需求

执行路线图中的任务 2.1，增强 `stitcher-config` 包中的配置模型。具体来说，需要为 `StitcherConfig` 添加一个新的 `peripheral_paths` 字段，用于定义项目中的“周边”源码区域（如 `examples/`, `scripts/`），并更新加载逻辑以从 `pyproject.toml` 中解析此配置。

### 评论

这是实现“配置与发现统一”目标的关键一步。通过将 `peripheral_paths` 纳入核心配置模型，我们确保了系统的所有组件（无论是 `application` 还是 `refactor`）都将基于同一份真理来源（Single Source of Truth）来理解项目的文件结构，这彻底杜绝了两者之间可能出现的视图不一致问题。

### 目标

1.  在 `stitcher.config.loader.StitcherConfig` 数据类中添加 `peripheral_paths: List[str]` 字段。
2.  更新 `load_config_from_path` 函数，使其能够正确地从 `pyproject.toml` 的 `[tool.stitcher.targets.<name>]` 或 `[tool.stitcher]` 中解析 `peripheral_paths` 列表。

### 基本原理

我们将直接修改 `StitcherConfig` 数据类，为其增加一个新字段。随后，在 `load_config_from_path` 函数中，我们将分别在处理多目标（`targets`）配置和单目标（传统）配置的逻辑分支中，添加对 `peripheral_paths` 的解析。这确保了无论是哪种配置模式，新字段都能被正确加载，保证了向后兼容性和功能的完整性。

### 标签

#intent/build #flow/ready #priority/high #comp/config #concept/config #scope/api #ai/instruct #task/domain/architecture #task/object/config-unification #task/action/implementation #task/state/begin

---

### Script

#### Acts 1: 修改 stitcher-config

我们将分三步修改 `loader.py`：首先为 `StitcherConfig` 数据类添加 `peripheral_paths` 字段，然后分别为多目标和单目标配置模式下的实例化逻辑添加对该字段的解析。

首先，在 `StitcherConfig` 中添加新字段。

~~~~~act
patch_file
packages/stitcher-config/src/stitcher/config/loader.py
~~~~~
~~~~~python.old
    stub_path: Optional[str] = None
    stub_package: Optional[str] = None
    docstring_style: str = "raw"
~~~~~
~~~~~python.new
    stub_path: Optional[str] = None
    stub_package: Optional[str] = None
    docstring_style: str = "raw"
    peripheral_paths: List[str] = field(default_factory=list)
~~~~~

然后，更新多目标配置的加载逻辑。

~~~~~act
patch_file
packages/stitcher-config/src/stitcher/config/loader.py
~~~~~
~~~~~python.old
                    stub_path=target_data.get("stub_path"),
                    stub_package=target_data.get("stub_package"),
                    docstring_style=target_data.get("docstring_style", "raw"),
                )
            )
~~~~~
~~~~~python.new
                    stub_path=target_data.get("stub_path"),
                    stub_package=target_data.get("stub_package"),
                    docstring_style=target_data.get("docstring_style", "raw"),
                    peripheral_paths=target_data.get("peripheral_paths", []),
                )
            )
~~~~~

最后，更新单目标（传统）配置的加载逻辑。

~~~~~act
patch_file
packages/stitcher-config/src/stitcher/config/loader.py
~~~~~
~~~~~python.old
        configs.append(
            StitcherConfig(
                scan_paths=stitcher_data.get("scan_paths", []),
                plugins=plugins,
                stub_path=stitcher_data.get("stub_path"),
                stub_package=stitcher_data.get("stub_package"),
                docstring_style=stitcher_data.get("docstring_style", "raw"),
            )
        )
~~~~~
~~~~~python.new
        configs.append(
            StitcherConfig(
                scan_paths=stitcher_data.get("scan_paths", []),
                plugins=plugins,
                stub_path=stitcher_data.get("stub_path"),
                stub_package=stitcher_data.get("stub_package"),
                docstring_style=stitcher_data.get("docstring_style", "raw"),
                peripheral_paths=stitcher_data.get("peripheral_paths", []),
            )
        )
~~~~~

### 下一步建议

我们已经成功扩展了配置模型。根据路线图，下一个合乎逻辑的步骤是执行 **任务 2.2：统一工作区构建**。

这将涉及修改 `stitcher.refactor.engine.Workspace`，使其：
1.  **停止**自行解析 `pyproject.toml`。
2.  **转而**接受一个 `StitcherConfig` 对象作为其构造函数的参数。
3.  利用 `StitcherConfig` 中的 `scan_paths` 和我们刚刚添加的 `peripheral_paths` 来构建其内部的文件视图。

这将彻底消除 `refactor` 包中重复的配置解析逻辑，完成本阶段的核心目标。如果你同意，我将生成执行此项重构的计划。
