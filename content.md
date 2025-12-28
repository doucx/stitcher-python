好的，我们进入第二阶段。

此阶段的核心是进行一次精巧的“心脏搭桥手术”。我们将在 `stitcher-application` 的核心逻辑中，切断错误处理与用户交互之间的硬编码连接，并用一个灵活的、抽象的 `InteractionHandler` 协议来取而代之。这使得核心业务逻辑（Application）不再关心“如何”与用户交互，只关心“得到一个决策”，为我们下一阶段实现高级交互界面（Presentation）铺平了道路。

## [WIP] refactor: 通过 InteractionHandler 协议解耦检查逻辑

### 用户需求
实施“交互式引导”功能的第二阶段。这需要重构 `StitcherApp`，使其不再直接处理 `force-relink` 和 `reconcile` 等布尔标志，而是通过一个可注入的 `InteractionHandler` 协议来获取决策，从而将核心业务逻辑与用户界面交互解耦。

### 评论
这是整个功能架构中最关键的一步。通过依赖注入（Dependency Injection）引入 `InteractionHandler` 协议，我们遵循了“依赖倒置原则”。这极大地提升了代码的可测试性——我们现在可以在单元测试中注入一个 Mock Handler 来精确控制 `StitcherApp` 的行为，而无需模拟真实的用户输入。同时，它也保证了应用层（`stitcher-application`）的纯粹性，使其未来可以轻松地对接不同类型的用户界面（如 CLI, TUI, 甚至 LSP）。

### 目标
1.  在 `stitcher.app` 中创建 `protocols.py` 文件，定义 `InteractionContext` 数据类和 `InteractionHandler` 协议。
2.  创建 `handlers.py` 文件，并实现一个默认的 `NoOpInteractionHandler`，它将封装旧有的、基于命令行标志的非交互式行为。
3.  修改 `StitcherApp` 的构造函数 `__init__`，以接受一个可选的 `interaction_handler`。
4.  重构 `StitcherApp._analyze_file` 方法，移除 `force_relink` 和 `reconcile` 参数，改为接收并调用 `handler.ask_resolution()`。
5.  更新 `StitcherApp.run_check` 方法，使其根据是否注入了 `interaction_handler` 来实例化和使用相应的处理器。

### 基本原理
我们将 `run_check` 的核心逻辑修改为一个“检测-委托-执行”模型。当 `_analyze_file` 检测到一个冲突（如 `SIGNATURE_DRIFT`）时，它不再自行判断如何处理，而是将所有相关信息打包成一个 `InteractionContext` 对象，然后将决策权完全“委托”给 `InteractionHandler`。`Handler` 返回一个明确的 `ResolutionAction` 后，`_analyze_file` 再根据这个指令执行相应的操作（更新哈希或记录错误）。这种职责分离使得代码更加清晰和健壮。

### 标签
#intent/refine #flow/ready #priority/high #comp/application #concept/state #scope/api #ai/instruct #task/domain/cli #task/object/interactive-check #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 创建协议和上下文数据类

我们首先创建新文件 `protocols.py` 来定义应用层与表现层之间的通信契约。

~~~~~act
write_file
packages/stitcher-application/src/stitcher/app/protocols.py
~~~~~
~~~~~python
from typing import Protocol, List
from dataclasses import dataclass, field

from stitcher.spec import ResolutionAction, ConflictType


@dataclass
class InteractionContext:
    """Data packet passed to the handler to request a user decision."""

    file_path: str
    fqn: str
    conflict_type: ConflictType
    # Future extensions:
    # signature_diff: str = ""
    # doc_diff: str = ""


class InteractionHandler(Protocol):
    """Protocol for handling user interactions during a check."""

    def ask_resolution(self, context: InteractionContext) -> ResolutionAction:
        """
        Asks the user (or a non-interactive policy) how to resolve a conflict.
        """
        ...
~~~~~

#### Acts 2: 实现默认的非交互式处理器

接下来，我们创建 `handlers.py` 并实现 `NoOpInteractionHandler`，它将保持旧有的、基于命令行标志的行为，作为默认实现和 CI 环境下的后备方案。

~~~~~act
run_command
~~~~~
~~~~~
mkdir -p packages/stitcher-application/src/stitcher/app/handlers
touch packages/stitcher-application/src/stitcher/app/handlers/__init__.py
~~~~~

~~~~~act
write_file
packages/stitcher-application/src/stitcher/app/handlers/noop_handler.py
~~~~~
~~~~~python
from stitcher.app.protocols import InteractionHandler, InteractionContext
from stitcher.spec import ResolutionAction, ConflictType


