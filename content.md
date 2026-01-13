我理解并完全同意您的分析。当前系统在标识符上的不一致性是导致不确定性和脆弱性的根源。为了建立一个本体论正确的系统，我们必须进行这次“大清洗”，以 SURI 作为唯一的、不可动摇的物理事实标识符。

我将严格遵循您制定的计划，首先从净化测试数据开始。这将为后续的核心逻辑重构建立一个明确、可验证的目标。

以下是执行此任务第一步的计划。

## [WIP] test: Align refactor integration tests with SURI/Fragment ontology

### 用户需求

根据 ADAP 协议触发后的新架构方向，必须清洗所有集成测试中的数据。具体要求如下：
1.  所有在测试中创建的 `.json` 签名文件，其键必须从 FQN (完全限定名) 更改为 SURI (Stitcher URI)。
2.  所有在测试中创建的 `.stitcher.yaml` 文档文件，其键必须从 FQN 更改为 Fragment (符号的短名/逻辑路径)。
3.  同步更新测试中的断言，以验证新架构下的正确行为。

### 评论

这是至关重要且正确的第一步。通过首先使测试套件符合新的标识符本体论，我们不仅清除了技术债，更重要的是，我们将测试转化为新架构的活文档和行为规范。这将为后续重写 `Planner` 和 `Adapter` 提供一个坚实、可靠的安全网。

### 目标

1.  定位 `packages/stitcher-refactor/tests/integration/` 目录下所有使用 FQN 作为 sidecar 文件键的测试。
2.  将这些测试中的 `.stitcher.yaml` 文件键修改为 Fragment。
3.  将这些测试中的 `.json` 签名文件键修改为 SURI。
4.  更新相关的变量和断言，确保测试逻辑与新的数据模型对齐。

### 基本原理

我们将遵循“大清洗”指令，逐一修改受影响的集成测试文件。通过 `patch_file` 操作，我们将精确地替换旧的、基于 FQN 的数据定义和断言，代之以基于 SURI 和 Fragment 的新规范。这确保了测试数据与 `d3-principle-arch-stable-identifiers` 原则中定义的物理事实和标识符体系完全一致，为后续的实现层重构铺平了道路。

### 标签

#intent/tooling #intent/refine #flow/ready #priority/critical #comp/tests #concept/state #scope/dx #task/domain/testing #task/object/identifier-ontology #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: 更新 `test_debug_rename_failure.py`

此测试模拟了对 `MessageBus` 的重命名。我们将更新其 sidecar 数据键和断言，以使用 SURI 和 Fragment。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_debug_rename_failure.py
~~~~~
~~~~~python.old
    # 1. ARRANGE
    factory = WorkspaceFactory(tmp_path)
    old_fqn = "stitcher.common.messaging.bus.MessageBus"
    new_fqn = "stitcher.common.messaging.bus.FeedbackBus"

    project_root = (
        factory.with_pyproject(".")
        .with_pyproject("packages/stitcher-common")
        .with_source(
            "packages/stitcher-common/src/stitcher/common/__init__.py",
            "from .messaging.bus import MessageBus\n",
        )
        .with_source(
            "packages/stitcher-common/src/stitcher/common/messaging/protocols.py",
            "class Renderer: pass",
        )
        .with_source(
            "packages/stitcher-common/src/stitcher/common/messaging/__init__.py", ""
        )
        .with_source(
            "packages/stitcher-common/src/stitcher/common/messaging/bus.py",
            BUS_PY_CONTENT,
        )
        # ADD SIDECAR FILES
        .with_docs(
            "packages/stitcher-common/src/stitcher/common/messaging/bus.stitcher.yaml",
            {
                "MessageBus": "Docs for MessageBus.",
                "MessageBus.info": "Docs for info method.",
            },
        )
        .with_raw_file(
            ".stitcher/signatures/packages/stitcher-common/src/stitcher/common/messaging/bus.json",
            json.dumps({old_fqn: {"hash": "abc"}}),
        )
        .build()
    )

    bus_path = (
        project_root / "packages/stitcher-common/src/stitcher/common/messaging/bus.py"
    )
    bus_yaml_path = bus_path.with_suffix(".stitcher.yaml")
    bus_sig_path = (
        project_root
        / ".stitcher/signatures/packages/stitcher-common/src/stitcher/common/messaging/bus.json"
    )

    # 2. LOAD GRAPH
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("stitcher")

    # 3. EXECUTE REFACTOR
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )
    from stitcher.refactor.migration import MigrationSpec
    from stitcher.refactor.engine.planner import Planner

    op = RenameSymbolOperation(old_fqn, new_fqn)
    spec = MigrationSpec().add(op)
    planner = Planner()
    file_ops = planner.plan(spec, ctx)

    tm = TransactionManager(project_root)
    for fop in file_ops:
        if isinstance(fop, WriteFileOp):
            tm.add_write(fop.path, fop.content)
    tm.commit()

    # 4. FINAL ASSERTION
    # Assert Python file content
    updated_content = bus_path.read_text()
    assert "class FeedbackBus:" in updated_content, (
        "BUG: Python code definition was not renamed."
    )

    # Assert YAML sidecar content
    updated_yaml_data = yaml.safe_load(bus_yaml_path.read_text())
    assert "FeedbackBus" in updated_yaml_data, "BUG: YAML doc key was not renamed."
    assert "MessageBus" not in updated_yaml_data
    assert "FeedbackBus.info" in updated_yaml_data, (
        "BUG: YAML doc method key was not renamed."
    )

    # Assert Signature sidecar content
    updated_sig_data = json.loads(bus_sig_path.read_text())
    assert new_fqn in updated_sig_data, "BUG: Signature JSON FQN key was not renamed."
    assert old_fqn not in updated_sig_data
    assert updated_sig_data[new_fqn] == {"hash": "abc"}
