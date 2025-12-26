好的，所有本地化和语言检测相关的代码和资源文件都已准备就绪。我将生成一个 `[COMMIT]` 计划来提交这些变更，从而标志着本地化宏观任务的完成。

## [COMMIT] feat(i18n): Implement generic LANG detection and complete Chinese localization

### 用户需求
提交所有与国际化 (i18n) 相关的代码和资源文件变更，包括：
1.  `stitcher-needle` 中的通用 `LANG` 环境变量检测逻辑。
2.  `stitcher-cli` 的 UI 消息和配置帮助文本的本地化迁移。
3.  `stitcher-common` 中所有运行时消息的完整中文翻译。

### 评论
本次提交是项目迈向成熟的关键一步。通过适配系统标准的 `LANG` 环境变量，Stitcher 实现了零配置的本地化支持，极大地提升了全球用户的体验 (UX)。同时，我们验证了 `stitcher-needle` 多根加载机制的有效性，即多个独立包可以贡献自己的资源到同一个运行时注册表。

### 目标
将以下三个核心改动作为单一、完整的逻辑单元提交：
1.  **Needle 运行时增强**: 增加对 `LANG` 变量（如 `zh_CN.UTF-8`）的解析支持。
2.  **CLI 消息解耦**: 将 `stitcher-cli` 的所有 `typer` 帮助文本替换为语义指针 (`L.cli...`)。
3.  **中文资源完整性**: 提交 `stitcher-common` 和 `stitcher-cli` 的中文（`zh`）语言资源包。

### 基本原理
我们通过在 `Needle.get` 中引入优先级解析链（`STITCHER_LANG` > `LANG` > `default`）来提供灵活且通用的语言检测。将 CLI UI 文本和业务逻辑反馈文本分别放入它们各自的包内维护，遵循了关注点分离原则，确保未来维护和扩展时互不干扰。

### 标签
#intent/build #intent/refine #flow/ready #priority/high
#comp/cli #comp/needle #comp/common #concept/i18n #scope/ux #scope/dx
#ai/instruct
#task/domain/i18n #task/object/language-detection #task/action/standardization
#task/state/end

---

### Script

#### Acts 1: 添加所有修改和新增的文件到暂存区

~~~~~act
git_add
~~~~~

#### Acts 2: 执行 Git 提交

~~~~~act
git_commit
~~~~~
~~~~~text
feat(i18n): Implement generic LANG detection and complete Chinese localization

This commit finalizes the core localization framework, enabling the Stitcher CLI
and runtime messages to respond to the user's system language settings.

Key changes:
1.  **Needle Runtime**: Implemented `_resolve_lang` in `stitcher-needle` to prioritize `STITCHER_LANG` over, and then parse, the standard Unix `LANG` variable (e.g., `zh_CN.UTF-8` -> `zh`).
2.  **CLI Localization**: Migrated all hardcoded `typer` help messages in `stitcher-cli` to use semantic pointers (`L.cli...`) and registered its own asset root.
3.  **Chinese Assets**: Provided complete Chinese (`zh`) localization for both `stitcher-cli` (UI/Commands) and `stitcher-common` (Runtime messages/Errors).

This ensures a robust, standard-compliant, and fully localized user experience.
~~~~~

### 下一步建议
**宏观任务已完成。** 建议开始下一个宏观任务，例如按照路线图继续推进 **第三阶段：健壮性与高级功能** 中的性能优化，引入缓存机制（`任务 3.2: 缓存机制 (性能优化)`）。