class NoOpInteractionHandler(InteractionHandler):
    """
    A non-interactive handler that resolves conflicts based on CLI flags.
    This preserves the original behavior for CI/CD environments.
    """

    def __init__(self, force_relink: bool = False, reconcile: bool = False):
        self._force_relink = force_relink
        self._reconcile = reconcile

    def ask_resolution(self, context: InteractionContext) -> ResolutionAction:
        if context.conflict_type == ConflictType.SIGNATURE_DRIFT:
            if self._force_relink:
                return ResolutionAction.RELINK
        elif context.conflict_type == ConflictType.CO_EVOLUTION:
            if self._reconcile:
                return ResolutionAction.RECONCILE
        return ResolutionAction.SKIP
~~~~~

#### Acts 3: 在 `StitcherApp` 中注入和重构

现在，我们对 `core.py` 进行核心改造，注入 `InteractionHandler` 并重构 `run_check` 和 `_analyze_file`。

##### 3.1: 更新 `__init__` 和 `imports`

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
from stitcher.spec import ModuleDef
from stitcher.common import bus
from needle.pointer import L
from stitcher.config import load_config_from_path, StitcherConfig
from stitcher.app.services import (
    DocumentManager,
    SignatureManager,
    StubPackageManager,
)
~~~~~
~~~~~python.new
import copy
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict
from dataclasses import dataclass, field

from stitcher.scanner import (
    parse_source_code,
    parse_plugin_entry,
    InspectionError,
    strip_docstrings,
    inject_docstrings,
)
from stitcher.io import StubGenerator
from stitcher.spec import ModuleDef, ConflictType, ResolutionAction
from stitcher.common import bus
from needle.pointer import L
from stitcher.config import load_config_from_path, StitcherConfig
from stitcher.app.services import (
    DocumentManager,
    SignatureManager,
    StubPackageManager,
)
from .protocols import InteractionHandler, InteractionContext
from .handlers.noop_handler import NoOpInteractionHandler
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
class StitcherApp:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.generator = StubGenerator()
        self.doc_manager = DocumentManager(root_path)
        self.sig_manager = SignatureManager(root_path)
        self.stub_pkg_manager = StubPackageManager()
~~~~~
~~~~~python.new
class StitcherApp:
    def __init__(
        self,
        root_path: Path,
        interaction_handler: Optional[InteractionHandler] = None,
    ):
        self.root_path = root_path
        self.generator = StubGenerator()
        self.doc_manager = DocumentManager(root_path)
        self.sig_manager = SignatureManager(root_path)
        self.stub_pkg_manager = StubPackageManager()
        self.interaction_handler = interaction_handler
~~~~~