~~~~~
~~~~~python.new
    # 1. ARRANGE
    factory = WorkspaceFactory(tmp_path)
    old_fqn = "stitcher.common.messaging.bus.MessageBus"
    new_fqn = "stitcher.common.messaging.bus.FeedbackBus"

    # Define paths and identifiers according to the new ontology
    py_rel_path = "packages/stitcher-common/src/stitcher/common/messaging/bus.py"
    old_suri = f"py://{py_rel_path}#MessageBus"
    new_suri = f"py://{py_rel_path}#FeedbackBus"

    project_root = (
        factory.with_pyproject(".")
        .with_pyproject("packages/stitcher-common")
        .with_source(
            "packages/stitcher-common/src/stitcher/common/__init__.py",
            "from .messaging.bus import MessageBus\n",
        )
        .with_source(
            "packages/stitcher-common/src/stitcher/common/messaging/protocols.py",
            "class Renderer: pass",
        )
        .with_source(
            "packages/stitcher-common/src/stitcher/common/messaging/__init__.py", ""
        )
        .with_source(
            "packages/stitcher-common/src/stitcher/common/messaging/bus.py",
            BUS_PY_CONTENT,
        )
        # ADD SIDECAR FILES
        .with_docs(
            "packages/stitcher-common/src/stitcher/common/messaging/bus.stitcher.yaml",
            {
                # Keys are now Fragments (short names)
                "MessageBus": "Docs for MessageBus.",
                "MessageBus.info": "Docs for info method.",
            },
        )
        .with_raw_file(
            ".stitcher/signatures/packages/stitcher-common/src/stitcher/common/messaging/bus.json",
            # Key is now a SURI
            json.dumps({old_suri: {"hash": "abc"}}),
        )
        .build()
    )

    bus_path = (
        project_root / "packages/stitcher-common/src/stitcher/common/messaging/bus.py"
    )
    bus_yaml_path = bus_path.with_suffix(".stitcher.yaml")
    bus_sig_path = (
        project_root
        / ".stitcher/signatures/packages/stitcher-common/src/stitcher/common/messaging/bus.json"
    )

    # 2. LOAD GRAPH
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("stitcher")

    # 3. EXECUTE REFACTOR
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )
    from stitcher.refactor.migration import MigrationSpec
    from stitcher.refactor.engine.planner import Planner

    op = RenameSymbolOperation(old_fqn, new_fqn)
    spec = MigrationSpec().add(op)
    planner = Planner()
    file_ops = planner.plan(spec, ctx)

    tm = TransactionManager(project_root)
    for fop in file_ops:
        if isinstance(fop, WriteFileOp):
            tm.add_write(fop.path, fop.content)
    tm.commit()

    # 4. FINAL ASSERTION
    # Assert Python file content
    updated_content = bus_path.read_text()
    assert "class FeedbackBus:" in updated_content, (
        "BUG: Python code definition was not renamed."
    )

    # Assert YAML sidecar content (Fragments)
    updated_yaml_data = yaml.safe_load(bus_yaml_path.read_text())
    assert "FeedbackBus" in updated_yaml_data, "BUG: YAML doc key was not renamed."
    assert "MessageBus" not in updated_yaml_data
    assert "FeedbackBus.info" in updated_yaml_data, (
        "BUG: YAML doc method key was not renamed."
    )

    # Assert Signature sidecar content (SURI)
    updated_sig_data = json.loads(bus_sig_path.read_text())
    assert new_suri in updated_sig_data, "BUG: Signature JSON SURI key was not renamed."
    assert old_suri not in updated_sig_data
    assert updated_sig_data[new_suri] == {"hash": "abc"}
~~~~~

#### Acts 2: 更新 `test_monorepo_refactor_e2e.py`

此测试验证跨包重构。同样，我们需要将 sidecar 文件中的 FQN 键替换为新规范。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_monorepo_refactor_e2e.py
~~~~~
~~~~~python.old
    project_root = (
        factory.with_pyproject("packages/pkg_a")
        .with_source("packages/pkg_a/src/pkga_lib/__init__.py", "")
        .with_source("packages/pkg_a/src/pkga_lib/core.py", "class SharedClass: pass")
        .with_docs(
            "packages/pkg_a/src/pkga_lib/core.stitcher.yaml",
            {"pkga_lib.core.SharedClass": "A shared class."},
        )
        .with_raw_file(
            ".stitcher/signatures/packages/pkg_a/src/pkga_lib/core.json",
            json.dumps({"pkga_lib.core.SharedClass": {"hash": "abc"}}),
        )
        .with_pyproject("packages/pkg_b")
        .with_source("packages/pkg_b/src/pkgb_app/__init__.py", "")
        .with_source(
            "packages/pkg_b/src/pkgb_app/main.py",
            "from pkga_lib.core import SharedClass\n\ninstance = SharedClass()",
        )
        .build()
    )

    # Define paths for the operation
    src_path = project_root / "packages/pkg_a/src/pkga_lib/core.py"
    dest_path = project_root / "packages/pkg_a/src/pkga_lib/utils/tools.py"
    consumer_path = project_root / "packages/pkg_b/src/pkgb_app/main.py"

    # 2. ACT
    # The new SemanticGraph should automatically find both 'src' dirs
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    assert project_root / "packages/pkg_a/src" in graph.search_paths
    assert project_root / "packages/pkg_b/src" in graph.search_paths

    # Load all packages
    graph.load("pkga_lib")
    graph.load("pkgb_app")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )

    from stitcher.refactor.migration import MigrationSpec
    from stitcher.refactor.engine.planner import Planner

    op = MoveFileOperation(src_path, dest_path)
    spec = MigrationSpec().add(op)
    planner = Planner()
    file_ops = planner.plan(spec, ctx)

    tm = TransactionManager(project_root)
    for fop in file_ops:
        if isinstance(fop, MoveFileOp):
            tm.add_move(fop.path, fop.dest)
        elif isinstance(fop, WriteFileOp):
            tm.add_write(fop.path, fop.content)
    tm.commit()

    # 3. ASSERT
    # A. File system verification
    assert not src_path.exists()
    assert dest_path.exists()
    dest_yaml = dest_path.with_suffix(".stitcher.yaml")
    assert dest_yaml.exists()
    dest_sig_path = (
        project_root
        / ".stitcher/signatures/packages/pkg_a/src/pkga_lib/utils/tools.json"
    )
    assert dest_sig_path.exists()

    # B. Cross-package import verification
    updated_consumer_code = consumer_path.read_text()
    expected_import = "from pkga_lib.utils.tools import SharedClass"
    assert expected_import in updated_consumer_code

    # C. Sidecar FQN verification
    new_yaml_data = yaml.safe_load(dest_yaml.read_text())
    expected_fqn = "pkga_lib.utils.tools.SharedClass"
    assert expected_fqn in new_yaml_data
    assert new_yaml_data[expected_fqn] == "A shared class."

    new_sig_data = json.loads(dest_sig_path.read_text())
    assert expected_fqn in new_sig_data
    assert new_sig_data[expected_fqn] == {"hash": "abc"}
