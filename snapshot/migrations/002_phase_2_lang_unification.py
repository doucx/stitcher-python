from pathlib import Path
from stitcher.refactor.migration import MigrationSpec, Move, MoveDir


def upgrade(spec: MigrationSpec):
    """
    Stitcher 架构重构阶段二：语言能力统一与合并 (Language Capability Unification)

    此脚本将 stitcher-python-adapter 和 stitcher-python-analysis 的核心能力
    按功能垂直切分并迁移到统一的 stitcher-lang-python 包中。
    """

    # --- 1. 解析能力 (Parsing) ---
    
    # 迁移 Griffe 解析器
    # 原: stitcher.adapter.python.griffe_parser
    # 新: stitcher.lang.python.parser.griffe
    spec.add(Move(
        Path("packages/stitcher-python-adapter/src/stitcher/adapter/python/griffe_parser.py"),
        Path("packages/stitcher-lang-python/src/stitcher/lang/python/parser/griffe.py")
    ))
    
    # 迁移 CST 解析器 (原 internal.parser)
    # 原: stitcher.adapter.python.internal.parser
    # 新: stitcher.lang.python.parser.cst
    spec.add(Move(
        Path("packages/stitcher-python-adapter/src/stitcher/adapter/python/internal/parser.py"),
        Path("packages/stitcher-lang-python/src/stitcher/lang/python/parser/cst.py")
    ))

    # --- 2. 索引能力 (Indexing) ---

    # 迁移 Index Adapter
    # 原: stitcher.adapter.python.index_adapter
    # 新: stitcher.lang.python.adapter
    spec.add(Move(
        Path("packages/stitcher-python-adapter/src/stitcher/adapter/python/index_adapter.py"),
        Path("packages/stitcher-lang-python/src/stitcher/lang/python/adapter.py")
    ))

    # 迁移分析模型 (如 UsageLocation)
    # 原: stitcher.python.analysis.models
    # 新: stitcher.lang.python.analysis.models
    spec.add(Move(
        Path("packages/stitcher-python-analysis/src/stitcher/python/analysis/models.py"),
        Path("packages/stitcher-lang-python/src/stitcher/lang/python/analysis/models.py")
    ))

    # 迁移 CST Visitors
    # 原: stitcher.python.analysis.cst.visitors
    # 新: stitcher.lang.python.analysis.visitors
    spec.add(Move(
        Path("packages/stitcher-python-analysis/src/stitcher/python/analysis/cst/visitors.py"),
        Path("packages/stitcher-lang-python/src/stitcher/lang/python/analysis/visitors.py")
    ))

    # --- 3. 转换能力 (Transforming) ---

    # 迁移 Transformer Facade
    # 原: stitcher.adapter.python.internal.transformer
    # 新: stitcher.lang.python.transform.facade
    spec.add(Move(
        Path("packages/stitcher-python-adapter/src/stitcher/adapter/python/internal/transformer.py"),
        Path("packages/stitcher-lang-python/src/stitcher/lang/python/transform/facade.py")
    ))

    # 迁移具体 CST Transformers (Strip/Inject)
    # 原: stitcher.python.analysis.cst.transformers
    # 新: stitcher.lang.python.transform.cst_visitors
    spec.add(Move(
        Path("packages/stitcher-python-analysis/src/stitcher/python/analysis/cst/transformers.py"),
        Path("packages/stitcher-lang-python/src/stitcher/lang/python/transform/cst_visitors.py")
    ))

    # --- 4. 文档能力 (Docstrings) ---

    # 迁移整个 docstring 子包
    # 原: stitcher.adapter.python.docstring
    # 新: stitcher.lang.python.docstring
    spec.add(MoveDir(
        Path("packages/stitcher-python-adapter/src/stitcher/adapter/python/docstring"),
        Path("packages/stitcher-lang-python/src/stitcher/lang/python/docstring")
    ))