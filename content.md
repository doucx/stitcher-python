好的，我们现在开始执行 **阶段一：功能平移** 的第一步。

我们将把 `stitcher-bus` 中的所有 I18n 资源文件搬迁到 `stitcher-common` 中。这样做是为了让资产能够跟随通用包分发，同时为下一步在 `stitcher-common` 中配置 `pyneedle-bus` 提供必要的本地资源路径。

## [WIP] refactor(bus): 搬迁 stitcher-bus 资产到 stitcher-common

### 用户需求
按照“激进重构”计划，将 `stitcher-bus` 现有的 I18n JSON 资产搬迁到 `stitcher-common` 的相应目录下。

### 评论
这是解耦的第一步。`stitcher-common` 被所有组件依赖，是存放共用资源（如错误信息模板、CLI 文案）的最理想物理位置。后续 `pyneedle-bus` 的 `MessageStore` 将会从这里加载资源。

### 目标
1.  在 `packages/stitcher-common/src/stitcher/common/` 下创建 `assets` 目录。
2.  将 `packages/stitcher-bus/src/stitcher/bus/assets/` 下的整个 `needle` 结构移动到新位置。
3.  验证搬迁后的路径结构。

### 基本原理
我们使用 `run_command` 来执行目录级的移动操作，以确保所有子目录（`en`, `zh` 及其下的所有模块分类）完整保留。搬迁后，`stitcher-common` 的 `pyproject.toml` 已经配置了 `include = ["/src/stitcher/common/assets"]`，因此这些资源会自动包含在构建产物中。

### 标签
#intent/refine #flow/ready #priority/high 
#comp/common #comp/bus #scope/core
#ai/instruct
#task/domain/bus #task/object/assets-relocation #task/action/relocate #task/state/begin

---

### Script

#### Acts 1: 创建目标目录并移动资产

我们将确保目标路径存在，然后执行物理移动。

~~~~~act
run_command
~~~~~
~~~~~
mkdir -p packages/stitcher-common/src/stitcher/common/assets
mv packages/stitcher-bus/src/stitcher/bus/assets/needle packages/stitcher-common/src/stitcher/common/assets/
~~~~~

#### Acts 2: 验证移动结果

检查新路径下的文件结构，确保 `en` 和 `zh` 目录及其内容完整。

~~~~~act
run_command
~~~~~
~~~~~
ls -R packages/stitcher-common/src/stitcher/common/assets/needle
~~~~~

### 下一步建议
资产搬迁完成后，下一步我们将在 `packages/stitcher-common/src/stitcher/common/bus.py` 中创建新的总线入口。该入口将负责实例化 `pyneedle-bus` 并向其注册刚才搬迁的资产路径，从而实现功能上的无缝替换。
