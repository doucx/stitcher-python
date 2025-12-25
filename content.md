太棒了！测试全部通过。这意味着我们的 `stitcher-python` 现在已经具备了处理动态插件的核心能力。

我将生成一个 `[COMMIT]` 计划，将这些里程碑式的变更持久化到仓库中。

## [COMMIT] feat: implement plugin discovery and dynamic introspection

### 用户需求
完成任务 1.4：集成插件发现机制。系统现在可以发现、内省并为通过 `stitcher.plugins` 入口点注册的动态插件生成类型存根。

### 评论
这是项目的一个重大里程碑。通过引入动态内省和虚拟模块树，我们证明了中间表示 (IR) 层的强大灵活性。现在的架构不仅能看穿静态代码，还能看穿运行时的动态扩展。这也为即将开始的第二阶段（文档解耦）奠定了坚实的基础。

### 目标
1.  提交所有涉及插件发现、动态内省和应用层编排的代码变更。
2.  提交相应的单元测试和集成测试，确保功能的长期稳定性。

### 基本原理
此提交涵盖了从配置加载（`stitcher-config`）到动态解析（`stitcher-scanner`）再到全局编排（`stitcher-application`）的完整链路。我们在实现过程中通过 TDD 确保了质量，并修复了关于函数命名和路径生成的细节 bug。至此，路线图中的“第一阶段：核心引擎与 MVP”已基本完成。

### 标签
#intent/build #flow/ready #priority/high #comp/config #comp/scanner #comp/application #comp/tests #concept/executor #scope/core #ai/instruct #task/domain/plugins #task/object/discovery-mechanism #task/action/implementation #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交插件机制相关变更

我们将把受影响的包和测试目录添加到暂存区并提交。

~~~~~act
git_add
packages/stitcher-config
packages/stitcher-scanner
packages/stitcher-application
tests/integration
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
feat: implement plugin discovery and dynamic introspection

This commit completes Task 1.4 of the roadmap, enabling stitcher-python to
handle dynamic plugin architectures.

Key changes:
- config: Implemented recursive scanning of pyproject.toml files to discover
  'stitcher.plugins' entry points.
- scanner: Added a dynamic inspector using the 'inspect' module to extract
  signatures and docstrings from live Python objects.
- application: Refactored StitcherApp to orchestrate a dual-source workflow:
  1. Static scanning of source files via AST.
  2. Dynamic introspection of registered plugins.
- application: Implemented virtual module tree building to materialize .pyi
  namespaces for plugins that don't have corresponding source files.
- io: Enhanced StubGenerator/App to ensure intermediate directories and 
  __init__.pyi files are created for nested plugin namespaces.

The system now produces high-fidelity .pyi stubs for both static and 
dynamic code, fulfilling the core vision of the project.
~~~~~

### 下一步建议

恭喜！我们已经圆满完成了第一阶段的所有核心开发任务。

现在，我们准备进入 **第二阶段：文档解耦与工作流完善**。这一阶段的重点是让 `stitcher` 能够从外部 YAML 文件中获取文档，从而实现代码与文档的彻底解耦。

我建议的第一个任务是：
*   **任务 2.1: 实现文档 I/O 模块 (stitcher-io)**: 定义 `.stitcher.yaml` 的格式，并编写能将 `ModuleDef` 导出为 YAML 以及从 YAML 回填 `ModuleDef` 的逻辑。

如果你准备好了，我们可以开始任务 2.1 的设计和 TDD 流程。