~~~~~
~~~~~python.new
    # --- Define identifiers based on the new ontology ---
    py_rel_path = "packages/pkg_a/src/pkga_lib/core.py"
    old_suri = f"py://{py_rel_path}#SharedClass"

    project_root = (
        factory.with_pyproject("packages/pkg_a")
        .with_source("packages/pkg_a/src/pkga_lib/__init__.py", "")
        .with_source("packages/pkg_a/src/pkga_lib/core.py", "class SharedClass: pass")
        .with_docs(
            "packages/pkg_a/src/pkga_lib/core.stitcher.yaml",
            # Key is now Fragment
            {"SharedClass": "A shared class."},
        )
        .with_raw_file(
            ".stitcher/signatures/packages/pkg_a/src/pkga_lib/core.json",
            # Key is now SURI
            json.dumps({old_suri: {"hash": "abc"}}),
        )
        .with_pyproject("packages/pkg_b")
        .with_source("packages/pkg_b/src/pkgb_app/__init__.py", "")
        .with_source(
            "packages/pkg_b/src/pkgb_app/main.py",
            "from pkga_lib.core import SharedClass\n\ninstance = SharedClass()",
        )
        .build()
    )

    # Define paths for the operation
    src_path = project_root / "packages/pkg_a/src/pkga_lib/core.py"
    dest_path = project_root / "packages/pkg_a/src/pkga_lib/utils/tools.py"
    consumer_path = project_root / "packages/pkg_b/src/pkgb_app/main.py"

    # 2. ACT
    # The new SemanticGraph should automatically find both 'src' dirs
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    assert project_root / "packages/pkg_a/src" in graph.search_paths
    assert project_root / "packages/pkg_b/src" in graph.search_paths

    # Load all packages
    graph.load("pkga_lib")
    graph.load("pkgb_app")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )

    from stitcher.refactor.migration import MigrationSpec
    from stitcher.refactor.engine.planner import Planner

    op = MoveFileOperation(src_path, dest_path)
    spec = MigrationSpec().add(op)
    planner = Planner()
    file_ops = planner.plan(spec, ctx)

    tm = TransactionManager(project_root)
    for fop in file_ops:
        if isinstance(fop, MoveFileOp):
            tm.add_move(fop.path, fop.dest)
        elif isinstance(fop, WriteFileOp):
            tm.add_write(fop.path, fop.content)
    tm.commit()

    # 3. ASSERT
    # A. File system verification
    assert not src_path.exists()
    assert dest_path.exists()
    dest_yaml = dest_path.with_suffix(".stitcher.yaml")
    assert dest_yaml.exists()
    dest_sig_path = (
        project_root
        / ".stitcher/signatures/packages/pkg_a/src/pkga_lib/utils/tools.json"
    )
    assert dest_sig_path.exists()

    # B. Cross-package import verification
    updated_consumer_code = consumer_path.read_text()
    expected_import = "from pkga_lib.utils.tools import SharedClass"
    assert expected_import in updated_consumer_code

    # C. Sidecar key verification
    # YAML uses Fragments
    new_yaml_data = yaml.safe_load(dest_yaml.read_text())
    assert "SharedClass" in new_yaml_data
    assert new_yaml_data["SharedClass"] == "A shared class."

    # JSON uses SURIs
    new_py_rel_path = "packages/pkg_a/src/pkga_lib/utils/tools.py"
    expected_suri = f"py://{new_py_rel_path}#SharedClass"
    new_sig_data = json.loads(dest_sig_path.read_text())
    assert expected_suri in new_sig_data
    assert new_sig_data[expected_suri] == {"hash": "abc"}
~~~~~

#### Acts 3: 更新 `test_move_directory_e2e.py`

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_directory_e2e.py
~~~~~
~~~~~python.old
    project_root = (
        factory.with_pyproject(".")
        .with_source("mypkg/core/__init__.py", "")
        .with_source("mypkg/core/utils.py", "class Helper: pass")
        .with_raw_file("mypkg/core/config.txt", "setting=value")
        .with_raw_file("mypkg/core/.env", "SECRET=123")
        .with_source(
            "app.py",
            """
            from mypkg.core.utils import Helper

            h = Helper()
            """,
        )
        .with_docs(
            "mypkg/core/utils.stitcher.yaml",
            {"mypkg.core.utils.Helper": "Doc for Helper"},
        )
        .with_raw_file(
            ".stitcher/signatures/mypkg/core/utils.json",
            json.dumps({"mypkg.core.utils.Helper": {"hash": "123"}}),
        )
        .build()
    )

    core_dir = project_root / "mypkg/core"
    services_dir = project_root / "mypkg/services"
    app_py = project_root / "app.py"
    sig_root = project_root / ".stitcher/signatures"

    # 2. ANALYSIS
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("mypkg")
    graph.load("app")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )

    from stitcher.refactor.migration import MigrationSpec
    from stitcher.refactor.engine.planner import Planner

    op = MoveDirectoryOperation(core_dir, services_dir)
    spec = MigrationSpec().add(op)
    planner = Planner()
    file_ops = planner.plan(spec, ctx)

    # 3. EXECUTION
    tm = TransactionManager(project_root)
    for fop in file_ops:
        if isinstance(fop, MoveFileOp):
            tm.add_move(fop.path, fop.dest)
        elif isinstance(fop, DeleteDirectoryOp):
            tm.add_delete_dir(fop.path)
        elif isinstance(fop, WriteFileOp):
            tm.add_write(fop.path, fop.content)
    tm.commit()

    # 4. VERIFICATION
    assert not core_dir.exists()
    assert services_dir.exists()
    assert (services_dir / "utils.py").exists()
    assert (services_dir / "config.txt").read_text() == "setting=value"

    assert (services_dir / "utils.stitcher.yaml").exists()
    new_sig_path = sig_root / "mypkg/services/utils.json"
    assert new_sig_path.exists()

    new_yaml_data = yaml.safe_load((services_dir / "utils.stitcher.yaml").read_text())
    assert "mypkg.services.utils.Helper" in new_yaml_data
    new_sig_data = json.loads(new_sig_path.read_text())
    assert "mypkg.services.utils.Helper" in new_sig_data

    updated_app_code = app_py.read_text(encoding="utf-8")
    assert "from mypkg.services.utils import Helper" in updated_app_code
~~~~~
~~~~~python.new
    py_rel_path = "mypkg/core/utils.py"
    old_suri = f"py://{py_rel_path}#Helper"

    project_root = (
        factory.with_pyproject(".")
        .with_source("mypkg/core/__init__.py", "")
        .with_source("mypkg/core/utils.py", "class Helper: pass")
        .with_raw_file("mypkg/core/config.txt", "setting=value")
        .with_raw_file("mypkg/core/.env", "SECRET=123")
        .with_source(
            "app.py",
            """
            from mypkg.core.utils import Helper

            h = Helper()
            """,
        )
        .with_docs(
            "mypkg/core/utils.stitcher.yaml",
            # Key is Fragment
            {"Helper": "Doc for Helper"},
        )
        .with_raw_file(
            ".stitcher/signatures/mypkg/core/utils.json",
            # Key is SURI
            json.dumps({old_suri: {"hash": "123"}}),
        )
        .build()
    )

    core_dir = project_root / "mypkg/core"
    services_dir = project_root / "mypkg/services"
    app_py = project_root / "app.py"
    sig_root = project_root / ".stitcher/signatures"

    # 2. ANALYSIS
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("mypkg")
    graph.load("app")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )

    from stitcher.refactor.migration import MigrationSpec
    from stitcher.refactor.engine.planner import Planner

    op = MoveDirectoryOperation(core_dir, services_dir)
    spec = MigrationSpec().add(op)
    planner = Planner()
    file_ops = planner.plan(spec, ctx)

    # 3. EXECUTION
    tm = TransactionManager(project_root)
    for fop in file_ops:
        if isinstance(fop, MoveFileOp):
            tm.add_move(fop.path, fop.dest)
        elif isinstance(fop, DeleteDirectoryOp):
            tm.add_delete_dir(fop.path)
        elif isinstance(fop, WriteFileOp):
            tm.add_write(fop.path, fop.content)
    tm.commit()

    # 4. VERIFICATION
    assert not core_dir.exists()
    assert services_dir.exists()
    assert (services_dir / "utils.py").exists()
    assert (services_dir / "config.txt").read_text() == "setting=value"

    assert (services_dir / "utils.stitcher.yaml").exists()
    new_sig_path = sig_root / "mypkg/services/utils.json"
    assert new_sig_path.exists()

    # YAML key is Fragment
    new_yaml_data = yaml.safe_load((services_dir / "utils.stitcher.yaml").read_text())
    assert "Helper" in new_yaml_data

    # JSON key is SURI
    new_py_rel_path = "mypkg/services/utils.py"
    expected_suri = f"py://{new_py_rel_path}#Helper"
    new_sig_data = json.loads(new_sig_path.read_text())
    assert expected_suri in new_sig_data

    updated_app_code = app_py.read_text(encoding="utf-8")
    assert "from mypkg.services.utils import Helper" in updated_app_code
