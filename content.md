好的，我们正式进入实施路线图的第二阶段。

此阶段的核心是将作为“基准”的签名存档 (`.stitcher/signatures/*.json`) 与作为“现状”的索引库 (`.stitcher/index/index.db`) 在核心标识符和数据结构上完全对齐。

## [WIP] refactor(application): 对齐 SignatureManager 与 SURI 标识符

### 用户需求
根据 [Stitcher 2.0 确定性链接实施路线图：Index-First 架构](Stitcher%202.0%20确定性链接实施路线图：Index-First%20架构.md)，需要重构 `SignatureManager`，以实现以下目标：
1.  将 `.json` 基准文件中的字典键（Key）从局部的 FQN 片段（fragment）升级为全局唯一的 SURI (Stitcher Uniform Resource Identifier)。
2.  使其能够存储和加载新增的基准哈希字段：`baseline_code_signature_text` 和 `baseline_code_docstring_hash`。

### 评论
这是迈向“Query-First”架构的关键一步。通过将基准存档的 Key 切换为 SURI，我们彻底消除了标识符的歧义性。一个 SURI 同时包含了文件的物理路径和符号的逻辑路径，使得基准文件成为一个完全自包含的、可移植的“真理快照”。

### 目标
1.  修改 `SignatureManager.save_composite_hashes` 方法，在序列化到 JSON 时，将 FQN 片段转换为完整的 SURI 字符串作为 Key。
2.  修改 `SignatureManager.load_composite_hashes` 方法，在从 JSON 反序列化时，能解析 SURI Key 并提取出 FQN 片段，以维持其返回 `Dict[str, Fingerprint]` 的接口契约。
3.  `Fingerprint` 类本身的设计已支持新字段，无需修改。

### 基本原理
我们将利用在 `stitcher-python-adapter` 中已经实现的 `SURIGenerator` 工具来完成 SURI 的生成和解析。
-   **写入时**: 对每一个 FQN，结合其所属的 `file_path`，调用 `SURIGenerator.for_symbol()` 来生成 `py://path/to/file.py#ClassName.method` 格式的 Key。
-   **读取时**: 遍历 JSON 的所有 Key，对每一个 Key 调用 `SURIGenerator.parse()`，提取出 `#` 后的 fragment 作为返回字典的 Key。

### 标签
#intent/refine #flow/ready #priority/high #comp/application #concept/state #scope/api #ai/instruct #task/domain/storage #task/object/stitcher-index #task/action/upgrade-schema #task/state/continue

---

### Script

#### Acts 1: 导入 SURI 生成器

首先，我们需要在 `signature_manager.py` 中导入 `SURIGenerator`。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/signature_manager.py
~~~~~
~~~~~python.old
from stitcher.spec import (
    Fingerprint,
    InvalidFingerprintKeyError,
)
from stitcher.common.services import AssetPathResolver
~~~~~
~~~~~python.new
import json
from pathlib import Path
from typing import Dict

from stitcher.spec import (
    Fingerprint,
    InvalidFingerprintKeyError,
)
from stitcher.common.services import AssetPathResolver
from stitcher.adapter.python.uri import SURIGenerator
~~~~~

#### Acts 2: 更新保存逻辑以使用 SURI Key

修改 `save_composite_hashes` 方法，将 FQN 转换为 SURI 作为 JSON 的键。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/signature_manager.py
~~~~~
~~~~~python.old
        sig_path = self._get_sig_path(file_path)
        sig_path.parent.mkdir(parents=True, exist_ok=True)

        serialized_data = {fqn: fp.to_dict() for fqn, fp in hashes.items()}

        with sig_path.open("w", encoding="utf-8") as f:
            json.dump(serialized_data, f, indent=2, sort_keys=True)
~~~~~
~~~~~python.new
        sig_path = self._get_sig_path(file_path)
        sig_path.parent.mkdir(parents=True, exist_ok=True)

        serialized_data = {
            SURIGenerator.for_symbol(file_path, fqn): fp.to_dict()
            for fqn, fp in hashes.items()
        }

        with sig_path.open("w", encoding="utf-8") as f:
            json.dump(serialized_data, f, indent=2, sort_keys=True)
~~~~~

#### Acts 3: 更新加载逻辑以解析 SURI Key

修改 `load_composite_hashes` 方法，使其能够解析 SURI 键并提取 FQN。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/signature_manager.py
~~~~~
~~~~~python.old
            with sig_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return {}
                result = {}
                for fqn, fp_data in data.items():
                    result[fqn] = Fingerprint.from_dict(fp_data)
                return result
        except (json.JSONDecodeError, OSError, InvalidFingerprintKeyError):
            return {}
~~~~~
~~~~~python.new
            with sig_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return {}
                result = {}
                for suri, fp_data in data.items():
                    try:
                        _path, fragment = SURIGenerator.parse(suri)
                        if fragment:
                            result[fragment] = Fingerprint.from_dict(fp_data)
                    except (ValueError, InvalidFingerprintKeyError):
                        # Gracefully skip malformed SURIs or invalid fingerprint data
                        continue
                return result
        except (json.JSONDecodeError, OSError):
            return {}
~~~~~

### 下一步建议

我们已经成功地升级了基准存档的格式。现在，基准 (`.json`) 和现状 (`.db`) 都拥有了进行精确、高性能比对所需的所有信息。

接下来的任务是 **阶段 3：逻辑驱动重构**，我们将重构 `CheckRunner`，使其完全抛弃实时 AST 解析，转而使用全新的 "Query-First" 模式，即直接在内存中比对从索引库查询出的 `Actual` 状态和从签名文件加载的 `Baseline` 状态。这将是新架构带来性能飞跃的第一次真正体现。
