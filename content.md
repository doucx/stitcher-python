你的分析非常准确。在多项目协作的开发阶段，`uv` 需要明确的 `sources` 配置来将外部项目（`Needle`）的包映射到本地路径。

根据 `ADAP v1.0` 协议，我们需要消除这种“环境不确定性”。我将修改根目录和 `stitcher-common` 的配置文件，将 `pyneedle-*` 系列包指向你的 `Needle` 仓库。

## [WIP] chore(env): 配置 uv 外部源码映射以支持 pyneedle-bus

### 用户需求
配置 `uv` 的源码映射（Sources），使 `Stitcher` 项目能够正确加载位于 `../Needle` 目录下的 `pyneedle-bus` 及其依赖项。

### 评论
由于 `pyneedle-bus` 尚未发布到公共仓库，且其本身依赖于 `Needle` 项目内的其他子包（`spec`, `pointer`, `runtime`），我们必须在 `uv` 配置中建立一条完整的“本地路径链”。

### 目标
1.  在根目录 `pyproject.toml` 中添加 `pyneedle-bus`、`pyneedle-runtime`、`pyneedle-pointer` 和 `pyneedle-spec` 的路径映射。
2.  在 `packages/stitcher-common/pyproject.toml` 中同步添加 `pyneedle-bus` 的源码映射。

### 基本原理
`uv` 的 `[tool.uv.sources]` 块允许我们将依赖项重定向到本地相对路径。
*   从根目录出发，路径为 `../Needle/packages/pyneedle-*`。
*   从 `packages/stitcher-common` 出发，路径为 `../../../Needle/packages/pyneedle-*`。

我们将配置所有 4 个核心包，以确保 `uv` 在解析 `pyneedle-bus` 的依赖树时不会去查询远程仓库。

### 标签
#intent/tooling #flow/ready #priority/high 
#comp/build #scope/dx
#ai/instruct
#task/domain/environment #task/object/uv-sources #task/action/configure #task/state/continue

---

### Script

#### Acts 1: 配置根目录的源码映射

我们将这些外部依赖注册到工作区根目录。

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml.old
[tool.uv.sources]
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
stitcher-application = { workspace = true }
stitcher-cli = { workspace = true }
stitcher-stubgen = { workspace = true }
stitcher-test-utils = { workspace = true }
stitcher-refactor = { workspace = true }
stitcher-index = { workspace = true }
stitcher-workspace = { workspace = true }
stitcher-lang-python = { workspace = true }
stitcher-lang-sidecar = { workspace = true }
stitcher-analysis = { workspace = true }
stitcher-bus = { workspace = true }
~~~~~
~~~~~toml.new
[tool.uv.sources]
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
stitcher-application = { workspace = true }
stitcher-cli = { workspace = true }
stitcher-stubgen = { workspace = true }
stitcher-test-utils = { workspace = true }
stitcher-refactor = { workspace = true }
stitcher-index = { workspace = true }
stitcher-workspace = { workspace = true }
stitcher-lang-python = { workspace = true }
stitcher-lang-sidecar = { workspace = true }
stitcher-analysis = { workspace = true }
stitcher-bus = { workspace = true }

# External Needle dependencies
pyneedle-bus = { path = "../Needle/packages/pyneedle-bus", editable = true }
pyneedle-runtime = { path = "../Needle/packages/pyneedle-runtime", editable = true }
pyneedle-pointer = { path = "../Needle/packages/pyneedle-pointer", editable = true }
pyneedle-spec = { path = "../Needle/packages/pyneedle-spec", editable = true }
~~~~~

#### Acts 2: 配置 `stitcher-common` 的源码映射

为了确保包级别的独立解析也能成功，我们在 `stitcher-common` 中也添加对应的映射。

~~~~~act
patch_file
packages/stitcher-common/pyproject.toml
~~~~~
~~~~~toml.old
[tool.uv.sources]
~~~~~
~~~~~toml.new
[tool.uv.sources]
pyneedle-bus = { path = "../../../Needle/packages/pyneedle-bus", editable = true }
~~~~~

### 下一步建议
配置完成后，请再次尝试运行 `uv run pytest packages --prerelease=allow`。如果依赖解析成功，我们将继续执行 **全局清理与替换**，将代码中所有对旧 `bus` 的引用重定向到新入口。

*注意：如果报错提示找不到其他 `pyneedle-*` 包，我们可能还需要在 `stitcher-common` 的 sources 中补齐它们，但通常 workspace 根目录的配置足以覆盖。*