~~~~~

#### Acts 4: 更新 `test_move_directory_monorepo_e2e.py`

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_directory_monorepo_e2e.py
~~~~~
~~~~~python.old
    project_root = (
        factory
        # --- cascade-engine package ---
        .with_pyproject("cascade-engine")
        .with_source(
            "cascade-engine/src/cascade/__init__.py",
            "__path__ = __import__('pkgutil').extend_path(__path__, __name__)",
        )
        .with_source("cascade-engine/src/cascade/engine/__init__.py", "")
        .with_source("cascade-engine/src/cascade/engine/core/__init__.py", "")
        .with_source(
            "cascade-engine/src/cascade/engine/core/logic.py", "class EngineLogic: pass"
        )
        .with_docs(
            "cascade-engine/src/cascade/engine/core/logic.stitcher.yaml",
            {"cascade.engine.core.logic.EngineLogic": "Core engine logic."},
        )
        .with_raw_file(
            ".stitcher/signatures/cascade-engine/src/cascade/engine/core/logic.json",
            json.dumps({"cascade.engine.core.logic.EngineLogic": {"hash": "abc"}}),
        )
        # --- cascade-runtime package ---
        .with_pyproject("cascade-runtime")
        .with_source(
            "cascade-runtime/src/cascade/__init__.py",
            "__path__ = __import__('pkgutil').extend_path(__path__, __name__)",
        )
        .with_source("cascade-runtime/src/cascade/runtime/__init__.py", "")
        .with_source(
            "cascade-runtime/src/cascade/runtime/app.py",
            "from cascade.engine.core.logic import EngineLogic\n\nlogic = EngineLogic()",
        )
    ).build()

    # Define paths for the operation
    src_dir = project_root / "cascade-engine/src/cascade/engine/core"
    dest_dir = project_root / "cascade-runtime/src/cascade/runtime/core"
    consumer_path = project_root / "cascade-runtime/src/cascade/runtime/app.py"

    # 2. ACT
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    # Load the top-level namespace package. Griffe will discover all its parts
    # from the search paths provided by the Workspace.
    graph.load("cascade")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )

    from stitcher.refactor.migration import MigrationSpec
    from stitcher.refactor.engine.planner import Planner

    op = MoveDirectoryOperation(src_dir, dest_dir)
    spec = MigrationSpec().add(op)
    planner = Planner()
    file_ops = planner.plan(spec, ctx)

    tm = TransactionManager(project_root)
    for fop in file_ops:
        if isinstance(fop, MoveFileOp):
            tm.add_move(fop.path, fop.dest)
        elif isinstance(fop, DeleteDirectoryOp):
            tm.add_delete_dir(fop.path)
        elif isinstance(fop, WriteFileOp):
            tm.add_write(fop.path, fop.content)
    tm.commit()

    # 3. ASSERT
    # A. File system verification
    assert not src_dir.exists()
    assert dest_dir.exists()
    new_py_file = dest_dir / "logic.py"
    new_yaml_file = new_py_file.with_suffix(".stitcher.yaml")
    new_sig_file_path = (
        project_root
        / ".stitcher/signatures/cascade-runtime/src/cascade/runtime/core/logic.json"
    )

    assert new_py_file.exists()
    assert new_yaml_file.exists()
    assert new_sig_file_path.exists()

    # B. Cross-package import verification
    updated_consumer_code = consumer_path.read_text()
    expected_import = "from cascade.runtime.core.logic import EngineLogic"
    assert expected_import in updated_consumer_code

    # C. Sidecar FQN verification
    new_yaml_data = yaml.safe_load(new_yaml_file.read_text())
    expected_fqn = "cascade.runtime.core.logic.EngineLogic"
    assert expected_fqn in new_yaml_data
    assert new_yaml_data[expected_fqn] == "Core engine logic."

    new_sig_data = json.loads(new_sig_file_path.read_text())
    assert expected_fqn in new_sig_data
    assert new_sig_data[expected_fqn] == {"hash": "abc"}
~~~~~
~~~~~python.new
    py_rel_path = "cascade-engine/src/cascade/engine/core/logic.py"
    old_suri = f"py://{py_rel_path}#EngineLogic"

    project_root = (
        factory
        # --- cascade-engine package ---
        .with_pyproject("cascade-engine")
        .with_source(
            "cascade-engine/src/cascade/__init__.py",
            "__path__ = __import__('pkgutil').extend_path(__path__, __name__)",
        )
        .with_source("cascade-engine/src/cascade/engine/__init__.py", "")
        .with_source("cascade-engine/src/cascade/engine/core/__init__.py", "")
        .with_source(
            "cascade-engine/src/cascade/engine/core/logic.py", "class EngineLogic: pass"
        )
        .with_docs(
            "cascade-engine/src/cascade/engine/core/logic.stitcher.yaml",
            # Key is Fragment
            {"EngineLogic": "Core engine logic."},
        )
        .with_raw_file(
            ".stitcher/signatures/cascade-engine/src/cascade/engine/core/logic.json",
            # Key is SURI
            json.dumps({old_suri: {"hash": "abc"}}),
        )
        # --- cascade-runtime package ---
        .with_pyproject("cascade-runtime")
        .with_source(
            "cascade-runtime/src/cascade/__init__.py",
            "__path__ = __import__('pkgutil').extend_path(__path__, __name__)",
        )
        .with_source("cascade-runtime/src/cascade/runtime/__init__.py", "")
        .with_source(
            "cascade-runtime/src/cascade/runtime/app.py",
            "from cascade.engine.core.logic import EngineLogic\n\nlogic = EngineLogic()",
        )
    ).build()

    # Define paths for the operation
    src_dir = project_root / "cascade-engine/src/cascade/engine/core"
    dest_dir = project_root / "cascade-runtime/src/cascade/runtime/core"
    consumer_path = project_root / "cascade-runtime/src/cascade/runtime/app.py"

    # 2. ACT
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    # Load the top-level namespace package. Griffe will discover all its parts
    # from the search paths provided by the Workspace.
    graph.load("cascade")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )

    from stitcher.refactor.migration import MigrationSpec
    from stitcher.refactor.engine.planner import Planner

    op = MoveDirectoryOperation(src_dir, dest_dir)
    spec = MigrationSpec().add(op)
    planner = Planner()
    file_ops = planner.plan(spec, ctx)

    tm = TransactionManager(project_root)
    for fop in file_ops:
        if isinstance(fop, MoveFileOp):
            tm.add_move(fop.path, fop.dest)
        elif isinstance(fop, DeleteDirectoryOp):
            tm.add_delete_dir(fop.path)
        elif isinstance(fop, WriteFileOp):
            tm.add_write(fop.path, fop.content)
    tm.commit()

    # 3. ASSERT
    # A. File system verification
    assert not src_dir.exists()
    assert dest_dir.exists()
    new_py_file = dest_dir / "logic.py"
    new_yaml_file = new_py_file.with_suffix(".stitcher.yaml")
    new_sig_file_path = (
        project_root
        / ".stitcher/signatures/cascade-runtime/src/cascade/runtime/core/logic.json"
    )

    assert new_py_file.exists()
    assert new_yaml_file.exists()
    assert new_sig_file_path.exists()

    # B. Cross-package import verification
    updated_consumer_code = consumer_path.read_text()
    expected_import = "from cascade.runtime.core.logic import EngineLogic"
    assert expected_import in updated_consumer_code

    # C. Sidecar key verification
    # YAML uses Fragments
    new_yaml_data = yaml.safe_load(new_yaml_file.read_text())
    assert "EngineLogic" in new_yaml_data
    assert new_yaml_data["EngineLogic"] == "Core engine logic."

    # JSON uses SURIs
    new_py_rel_path = "cascade-runtime/src/cascade/runtime/core/logic.py"
    expected_suri = f"py://{new_py_rel_path}#EngineLogic"
    new_sig_data = json.loads(new_sig_file_path.read_text())
    assert expected_suri in new_sig_data
    assert new_sig_data[expected_suri] == {"hash": "abc"}
