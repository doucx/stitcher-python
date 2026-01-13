好的，分析显示之前的修复未能解决根本问题。直接修改代码存在风险，我们需要先通过日志来观测系统的内部状态，以做出正确的诊断。

根据 `HFEA` 协议的“确定性路径追踪”原则和 `ADAP` 协议的“照明工具优先”原则，在进行进一步修改之前，首要任务是增强系统的可观测性。

我将为 `Planner` 和 `SidecarTransformer` 注入详细的日志记录，并配置 `pytest` 以在测试运行时显示这些 `DEBUG` 级别的日志。这将使我们能够精确追踪重构意图的传递、SURI 的解析以及转换决策的全过程。

## [WIP] chore: 为重构引擎添加诊断日志

### 用户需求
测试仍然失败，需要插入日志来诊断 SURI 转换失败的根本原因。

### 评论
这是一个正确的调试步骤。在不完全理解系统行为时，盲目修改代码是低效且危险的。通过日志增强可观测性，可以将“猜测性修复”转变为“确定性构建”。

### 目标
1.  修改 `pyproject.toml` 以启用 `pytest` 的 `DEBUG` 级别日志输出。
2.  在 `Planner` 中添加日志，以追踪意图的收集和分发。
3.  在 `SidecarTransformer` 中添加日志，以追踪 SURI 的解析、匹配和转换过程。

### 基本原理
通过在关键决策点（意图聚合、SURI 解析、路径/片段匹配）添加日志，我们可以构建一个清晰的数据流路径。当测试运行时，这些日志将暴露导致 SURI 未被正确更新的确切断点，无论是错误的输入上下文、失败的 SURI 解析还是错误的匹配逻辑。

### 标签
#intent/tooling #flow/ready #priority/critical #comp/refactor #comp/tests #scope/dx #ai/instruct #task/domain/debugging #task/object/refactor-engine #task/action/add-logging #task/state/begin

---

### Script

#### Acts 1: 配置 Pytest 以显示 DEBUG 日志