##### 3.2: 重构 `_analyze_file` 以使用 Handler

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
    def _analyze_file(
        self, module: ModuleDef, force_relink: bool, reconcile: bool
    ) -> FileCheckResult:
        result = FileCheckResult(path=module.file_path)

        # 1. Content Checks
        if (self.root_path / module.file_path).with_suffix(".stitcher.yaml").exists():
            doc_issues = self.doc_manager.check_module(module)
            if doc_issues["missing"]:
                result.warnings["missing"].extend(doc_issues["missing"])
            if doc_issues["redundant"]:
                result.warnings["redundant"].extend(doc_issues["redundant"])
            if doc_issues["pending"]:
                result.errors["pending"].extend(doc_issues["pending"])
            if doc_issues["conflict"]:
                result.errors["conflict"].extend(doc_issues["conflict"])
            if doc_issues["extra"]:
                result.errors["extra"].extend(doc_issues["extra"])

        # 2. State Machine Checks
        doc_path = (self.root_path / module.file_path).with_suffix(".stitcher.yaml")
        is_tracked = doc_path.exists()

        current_code_structure_map = self.sig_manager.compute_code_structure_hashes(
            module
        )
        current_yaml_content_map = self.doc_manager.compute_yaml_content_hashes(module)
        stored_hashes_map = self.sig_manager.load_composite_hashes(module)
        new_hashes_map = copy.deepcopy(stored_hashes_map)

        all_fqns = set(current_code_structure_map.keys()) | set(
            stored_hashes_map.keys()
        )

        for fqn in sorted(list(all_fqns)):
            current_code_structure_hash = current_code_structure_map.get(fqn)
            current_yaml_content_hash = current_yaml_content_map.get(fqn)
            stored = stored_hashes_map.get(fqn, {})
            baseline_code_structure_hash = stored.get("baseline_code_structure_hash")
            baseline_yaml_content_hash = stored.get("baseline_yaml_content_hash")

            # Case: Extra (In Storage, Not in Code)
            if not current_code_structure_hash and baseline_code_structure_hash:
                if fqn in new_hashes_map:
                    new_hashes_map.pop(fqn, None)
                continue

            # Case: New (In Code, Not in Storage)
            if current_code_structure_hash and not baseline_code_structure_hash:
                if is_tracked:
                    new_hashes_map[fqn] = {
                        "baseline_code_structure_hash": current_code_structure_hash,
                        "baseline_yaml_content_hash": current_yaml_content_hash,
                    }
                continue

            # Case: Existing
            code_structure_matches = (
                current_code_structure_hash == baseline_code_structure_hash
            )
            yaml_content_matches = (
                current_yaml_content_hash == baseline_yaml_content_hash
            )

            if code_structure_matches and yaml_content_matches:
                pass  # Synchronized
            elif code_structure_matches and not yaml_content_matches:
                # Doc Improvement: INFO, Auto-reconcile
                result.infos["doc_improvement"].append(fqn)
                if fqn in new_hashes_map:
                    new_hashes_map[fqn]["baseline_yaml_content_hash"] = (
                        current_yaml_content_hash
                    )
                result.auto_reconciled_count += 1
            elif not code_structure_matches and yaml_content_matches:
                # Signature Drift
                if force_relink:
                    result.reconciled["force_relink"].append(fqn)
                    if fqn in new_hashes_map:
                        new_hashes_map[fqn]["baseline_code_structure_hash"] = (
                            current_code_structure_hash
                        )
                else:
                    result.errors["signature_drift"].append(fqn)
            elif not code_structure_matches and not yaml_content_matches:
                # Co-evolution
                if reconcile:
                    result.reconciled["reconcile"].append(fqn)
                    new_hashes_map[fqn] = {
                        "baseline_code_structure_hash": current_code_structure_hash,
                        "baseline_yaml_content_hash": current_yaml_content_hash,
                    }
                else:
                    result.errors["co_evolution"].append(fqn)

        # 3. Untracked File check
        if not is_tracked and module.is_documentable():
            undocumented = module.get_undocumented_public_keys()
            if undocumented:
                result.warnings["untracked_detailed"].extend(undocumented)
            else:
                result.warnings["untracked"].append("all")

        # Save hash updates if any
        if new_hashes_map != stored_hashes_map:
            self.sig_manager.save_composite_hashes(module, new_hashes_map)

        return result
~~~~~
~~~~~python.new
    def _analyze_file(
        self, module: ModuleDef, handler: InteractionHandler
    ) -> FileCheckResult:
        result = FileCheckResult(path=module.file_path)

        # 1. Content Checks
        if (self.root_path / module.file_path).with_suffix(".stitcher.yaml").exists():
            doc_issues = self.doc_manager.check_module(module)
            if doc_issues["missing"]:
                result.warnings["missing"].extend(doc_issues["missing"])
            if doc_issues["redundant"]:
                result.warnings["redundant"].extend(doc_issues["redundant"])
            if doc_issues["pending"]:
                result.errors["pending"].extend(doc_issues["pending"])
            if doc_issues["conflict"]:
                result.errors["conflict"].extend(doc_issues["conflict"])
            if doc_issues["extra"]:
                result.errors["extra"].extend(doc_issues["extra"])

        # 2. State Machine Checks
        doc_path = (self.root_path / module.file_path).with_suffix(".stitcher.yaml")
        is_tracked = doc_path.exists()

        current_code_structure_map = self.sig_manager.compute_code_structure_hashes(
            module
        )
        current_yaml_content_map = self.doc_manager.compute_yaml_content_hashes(module)
        stored_hashes_map = self.sig_manager.load_composite_hashes(module)
        new_hashes_map = copy.deepcopy(stored_hashes_map)

        all_fqns = set(current_code_structure_map.keys()) | set(
            stored_hashes_map.keys()
        )

        for fqn in sorted(list(all_fqns)):
            current_code_structure_hash = current_code_structure_map.get(fqn)
            current_yaml_content_hash = current_yaml_content_map.get(fqn)
            stored = stored_hashes_map.get(fqn, {})
            baseline_code_structure_hash = stored.get("baseline_code_structure_hash")
            baseline_yaml_content_hash = stored.get("baseline_yaml_content_hash")

            if not current_code_structure_hash and baseline_code_structure_hash:
                if fqn in new_hashes_map:
                    new_hashes_map.pop(fqn, None)
                continue

            if current_code_structure_hash and not baseline_code_structure_hash:
                if is_tracked:
                    new_hashes_map[fqn] = {
                        "baseline_code_structure_hash": current_code_structure_hash,
                        "baseline_yaml_content_hash": current_yaml_content_hash,
                    }
                continue

            code_structure_matches = (
                current_code_structure_hash == baseline_code_structure_hash
            )
            yaml_content_matches = (
                current_yaml_content_hash == baseline_yaml_content_hash
            )

            if code_structure_matches and yaml_content_matches:
                pass
            elif code_structure_matches and not yaml_content_matches:
                result.infos["doc_improvement"].append(fqn)
                if fqn in new_hashes_map:
                    new_hashes_map[fqn]["baseline_yaml_content_hash"] = (
                        current_yaml_content_hash
                    )
                result.auto_reconciled_count += 1
            elif not code_structure_matches and yaml_content_matches:
                context = InteractionContext(
                    file_path=module.file_path,
                    fqn=fqn,
                    conflict_type=ConflictType.SIGNATURE_DRIFT,
                )
                action = handler.ask_resolution(context)
                if action == ResolutionAction.RELINK:
                    result.reconciled["force_relink"].append(fqn)
                    if fqn in new_hashes_map:
                        new_hashes_map[fqn]["baseline_code_structure_hash"] = (
                            current_code_structure_hash
                        )
                else:
                    result.errors["signature_drift"].append(fqn)
            elif not code_structure_matches and not yaml_content_matches:
                context = InteractionContext(
                    file_path=module.file_path,
                    fqn=fqn,
                    conflict_type=ConflictType.CO_EVOLUTION,
                )
                action = handler.ask_resolution(context)
                if action == ResolutionAction.RECONCILE:
                    result.reconciled["reconcile"].append(fqn)
                    new_hashes_map[fqn] = {
                        "baseline_code_structure_hash": current_code_structure_hash,
                        "baseline_yaml_content_hash": current_yaml_content_hash,
                    }
                else:
                    result.errors["co_evolution"].append(fqn)

        if not is_tracked and module.is_documentable():
            undocumented = module.get_undocumented_public_keys()
            if undocumented:
                result.warnings["untracked_detailed"].extend(undocumented)
            else:
                result.warnings["untracked"].append("all")

        if new_hashes_map != stored_hashes_map:
            self.sig_manager.save_composite_hashes(module, new_hashes_map)

        return result