~~~~~

#### Acts 5: 更新 `test_move_file_e2e.py`

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_file_e2e.py
~~~~~
~~~~~python.old
    project_root = (
        factory.with_pyproject(".")
        .with_source("mypkg/__init__.py", "")
        .with_source("mypkg/old.py", "class A:\n    pass")
        .with_source(
            "mypkg/app.py",
            """
            import mypkg.old
            from mypkg.old import A
            from . import old
            from .old import A as AliasA

            x = mypkg.old.A()
            y = A()
            z = old.A()
            w = AliasA()
            """,
        )
        .with_docs("mypkg/old.stitcher.yaml", {"mypkg.old.A": "Doc"})
        .with_raw_file(
            ".stitcher/signatures/mypkg/old.json",
            json.dumps({"mypkg.old.A": {"h": "1"}}),
        )
        .build()
    )

    pkg_dir = project_root / "mypkg"
    old_py = pkg_dir / "old.py"
    app_py = pkg_dir / "app.py"
    old_yaml = old_py.with_suffix(".stitcher.yaml")
    sig_dir = project_root / ".stitcher/signatures/mypkg"
    old_json = sig_dir / "old.json"
    new_py = pkg_dir / "new.py"

    # 2. Analyze
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("mypkg")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )
    from stitcher.refactor.migration import MigrationSpec
    from stitcher.refactor.engine.planner import Planner

    op = MoveFileOperation(old_py, new_py)
    spec = MigrationSpec().add(op)
    planner = Planner()
    file_ops = planner.plan(spec, ctx)

    # 3. Commit
    tm = TransactionManager(project_root)
    for fop in file_ops:
        if isinstance(fop, MoveFileOp):
            tm.add_move(fop.path, fop.dest)
        elif isinstance(fop, WriteFileOp):
            tm.add_write(fop.path, fop.content)
    tm.commit()

    # 4. Verify
    # Files moved?
    assert not old_py.exists()
    assert new_py.exists()
    assert not old_yaml.exists()
    assert new_py.with_suffix(".stitcher.yaml").exists()
    assert not old_json.exists()
    assert (sig_dir / "new.json").exists()

    # Content updated?
    new_app = app_py.read_text("utf-8")
    assert "import mypkg.new" in new_app
    assert "from mypkg.new import A" in new_app
    assert "from . import new" in new_app
    # Note: Stitcher now converts relative imports with a module part to absolute imports for robustness
    assert "from mypkg.new import A as AliasA" in new_app

    # Sidecar Keys
    new_yaml_content = new_py.with_suffix(".stitcher.yaml").read_text("utf-8")
    assert "mypkg.new.A" in new_yaml_content
    assert "mypkg.old.A" not in new_yaml_content
~~~~~
~~~~~python.new
    py_rel_path = "mypkg/old.py"
    old_suri = f"py://{py_rel_path}#A"

    project_root = (
        factory.with_pyproject(".")
        .with_source("mypkg/__init__.py", "")
        .with_source("mypkg/old.py", "class A:\n    pass")
        .with_source(
            "mypkg/app.py",
            """
            import mypkg.old
            from mypkg.old import A
            from . import old
            from .old import A as AliasA

            x = mypkg.old.A()
            y = A()
            z = old.A()
            w = AliasA()
            """,
        )
        .with_docs("mypkg/old.stitcher.yaml", {"A": "Doc"})  # Key is Fragment
        .with_raw_file(
            ".stitcher/signatures/mypkg/old.json",
            json.dumps({old_suri: {"h": "1"}}),  # Key is SURI
        )
        .build()
    )

    pkg_dir = project_root / "mypkg"
    old_py = pkg_dir / "old.py"
    app_py = pkg_dir / "app.py"
    old_yaml = old_py.with_suffix(".stitcher.yaml")
    sig_dir = project_root / ".stitcher/signatures/mypkg"
    old_json = sig_dir / "old.json"
    new_py = pkg_dir / "new.py"

    # 2. Analyze
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("mypkg")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )
    from stitcher.refactor.migration import MigrationSpec
    from stitcher.refactor.engine.planner import Planner

    op = MoveFileOperation(old_py, new_py)
    spec = MigrationSpec().add(op)
    planner = Planner()
    file_ops = planner.plan(spec, ctx)

    # 3. Commit
    tm = TransactionManager(project_root)
    for fop in file_ops:
        if isinstance(fop, MoveFileOp):
            tm.add_move(fop.path, fop.dest)
        elif isinstance(fop, WriteFileOp):
            tm.add_write(fop.path, fop.content)
    tm.commit()

    # 4. Verify
    # Files moved?
    assert not old_py.exists()
    assert new_py.exists()
    assert not old_yaml.exists()
    assert new_py.with_suffix(".stitcher.yaml").exists()
    assert not old_json.exists()
    assert (sig_dir / "new.json").exists()

    # Content updated?
    new_app = app_py.read_text("utf-8")
    assert "import mypkg.new" in new_app
    assert "from mypkg.new import A" in new_app
    assert "from . import new" in new_app
    # Note: Stitcher now converts relative imports with a module part to absolute imports for robustness
    assert "from mypkg.new import A as AliasA" in new_app

    # Sidecar Keys
    new_yaml_content = new_py.with_suffix(".stitcher.yaml").read_text("utf-8")
    assert "A" in new_yaml_content
    assert "mypkg.new.A" not in new_yaml_content
~~~~~