我们将修改 `pyproject.toml`，为 `pytest` 添加日志相关的配置。

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml.old
[tool.pytest.ini_options]
addopts = "-ra --cov=stitcher --cov=needle --cov-report=term-missing"
testpaths = ["tests", "packages"]
norecursedirs = ["tests/fixtures"]
pythonpath = [
~~~~~
~~~~~toml.new
[tool.pytest.ini_options]
addopts = "-ra -s --cov=stitcher --cov=needle --cov-report=term-missing"
log_cli = "true"
log_cli_level = "DEBUG"
testpaths = ["tests", "packages"]
norecursedirs = ["tests/fixtures"]
pythonpath = [
~~~~~

#### Acts 2: 为 Planner 添加日志

现在，我们在 `planner.py` 中注入日志，以观察意图的生命周期。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/planner.py
~~~~~
~~~~~python.old
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, DefaultDict, TYPE_CHECKING
import json

if TYPE_CHECKING:
    from stitcher.refactor.migration import MigrationSpec
from stitcher.refactor.engine.context import RefactorContext
~~~~~
~~~~~python.new
import logging
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, DefaultDict, TYPE_CHECKING
import json

if TYPE_CHECKING:
    from stitcher.refactor.migration import MigrationSpec
from stitcher.refactor.engine.context import RefactorContext

log = logging.getLogger(__name__)
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/planner.py
~~~~~
~~~~~python.old
class Planner:
    def plan(self, spec: "MigrationSpec", ctx: RefactorContext) -> List[FileOp]:
        all_ops: List[FileOp] = []

        # --- 1. Intent Collection ---
        all_intents: List[RefactorIntent] = []
        for operation in spec.operations:
            all_intents.extend(operation.collect_intents(ctx))
~~~~~
~~~~~python.new
class Planner:
    def plan(self, spec: "MigrationSpec", ctx: RefactorContext) -> List[FileOp]:
        log.debug("--- Planner: Starting plan generation ---")
        all_ops: List[FileOp] = []

        # --- 1. Intent Collection ---
        all_intents: List[RefactorIntent] = []
        for operation in spec.operations:
            all_intents.extend(operation.collect_intents(ctx))
        log.debug(f"Collected {len(all_intents)} total intents.")
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/planner.py
~~~~~
~~~~~python.old
        rename_map: Dict[str, str] = {}
        for intent in all_intents:
            if isinstance(intent, RenameIntent):
                # TODO: Handle rename chains (A->B, B->C should become A->C)
                rename_map[intent.old_fqn] = intent.new_fqn
~~~~~
~~~~~python.new
        rename_map: Dict[str, str] = {}
        for intent in all_intents:
            if isinstance(intent, RenameIntent):
                # TODO: Handle rename chains (A->B, B->C should become A->C)
                rename_map[intent.old_fqn] = intent.new_fqn
        log.debug(f"Aggregated rename_map: {rename_map}")
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/planner.py
~~~~~
~~~~~python.old
        sidecar_updates: DefaultDict[Path, List[SidecarUpdateIntent]] = defaultdict(
            list
        )
        for intent in all_intents:
            if isinstance(intent, SidecarUpdateIntent):
                sidecar_updates[intent.sidecar_path].append(intent)

        sidecar_adapter = SidecarAdapter(ctx.workspace.root_path)
        sidecar_transformer = SidecarTransformer()
        for path, intents in sidecar_updates.items():
            # Load the sidecar file only once
            is_yaml = path.suffix in [".yaml", ".yml"]
            data = (
                sidecar_adapter.load_raw_data(path)
                if is_yaml
                else json.loads(path.read_text("utf-8"))
            )

            # Apply all intents for this file
            for intent in intents:
                old_module_fqn = intent.module_fqn
                new_module_fqn = module_rename_map.get(old_module_fqn, old_module_fqn)

                transform_ctx = SidecarTransformContext(
                    old_module_fqn=old_module_fqn,
                    new_module_fqn=new_module_fqn,
                    old_fqn=intent.old_fqn,
                    new_fqn=intent.new_fqn,
                    old_file_path=intent.old_file_path,
                    new_file_path=intent.new_file_path,
                )
                data = sidecar_transformer.transform(path, data, transform_ctx)
~~~~~
~~~~~python.new
        sidecar_updates: DefaultDict[Path, List[SidecarUpdateIntent]] = defaultdict(
            list
        )
        for intent in all_intents:
            if isinstance(intent, SidecarUpdateIntent):
                sidecar_updates[intent.sidecar_path].append(intent)
        log.debug(
            f"Aggregated {len(sidecar_updates)} sidecar files to update: {list(sidecar_updates.keys())}"
        )

        sidecar_adapter = SidecarAdapter(ctx.workspace.root_path)
        sidecar_transformer = SidecarTransformer()
        for path, intents in sidecar_updates.items():
            log.debug(f"Processing sidecar file: {path}")
            log.debug(f"  Intents for this file: {intents}")
            # Load the sidecar file only once
            is_yaml = path.suffix in [".yaml", ".yml"]
            data = (
                sidecar_adapter.load_raw_data(path)
                if is_yaml
                else json.loads(path.read_text("utf-8"))
            )

            # Apply all intents for this file
            for intent in intents:
                log.debug(f"  Applying intent: {intent}")
                old_module_fqn = intent.module_fqn
                new_module_fqn = module_rename_map.get(old_module_fqn, old_module_fqn)

                transform_ctx = SidecarTransformContext(
                    old_module_fqn=old_module_fqn,
                    new_module_fqn=new_module_fqn,
                    old_fqn=intent.old_fqn,
                    new_fqn=intent.new_fqn,
                    old_file_path=intent.old_file_path,
                    new_file_path=intent.new_file_path,
                )
                log.debug(f"  Creating transform_ctx: {transform_ctx}")
                data = sidecar_transformer.transform(path, data, transform_ctx)
~~~~~

#### Acts 3: 为 SidecarTransformer 添加日志

最后，我们在 `transform.py` 中添加日志，以观察 SURI 的处理细节。

~~~~~act
patch_file
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/transform.py
~~~~~
~~~~~python.old
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from stitcher.lang.python.uri import SURIGenerator
~~~~~
~~~~~python.new
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from stitcher.lang.python.uri import SURIGenerator

log = logging.getLogger(__name__)
~~~~~

~~~~~act
patch_file
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/transform.py
~~~~~
~~~~~python.old
    def _transform_json_data(
        self,
        data: Dict[str, Any],
        old_file_path: Optional[str],
        new_file_path: Optional[str],
        old_fragment: Optional[str],
        new_fragment: Optional[str],
    ) -> Dict[str, Any]:
        # Handle stitcher.lock format (nested fingerprints)
        if "fingerprints" in data and isinstance(data["fingerprints"], dict):
            new_fingerprints = self._transform_json_data(
                data["fingerprints"],
                old_file_path,
                new_file_path,
                old_fragment,
                new_fragment,
            )
            if new_fingerprints is not data["fingerprints"]:
                new_data = data.copy()
                new_data["fingerprints"] = new_fingerprints
                return new_data
            return data

        new_data = {}
        modified = False

        for key, value in data.items():
            if not key.startswith("py://"):
                new_data[key] = value
                continue

            try:
                # Use the centralized, fixed SURIGenerator
                path, fragment = SURIGenerator.parse(key)
            except ValueError:
                new_data[key] = value
                continue
~~~~~
~~~~~python.new
    def _transform_json_data(
        self,
        data: Dict[str, Any],
        old_file_path: Optional[str],
        new_file_path: Optional[str],
        old_fragment: Optional[str],
        new_fragment: Optional[str],
    ) -> Dict[str, Any]:
        log.debug(
            f"--- _transform_json_data (file context: {old_file_path or 'N/A'}) ---\n"
            f"  Context: old_frag={old_fragment}, new_frag={new_fragment}, old_path={old_file_path}, new_path={new_file_path}"
        )
        # Handle stitcher.lock format (nested fingerprints)
        if "fingerprints" in data and isinstance(data["fingerprints"], dict):
            log.debug("Found 'fingerprints' key, recursing.")
            new_fingerprints = self._transform_json_data(
                data["fingerprints"],
                old_file_path,
                new_file_path,
                old_fragment,
                new_fragment,
            )
            if new_fingerprints is not data["fingerprints"]:
                new_data = data.copy()
                new_data["fingerprints"] = new_fingerprints
                return new_data
            return data

        new_data = {}
        modified = False

        for key, value in data.items():
            log.debug(f"  Processing key: '{key}'")
            if not key.startswith("py://"):
                new_data[key] = value
                log.debug("    -> Not a SURI, skipping.")
                continue

            try:
                # Use the centralized, fixed SURIGenerator
                path, fragment = SURIGenerator.parse(key)
                log.debug(f"    - Parsed SURI: path='{path}', fragment='{fragment}'")
            except ValueError:
                new_data[key] = value
                log.debug(f"    - SURI parse failed, skipping.")
                continue
~~~~~

~~~~~act
patch_file
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/transform.py
~~~~~
~~~~~python.old
            if current_path != original_path or current_fragment != original_fragment:
                # Use SURIGenerator to construct the new key
                # We handle the 'empty fragment' case: if fragment is None/empty,
                # for_symbol might not be right if we want file-only SURI.
                # But here we are transforming existing SURIs which usually have fragments.
                # If original fragment was empty, current_fragment is empty.
                if current_fragment:
                    new_key = SURIGenerator.for_symbol(current_path, current_fragment)
                else:
                    new_key = SURIGenerator.for_file(current_path)
                
                new_data[new_key] = value
                modified = True
            else:
                new_data[key] = value
~~~~~
~~~~~python.new
            if current_path != original_path or current_fragment != original_fragment:
                # Use SURIGenerator to construct the new key
                # We handle the 'empty fragment' case: if fragment is None/empty,
                # for_symbol might not be right if we want file-only SURI.
                # But here we are transforming existing SURIs which usually have fragments.
                # If original fragment was empty, current_fragment is empty.
                if current_fragment:
                    new_key = SURIGenerator.for_symbol(current_path, current_fragment)
                else:
                    new_key = SURIGenerator.for_file(current_path)

                log.debug(f"    -> MODIFIED: New key will be '{new_key}'")
                new_data[new_key] = value
                modified = True
            else:
                log.debug("    -> UNCHANGED")
                new_data[key] = value
~~~~~

### 下一步建议

请重新运行测试。`pytest` 现在会捕获并显示详细的 `DEBUG` 日志。请将完整的、包含日志的测试失败输出提供给我，以便我进行最终的根本原因分析和修复。
