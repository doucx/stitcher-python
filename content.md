Of course. With all tests passing, it's time to complete the refactoring by removing the now-redundant files. This final step will leave our codebase clean and consistent with the new architecture.

I will now generate the plan to perform this cleanup.

## [WIP] refactor(arch): Remove redundant stubgen files after migration

### 用户需求

在成功将存根生成逻辑迁移到 `stitcher-stubgen` 包并更新所有调用方之后，需要清理 `stitcher-application` 和 `stitcher-python-adapter` 包中遗留的、现已无用的旧文件。

### 评论

这是保持代码库健康的必要步骤，也是我们架构重构的收官之作。留下“死代码”会增加新开发者的认知负担，并在未来可能引发难以察觉的错误。通过果断地删除这些冗余文件，我们正式完成了这次架构演进，确保了代码的物理结构与逻辑设计完全一致。

### 目标

1.  从 `stitcher-application` 中删除 `GenerateRunner` 和 `StubPackageManager` 的源文件及其关联的文档文件。
2.  从 `stitcher-python-adapter` 中删除旧的 `PythonStubGenerator` 包装器及其内部实现文件。

### 基本原理

在之前的步骤中，我们已经成功地将这些文件的功能迁移到了 `stitcher-stubgen` 包中，并且所有依赖这些功能的代码（包括应用代码和测试代码）都已被更新，转而调用新的 `StubgenService`。因此，这些原始文件现在已经完全不被任何代码引用，成为了“死代码”。

我们将使用一系列 `delete_file` 指令来精确地移除这些文件。这是一个安全的、不可逆的操作，它将使我们的项目结构最终达到我们所设计的整洁状态。

### 标签

#intent/refine #flow/ready #priority/medium #comp/application #comp/python-adapter #scope/core #task/domain/architecture #task/object/stubgen-package #task/action/cleanup #task/state/end

---

### Script

#### Acts 1: 清理 `stitcher-application` 包

我们将删除 `application` 包中与存根生成相关的、现已废弃的 `runner` 和 `service` 文件。

~~~~~act
delete_file
packages/stitcher-application/src/stitcher/app/runners/generate.py
~~~~~

~~~~~act
delete_file
packages/stitcher-application/src/stitcher/app/services/stub_package_manager.py
~~~~~

~~~~~act
delete_file
packages/stitcher-application/src/stitcher/app/services/stub_package_manager.stitcher.yaml
~~~~~

#### Acts 2: 清理 `stitcher-python-adapter` 包

接着，我们删除 `python-adapter` 包中旧的生成器实现。

~~~~~act
delete_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/generator.py
~~~~~

~~~~~act
delete_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/internal/stub_generator.py
~~~~~

### 下一步建议

我们已经成功地清理了所有冗余文件，`stitcher-stubgen` 的架构重构任务至此已全部完成。

这是一个逻辑上完整的工作单元，我建议你现在创建一个 `[COMMIT]` 计划，将这次重构的所有变更（从创建新包到删除旧文件）作为一个原子提交记录到版本控制中。这会为项目历史留下一条清晰、有意义的记录。