#### Acts 6: 更新 `test_move_nested_directory_e2e.py`

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_nested_directory_e2e.py
~~~~~
~~~~~python.old
    project_root = (
        factory.with_pyproject(".")
        .with_source("src/cascade/__init__.py", "")
        .with_source("src/cascade/core/__init__.py", "")
        .with_source("src/cascade/core/adapters/__init__.py", "")
        .with_source("src/cascade/core/adapters/cache/__init__.py", "")
        .with_source(
            "src/cascade/core/adapters/cache/in_memory.py", "class InMemoryCache: pass"
        )
        .with_docs(
            "src/cascade/core/adapters/cache/in_memory.stitcher.yaml",
            {"cascade.core.adapters.cache.in_memory.InMemoryCache": "Doc for Cache"},
        )
        .with_raw_file(
            ".stitcher/signatures/src/cascade/core/adapters/cache/in_memory.json",
            json.dumps(
                {"cascade.core.adapters.cache.in_memory.InMemoryCache": {"h": "123"}}
            ),
        )
        .with_source(
            "src/app.py",
            "from cascade.core.adapters.cache.in_memory import InMemoryCache",
        )
        .build()
    )

    # Define paths for the move operation
    src_dir_to_move = project_root / "src/cascade/core/adapters"
    dest_dir = project_root / "src/cascade/runtime/adapters"
    app_py_path = project_root / "src/app.py"

    # 2. ACT
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    # We load 'cascade' and 'app' to build the full semantic picture
    graph.load("cascade")
    graph.load("app")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )

    from stitcher.refactor.migration import MigrationSpec
    from stitcher.refactor.engine.planner import Planner

    op = MoveDirectoryOperation(src_dir_to_move, dest_dir)
    spec = MigrationSpec().add(op)
    planner = Planner()
    file_ops = planner.plan(spec, ctx)

    tm = TransactionManager(project_root)
    for fop in file_ops:
        if isinstance(fop, MoveFileOp):
            tm.add_move(fop.path, fop.dest)
        elif isinstance(fop, DeleteDirectoryOp):
            tm.add_delete_dir(fop.path)
        elif isinstance(fop, WriteFileOp):
            tm.add_write(fop.path, fop.content)
    tm.commit()

    # 3. ASSERT
    # A. Verify file system structure
    assert not src_dir_to_move.exists()
    assert dest_dir.exists()
    new_py_file = dest_dir / "cache/in_memory.py"
    new_yaml_file = new_py_file.with_suffix(".stitcher.yaml")
    new_sig_file_path = (
        project_root
        / ".stitcher/signatures/src/cascade/runtime/adapters/cache/in_memory.json"
    )

    assert new_py_file.exists()
    assert new_yaml_file.exists()
    assert new_sig_file_path.exists()

    # B. Verify content of external references
    updated_app_code = app_py_path.read_text()
    expected_import = (
        "from cascade.runtime.adapters.cache.in_memory import InMemoryCache"
    )
    assert expected_import in updated_app_code

    # C. Verify content of moved sidecar files (FQN update)
    new_yaml_data = yaml.safe_load(new_yaml_file.read_text())
    expected_yaml_fqn = "cascade.runtime.adapters.cache.in_memory.InMemoryCache"
    assert expected_yaml_fqn in new_yaml_data
    assert new_yaml_data[expected_yaml_fqn] == "Doc for Cache"

    new_sig_data = json.loads(new_sig_file_path.read_text())
    assert expected_yaml_fqn in new_sig_data
    assert new_sig_data[expected_yaml_fqn] == {"h": "123"}
~~~~~
~~~~~python.new
    py_rel_path = "src/cascade/core/adapters/cache/in_memory.py"
    old_suri = f"py://{py_rel_path}#InMemoryCache"

    project_root = (
        factory.with_pyproject(".")
        .with_source("src/cascade/__init__.py", "")
        .with_source("src/cascade/core/__init__.py", "")
        .with_source("src/cascade/core/adapters/__init__.py", "")
        .with_source("src/cascade/core/adapters/cache/__init__.py", "")
        .with_source(
            "src/cascade/core/adapters/cache/in_memory.py", "class InMemoryCache: pass"
        )
        .with_docs(
            "src/cascade/core/adapters/cache/in_memory.stitcher.yaml",
            # Key is Fragment
            {"InMemoryCache": "Doc for Cache"},
        )
        .with_raw_file(
            ".stitcher/signatures/src/cascade/core/adapters/cache/in_memory.json",
            # Key is SURI
            json.dumps({old_suri: {"h": "123"}}),
        )
        .with_source(
            "src/app.py",
            "from cascade.core.adapters.cache.in_memory import InMemoryCache",
        )
        .build()
    )

    # Define paths for the move operation
    src_dir_to_move = project_root / "src/cascade/core/adapters"
    dest_dir = project_root / "src/cascade/runtime/adapters"
    app_py_path = project_root / "src/app.py"

    # 2. ACT
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    # We load 'cascade' and 'app' to build the full semantic picture
    graph.load("cascade")
    graph.load("app")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )

    from stitcher.refactor.migration import MigrationSpec
    from stitcher.refactor.engine.planner import Planner

    op = MoveDirectoryOperation(src_dir_to_move, dest_dir)
    spec = MigrationSpec().add(op)
    planner = Planner()
    file_ops = planner.plan(spec, ctx)

    tm = TransactionManager(project_root)
    for fop in file_ops:
        if isinstance(fop, MoveFileOp):
            tm.add_move(fop.path, fop.dest)
        elif isinstance(fop, DeleteDirectoryOp):
            tm.add_delete_dir(fop.path)
        elif isinstance(fop, WriteFileOp):
            tm.add_write(fop.path, fop.content)
    tm.commit()

    # 3. ASSERT
    # A. Verify file system structure
    assert not src_dir_to_move.exists()
    assert dest_dir.exists()
    new_py_file = dest_dir / "cache/in_memory.py"
    new_yaml_file = new_py_file.with_suffix(".stitcher.yaml")
    new_sig_file_path = (
        project_root
        / ".stitcher/signatures/src/cascade/runtime/adapters/cache/in_memory.json"
    )

    assert new_py_file.exists()
    assert new_yaml_file.exists()
    assert new_sig_file_path.exists()

    # B. Verify content of external references
    updated_app_code = app_py_path.read_text()
    expected_import = (
        "from cascade.runtime.adapters.cache.in_memory import InMemoryCache"
    )
    assert expected_import in updated_app_code

    # C. Verify content of moved sidecar files
    # YAML key is Fragment
    new_yaml_data = yaml.safe_load(new_yaml_file.read_text())
    assert "InMemoryCache" in new_yaml_data
    assert new_yaml_data["InMemoryCache"] == "Doc for Cache"

    # JSON key is SURI
    new_py_rel_path = "src/cascade/runtime/adapters/cache/in_memory.py"
    expected_suri = f"py://{new_py_rel_path}#InMemoryCache"
    new_sig_data = json.loads(new_sig_file_path.read_text())
    assert expected_suri in new_sig_data
    assert new_sig_data[expected_suri] == {"h": "123"}
~~~~~

