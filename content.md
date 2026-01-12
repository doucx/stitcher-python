好的，既然所有重构和清理工作已通过测试验证，我们现在将这些变更作为一个完整的逻辑单元提交。

## [COMMIT] refactor: 将 Python 语言能力统一至 stitcher-lang-python

### 用户需求
完成架构重构路线图中的阶段二：将 `stitcher-python-adapter` 和 `stitcher-python-analysis` 合并为统一的 `stitcher-lang-python` 包，并清理所有相关依赖和导入路径。

### 评论
这是架构演进中的一个重大里程碑。通过消除两个 Python 相关包之间的人为物理隔离，我们不仅简化了 Monorepo 的结构，还通过统一的导出逻辑提升了开发者的调用体验。现在，Stitcher 的 Python 语言插件拥有了一个内聚且职责明确的家。

### 目标
1.  正式提交 `packages/stitcher-lang-python` 的创建。
2.  提交对 `stitcher-python-adapter` 和 `stitcher-python-analysis` 的物理删除。
3.  提交所有子包 `pyproject.toml` 的依赖关系更新。
4.  提交全局导入路径（从 `adapter.python` 到 `lang.python`）的修复。

### 基本原理
按照“意图-计划-执行-提交”的工作流，我们在执行了物理迁移和路径修复并确认测试通过后，进行原子提交。这确保了 Git 历史的清晰性，即每一个 `[COMMIT]` 节点都是一个功能完备且经过验证的系统状态。

### 标签
#intent/refine #flow/ready #priority/high
#comp/build #concept/parser #scope/dx
#ai/instruct
#task/domain/language-support
#task/object/stitcher-lang-python
#task/action/cleanup
#task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交阶段二重构成果

我们将所有涉及到的包和根目录配置文件添加到暂存区并提交。

~~~~~act
git_add
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor: unify Python language capabilities into stitcher-lang-python

This commit completes Phase 2 of the architectural refactoring roadmap:
1. Merged 'stitcher-python-adapter' and 'stitcher-python-analysis' into a single 'stitcher-lang-python' package.
2. Reorganized internal structure into functional sub-packages: parser, analysis, transform, and docstring.
3. Updated all workspace dependencies in pyproject.toml files.
4. Performed a global refactoring of import paths from 'stitcher.adapter.python' to 'stitcher.lang.python'.

This unification reduces monorepo overhead, clarifies domain boundaries, and provides a cleaner template for future language support.
~~~~~

### 下一步建议
- **执行 `uv sync`**: 如果你还没有运行，建议执行此命令以同步锁文件和本地虚拟环境。
- **启动阶段三**: 接下来我们将进入 **阶段三：核心服务抽象化 (Service Abstraction)**。建议先从定义 `IndexStoreProtocol` 开始，以解除 `Application` 层对 `stitcher-index` 具体实现的依赖。
