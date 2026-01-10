[简要回答]
`run_apply` 返回 False 导致退出代码为 1，确认触发了异常处理分支。但由于 SpyBus 在测试中拦截了消息，导致错误详情不可见。本计划将在关键路径（Runner 异常捕获、Graph 加载）添加直接写入 `sys.stderr` 的调试日志，以绕过 SpyBus 强制暴露错误堆栈。

## [WIP] fix(refactor): 增加 stderr 调试日志以诊断集成测试失败

### 错误分析
集成测试持续失败，且 `SpyBus` 拦截了所有应用层面的日志输出，导致无法看到 `RefactorRunner` 捕获的具体异常信息。当前的架构设计（UI 层与逻辑层分离）在测试环境下意外造成了“错误吞噬”。根据 ADAP 协议，必须消除这种盲区。

### 用户需求
在不依赖 `bus` 的情况下，获取系统运行时的内部状态和异常堆栈信息。

### 评论
这是在测试环境中调试“黑盒”行为的常用手段。

### 目标
1.  修改 `RefactorRunner`，在捕获异常时将完整的 traceback 打印到 `sys.stderr`。
2.  修改 `SemanticGraph`，打印加载模块和扫描路径的详细信息。

### 基本原理
直接操作 `sys.stderr` 是最底层的日志手段，它不受应用层 `SpyBus` 或 Mock 机制的影响，且 `pytest -s` 可以直接捕获其输出。这将为我们提供导致 `run_apply` 失败的确切异常信息。

### 标签
#intent/fix #flow/ready #priority/high #comp/runtime #task/domain/refactoring #task/object/logging #task/action/debug

---

### Script

#### Acts 1: 在 `RefactorRunner` 中注入 stderr 日志

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/refactor.py
~~~~~
~~~~~python.old
        except (MigrationError, FileNotFoundError) as e:
            bus.error(L.error.generic, error=str(e))
            return False
        except Exception as e:
            bus.error(L.error.generic, error=f"An unexpected error occurred: {e}")
            return False
~~~~~
~~~~~python.new
        except (MigrationError, FileNotFoundError) as e:
            import sys
            import traceback
            print(f"DEBUG: Known Error caught in RefactorRunner: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            bus.error(L.error.generic, error=str(e))
            return False
        except Exception as e:
            import sys
            import traceback
            print(f"DEBUG: Unexpected Error caught in RefactorRunner: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            bus.error(L.error.generic, error=f"An unexpected error occurred: {e}")
            return False
~~~~~

#### Acts 2: 在 `SemanticGraph` 中增加调试信息

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py
~~~~~
~~~~~python.old
    def load_from_workspace(self) -> None:
        # 1. Load all main packages
        for pkg_name in self.workspace.import_to_source_dirs.keys():
            module = self._griffe_loader.load(pkg_name, submodules=True)
            if isinstance(module, griffe.Module):
                self._modules[pkg_name] = module

        # 2. Load all peripheral files/directories
~~~~~
~~~~~python.new
    def load_from_workspace(self) -> None:
        import sys
        print(f"DEBUG: Graph loading from workspace. Search paths: {self.search_paths}", file=sys.stderr)
        # 1. Load all main packages
        for pkg_name in self.workspace.import_to_source_dirs.keys():
            print(f"DEBUG: Loading package '{pkg_name}'", file=sys.stderr)
            try:
                module = self._griffe_loader.load(pkg_name, submodules=True)
                if isinstance(module, griffe.Module):
                    self._modules[pkg_name] = module
                else:
                    print(f"DEBUG: '{pkg_name}' loaded as {type(module)}, not Module", file=sys.stderr)
            except Exception as e:
                print(f"DEBUG: Failed to load package '{pkg_name}': {e}", file=sys.stderr)
                raise

        # 2. Load all peripheral files/directories
~~~~~

### 下一步建议
再次运行 `pytest -s packages/stitcher-cli/tests/integration/test_refactor_command.py`，并检查控制台输出中以 `DEBUG:` 开头的信息和 Traceback。这将直接揭示失败的根本原因。