#### Acts 7: 更新 `test_rename_e2e.py`

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_e2e.py
~~~~~
~~~~~python.old
    project_root = (
        factory.with_pyproject(".")
        .with_source(
            "mypkg/core.py",
            """
        class OldHelper:
            pass

        def old_func():
            pass
        """,
        )
        .with_source(
            "mypkg/app.py",
            """
        from .core import OldHelper, old_func

        h = OldHelper()
        old_func()
        """,
        )
        .with_source("mypkg/__init__.py", "")
        .with_docs(
            "mypkg/core.stitcher.yaml",
            {
                "mypkg.core.OldHelper": "This is the old helper.",
                "mypkg.core.old_func": "This is an old function.",
            },
        )
        .with_raw_file(
            ".stitcher/signatures/mypkg/core.json",
            json.dumps(
                {
                    "mypkg.core.OldHelper": {"baseline_code_structure_hash": "hash1"},
                    "mypkg.core.old_func": {"baseline_code_structure_hash": "hash2"},
                }
            ),
        )
        .build()
    )

    core_path = project_root / "mypkg/core.py"
    app_path = project_root / "mypkg/app.py"
    doc_path = project_root / "mypkg/core.stitcher.yaml"
    sig_path = project_root / ".stitcher/signatures/mypkg/core.json"

    # 2. Analysis Phase
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("mypkg")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )

    # 3. Planning Phase
    from stitcher.refactor.migration import MigrationSpec
    from stitcher.refactor.engine.planner import Planner

    op = RenameSymbolOperation(
        old_fqn="mypkg.core.OldHelper", new_fqn="mypkg.core.NewHelper"
    )
    spec = MigrationSpec().add(op)
    planner = Planner()
    file_ops = planner.plan(spec, ctx)

    # 4. Execution Phase
    tm = TransactionManager(project_root)
    for op in file_ops:
        # In a real app, we might add ops one by one. Here we add all.
        # This assumes analyze() returns WriteFileOp with correct content.
        if isinstance(op, WriteFileOp):
            tm.add_write(op.path, op.content)

    tm.commit()

    # 5. Verification Phase
    # Check the file where the definition was
    modified_core_code = core_path.read_text(encoding="utf-8")
    assert "class NewHelper:" in modified_core_code
    assert "class OldHelper:" not in modified_core_code

    # Check the file where it was used
    modified_app_code = app_path.read_text(encoding="utf-8")
    assert "from .core import NewHelper, old_func" in modified_app_code
    assert "h = NewHelper()" in modified_app_code

    # Check sidecar files
    modified_doc_data = yaml.safe_load(doc_path.read_text("utf-8"))
    assert "mypkg.core.NewHelper" in modified_doc_data
    assert "mypkg.core.OldHelper" not in modified_doc_data
    assert modified_doc_data["mypkg.core.NewHelper"] == "This is the old helper."

    modified_sig_data = json.loads(sig_path.read_text("utf-8"))
    assert "mypkg.core.NewHelper" in modified_sig_data
    assert "mypkg.core.OldHelper" not in modified_sig_data
    assert (
        modified_sig_data["mypkg.core.NewHelper"]["baseline_code_structure_hash"]
        == "hash1"
    )
~~~~~
~~~~~python.new
    py_rel_path = "mypkg/core.py"
    old_helper_suri = f"py://{py_rel_path}#OldHelper"
    old_func_suri = f"py://{py_rel_path}#old_func"
    new_helper_suri = f"py://{py_rel_path}#NewHelper"

    project_root = (
        factory.with_pyproject(".")
        .with_source(
            "mypkg/core.py",
            """
        class OldHelper:
            pass

        def old_func():
            pass
        """,
        )
        .with_source(
            "mypkg/app.py",
            """
        from .core import OldHelper, old_func

        h = OldHelper()
        old_func()
        """,
        )
        .with_source("mypkg/__init__.py", "")
        .with_docs(
            "mypkg/core.stitcher.yaml",
            # Keys are Fragments
            {
                "OldHelper": "This is the old helper.",
                "old_func": "This is an old function.",
            },
        )
        .with_raw_file(
            ".stitcher/signatures/mypkg/core.json",
            # Keys are SURIs
            json.dumps(
                {
                    old_helper_suri: {"baseline_code_structure_hash": "hash1"},
                    old_func_suri: {"baseline_code_structure_hash": "hash2"},
                }
            ),
        )
        .build()
    )

    core_path = project_root / "mypkg/core.py"
    app_path = project_root / "mypkg/app.py"
    doc_path = project_root / "mypkg/core.stitcher.yaml"
    sig_path = project_root / ".stitcher/signatures/mypkg/core.json"

    # 2. Analysis Phase
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("mypkg")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )

    # 3. Planning Phase
    from stitcher.refactor.migration import MigrationSpec
    from stitcher.refactor.engine.planner import Planner

    op = RenameSymbolOperation(
        old_fqn="mypkg.core.OldHelper", new_fqn="mypkg.core.NewHelper"
    )
    spec = MigrationSpec().add(op)
    planner = Planner()
    file_ops = planner.plan(spec, ctx)

    # 4. Execution Phase
    tm = TransactionManager(project_root)
    for op in file_ops:
        # In a real app, we might add ops one by one. Here we add all.
        # This assumes analyze() returns WriteFileOp with correct content.
        if isinstance(op, WriteFileOp):
            tm.add_write(op.path, op.content)

    tm.commit()

    # 5. Verification Phase
    # Check the file where the definition was
    modified_core_code = core_path.read_text(encoding="utf-8")
    assert "class NewHelper:" in modified_core_code
    assert "class OldHelper:" not in modified_core_code

    # Check the file where it was used
    modified_app_code = app_path.read_text(encoding="utf-8")
    assert "from .core import NewHelper, old_func" in modified_app_code
    assert "h = NewHelper()" in modified_app_code

    # Check sidecar files
    modified_doc_data = yaml.safe_load(doc_path.read_text("utf-8"))
    assert "NewHelper" in modified_doc_data
    assert "OldHelper" not in modified_doc_data
    assert modified_doc_data["NewHelper"] == "This is the old helper."

    modified_sig_data = json.loads(sig_path.read_text("utf-8"))
    assert new_helper_suri in modified_sig_data
    assert old_helper_suri not in modified_sig_data
    assert (
        modified_sig_data[new_helper_suri]["baseline_code_structure_hash"]
        == "hash1"
    )
~~~~~