~~~~~

##### 3.3: 重构 `run_check` 以实例化和传递 Handler

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
    def run_check(self, force_relink: bool = False, reconcile: bool = False) -> bool:
        configs, _ = load_config_from_path(self.root_path)
        global_failed_files = 0
        global_warnings_files = 0
        for config in configs:
            if config.name != "default":
                bus.info(L.generate.target.processing, name=config.name)
            unique_files = self._get_files_from_config(config)
            modules = self._scan_files(unique_files)
            if not modules:
                continue
            for module in modules:
                res = self._analyze_file(module, force_relink, reconcile)
                if res.is_clean:
                    if res.auto_reconciled_count > 0:
                        bus.info(
                            L.check.state.auto_reconciled,
                            count=res.auto_reconciled_count,
                            path=res.path,
                        )
                    # Even if clean, we might want to report info-level updates like doc improvements
                    for key in sorted(res.infos["doc_improvement"]):
                        bus.info(L.check.state.doc_updated, key=key)
                    continue
~~~~~
~~~~~python.new
    def run_check(self, force_relink: bool = False, reconcile: bool = False) -> bool:
        handler = self.interaction_handler or NoOpInteractionHandler(
            force_relink=force_relink, reconcile=reconcile
        )

        configs, _ = load_config_from_path(self.root_path)
        global_failed_files = 0
        global_warnings_files = 0
        for config in configs:
            if config.name != "default":
                bus.info(L.generate.target.processing, name=config.name)
            unique_files = self._get_files_from_config(config)
            modules = self._scan_files(unique_files)
            if not modules:
                continue
            for module in modules:
                res = self._analyze_file(module, handler)
                if res.is_clean:
                    if res.auto_reconciled_count > 0:
                        bus.info(
                            L.check.state.auto_reconciled,
                            count=res.auto_reconciled_count,
                            path=res.path,
                        )
                    for key in sorted(res.infos["doc_improvement"]):
                        bus.info(L.check.state.doc_updated, key=key)
                    continue
~~~~~

### 下一步建议

我们已经成功地将 `StitcherApp` 的核心检查逻辑与用户交互解耦。现在，`StitcherApp` 依赖于一个抽象的 `InteractionHandler` 协议，并且我们提供了一个保持旧有行为的 `NoOpInteractionHandler` 作为默认实现。

下一步是进入 **阶段 3**：实现 CLI 层的交互逻辑。我们将在 `stitcher-cli` 中创建一个 `TyperInteractionHandler`，它将真正地与用户进行交互（检测 TTY、获取键盘输入、实现撤销和粘性默认值等），并将其注入到 `StitcherApp` 中。这将是整个功能的“最后一公里”，将我们构建的强大后端逻辑呈现给最终用户。