#### Acts 8: 更新 `test_rename_symbol_monorepo_e2e.py`

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_symbol_monorepo_e2e.py
~~~~~
~~~~~python.old
    project_root = (
        factory.with_pyproject(".")  # For top-level integration tests
        # --- Package A: Defines the symbol ---
        .with_pyproject("packages/pkg_a")
        .with_source("packages/pkg_a/src/pkga_lib/__init__.py", "")
        .with_source("packages/pkg_a/src/pkga_lib/core.py", "class OldNameClass: pass")
        .with_docs(
            "packages/pkg_a/src/pkga_lib/core.stitcher.yaml",
            {"pkga_lib.core.OldNameClass": "Docs for the old class."},
        )
        .with_raw_file(
            ".stitcher/signatures/packages/pkg_a/src/pkga_lib/core.json",
            json.dumps({"pkga_lib.core.OldNameClass": {"hash": "abc"}}),
        )
        .with_source(
            "packages/pkg_a/tests/test_core.py",
            "from pkga_lib.core import OldNameClass\n\ndef test_local():\n    assert OldNameClass is not None",
        )
        # --- Package B: Consumes the symbol ---
        .with_pyproject("packages/pkg_b")
        .with_source("packages/pkg_b/src/pkgb_app/__init__.py", "")
        .with_source(
            "packages/pkg_b/src/pkgb_app/main.py",
            "from pkga_lib.core import OldNameClass\n\ninstance = OldNameClass()",
        )
        # --- Top-level integration test: Also consumes the symbol ---
        .with_source("tests/integration/__init__.py", "")
        .with_source(
            "tests/integration/test_system.py",
            "from pkga_lib.core import OldNameClass\n\ndef test_system_integration():\n    assert OldNameClass",
        )
        .build()
    )

    # Define paths for verification
    definition_path = project_root / "packages/pkg_a/src/pkga_lib/core.py"
    pkg_a_test_path = project_root / "packages/pkg_a/tests/test_core.py"
    pkg_b_main_path = project_root / "packages/pkg_b/src/pkgb_app/main.py"
    top_level_test_path = project_root / "tests/integration/test_system.py"
    doc_path = definition_path.with_suffix(".stitcher.yaml")
    sig_path = (
        project_root / ".stitcher/signatures/packages/pkg_a/src/pkga_lib/core.json"
    )

    # 2. ACT
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("pkga_lib")
    graph.load("pkgb_app")
    graph.load("test_core")
    graph.load("integration")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )

    from stitcher.refactor.migration import MigrationSpec
    from stitcher.refactor.engine.planner import Planner

    op = RenameSymbolOperation(
        "pkga_lib.core.OldNameClass", "pkga_lib.core.NewNameClass"
    )
    spec = MigrationSpec().add(op)
    planner = Planner()
    file_ops = planner.plan(spec, ctx)

    tm = TransactionManager(project_root)
    for fop in file_ops:
        if isinstance(fop, WriteFileOp):
            tm.add_write(fop.path, fop.content)
    tm.commit()

    # 3. ASSERT
    # --- Code Files ---
    expected_import = "from pkga_lib.core import NewNameClass"
    assert "class NewNameClass: pass" in definition_path.read_text()
    assert expected_import in pkg_a_test_path.read_text()
    assert expected_import in pkg_b_main_path.read_text()
    assert expected_import in top_level_test_path.read_text()

    # --- Sidecar Files ---
    new_fqn = "pkga_lib.core.NewNameClass"
    old_fqn = "pkga_lib.core.OldNameClass"

    # YAML Doc file
    doc_data = yaml.safe_load(doc_path.read_text())
    assert new_fqn in doc_data
    assert old_fqn not in doc_data
    assert doc_data[new_fqn] == "Docs for the old class."

    # JSON Signature file
    sig_data = json.loads(sig_path.read_text())
    assert new_fqn in sig_data
    assert old_fqn not in sig_data
    assert sig_data[new_fqn] == {"hash": "abc"}
~~~~~
~~~~~python.new
    py_rel_path = "packages/pkg_a/src/pkga_lib/core.py"
    old_suri = f"py://{py_rel_path}#OldNameClass"
    new_suri = f"py://{py_rel_path}#NewNameClass"

    project_root = (
        factory.with_pyproject(".")  # For top-level integration tests
        # --- Package A: Defines the symbol ---
        .with_pyproject("packages/pkg_a")
        .with_source("packages/pkg_a/src/pkga_lib/__init__.py", "")
        .with_source("packages/pkg_a/src/pkga_lib/core.py", "class OldNameClass: pass")
        .with_docs(
            "packages/pkg_a/src/pkga_lib/core.stitcher.yaml",
            # Key is Fragment
            {"OldNameClass": "Docs for the old class."},
        )
        .with_raw_file(
            ".stitcher/signatures/packages/pkg_a/src/pkga_lib/core.json",
            # Key is SURI
            json.dumps({old_suri: {"hash": "abc"}}),
        )
        .with_source(
            "packages/pkg_a/tests/test_core.py",
            "from pkga_lib.core import OldNameClass\n\ndef test_local():\n    assert OldNameClass is not None",
        )
        # --- Package B: Consumes the symbol ---
        .with_pyproject("packages/pkg_b")
        .with_source("packages/pkg_b/src/pkgb_app/__init__.py", "")
        .with_source(
            "packages/pkg_b/src/pkgb_app/main.py",
            "from pkga_lib.core import OldNameClass\n\ninstance = OldNameClass()",
        )
        # --- Top-level integration test: Also consumes the symbol ---
        .with_source("tests/integration/__init__.py", "")
        .with_source(
            "tests/integration/test_system.py",
            "from pkga_lib.core import OldNameClass\n\ndef test_system_integration():\n    assert OldNameClass",
        )
        .build()
    )

    # Define paths for verification
    definition_path = project_root / "packages/pkg_a/src/pkga_lib/core.py"
    pkg_a_test_path = project_root / "packages/pkg_a/tests/test_core.py"
    pkg_b_main_path = project_root / "packages/pkg_b/src/pkgb_app/main.py"
    top_level_test_path = project_root / "tests/integration/test_system.py"
    doc_path = definition_path.with_suffix(".stitcher.yaml")
    sig_path = (
        project_root / ".stitcher/signatures/packages/pkg_a/src/pkga_lib/core.json"
    )

    # 2. ACT
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("pkga_lib")
    graph.load("pkgb_app")
    graph.load("test_core")
    graph.load("integration")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )

    from stitcher.refactor.migration import MigrationSpec
    from stitcher.refactor.engine.planner import Planner

    op = RenameSymbolOperation(
        "pkga_lib.core.OldNameClass", "pkga_lib.core.NewNameClass"
    )
    spec = MigrationSpec().add(op)
    planner = Planner()
    file_ops = planner.plan(spec, ctx)

    tm = TransactionManager(project_root)
    for fop in file_ops:
        if isinstance(fop, WriteFileOp):
            tm.add_write(fop.path, fop.content)
    tm.commit()

    # 3. ASSERT
    # --- Code Files ---
    expected_import = "from pkga_lib.core import NewNameClass"
    assert "class NewNameClass: pass" in definition_path.read_text()
    assert expected_import in pkg_a_test_path.read_text()
    assert expected_import in pkg_b_main_path.read_text()
    assert expected_import in top_level_test_path.read_text()

    # --- Sidecar Files ---
    # YAML Doc file (key is Fragment)
    doc_data = yaml.safe_load(doc_path.read_text())
    assert "NewNameClass" in doc_data
    assert "OldNameClass" not in doc_data
    assert doc_data["NewNameClass"] == "Docs for the old class."

    # JSON Signature file (key is SURI)
    sig_data = json.loads(sig_path.read_text())
    assert new_suri in sig_data
    assert old_suri not in sig_data
    assert sig_data[new_suri] == {"hash": "abc"}
~~~~~

### 下一步建议

我们已经成功地将测试数据与新的标识符本体论对齐。这是“大清洗”的第一步，也是最关键的一步。

下一步，我们将进入核心逻辑的改造，即**第二步：重写 Adapter**。具体任务是修改 `SidecarAdapter`，使其在解析 `.stitcher.yaml` 文件时：
1.  不再生成 `kind="yaml_fqn"` 的引用。
2.  而是根据 YAML 文件的物理路径，实时计算出其所描述的 Python 符号的 SURI。
3.  生成一个 `kind="yaml_suri"` (或类似的强类型) 的引用，其 `target_id` 直接就是计算出的 SURI。

这将彻底斩断系统对 FQN 的依赖，为后续 `Planner` 的重构奠定基础。如果您同意，我将开始制定执行此任务的计划。
