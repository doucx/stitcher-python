import pytest
from stitcher.app.core import StitcherApp
from stitcher.spec import (
    ModuleDef,
    FunctionDef,
    ResolutionAction,
)
from stitcher.test_utils import create_test_app


@pytest.fixture
def sample_module() -> ModuleDef:
    """一个包含两个函数用于测试的模块IR。"""
    return ModuleDef(
        file_path="src/main.py",
        functions=[
            FunctionDef(name="func_a", docstring="Source Doc A"),
            FunctionDef(name="func_b", docstring="Source Doc B"),
        ],
    )


@pytest.fixture
def app(tmp_path) -> StitcherApp:
    """一个用于调用内部方法的StitcherApp实例。"""
    # 绕过完整的依赖注入，因为我们只测试一个纯逻辑方法
    class PlannerTestApp(StitcherApp):
        def __init__(self):
            # We need doc_manager to be available for flatten_module_docs
            from stitcher.app.services import DocumentManager
            self.doc_manager = DocumentManager(root_path=tmp_path)

    return PlannerTestApp()


def test_plan_for_overwrite_with_strip(app, sample_module):
    """测试场景：代码优先 (`HYDRATE_OVERWRITE`) + 请求剥离 (`--strip`)"""
    decisions = {"func_a": ResolutionAction.HYDRATE_OVERWRITE}
    plan = app._generate_execution_plan(sample_module, decisions, strip_requested=True)

    p_a = plan["func_a"]
    assert p_a.hydrate_yaml is True
    assert p_a.update_code_fingerprint is True
    assert p_a.update_doc_fingerprint is True
    assert p_a.strip_source_docstring is True


def test_plan_for_overwrite_without_strip(app, sample_module):
    """测试场景：代码优先 (`HYDRATE_OVERWRITE`) + 不请求剥离"""
    decisions = {"func_a": ResolutionAction.HYDRATE_OVERWRITE}
    plan = app._generate_execution_plan(sample_module, decisions, strip_requested=False)

    p_a = plan["func_a"]
    assert p_a.hydrate_yaml is True
    assert p_a.update_code_fingerprint is True
    assert p_a.update_doc_fingerprint is True
    assert p_a.strip_source_docstring is False


def test_plan_for_keep_existing_with_strip(app, sample_module):
    """测试场景：侧栏优先 (`HYDRATE_KEEP_EXISTING`) + 请求剥离 (`--strip`)"""
    decisions = {"func_a": ResolutionAction.HYDRATE_KEEP_EXISTING}
    plan = app._generate_execution_plan(sample_module, decisions, strip_requested=True)

    p_a = plan["func_a"]
    assert p_a.hydrate_yaml is False
    assert p_a.update_code_fingerprint is True
    assert p_a.update_doc_fingerprint is False
    assert p_a.strip_source_docstring is True


def test_plan_for_keep_existing_without_strip(app, sample_module):
    """测试场景：侧栏优先 (`HYDRATE_KEEP_EXISTING`) + 不请求剥离"""
    decisions = {"func_a": ResolutionAction.HYDRATE_KEEP_EXISTING}
    plan = app._generate_execution_plan(sample_module, decisions, strip_requested=False)

    p_a = plan["func_a"]
    assert p_a.hydrate_yaml is False
    assert p_a.update_code_fingerprint is True
    assert p_a.update_doc_fingerprint is False
    assert p_a.strip_source_docstring is False


def test_plan_for_skip(app, sample_module):
    """测试场景：用户选择跳过 (`SKIP`)"""
    decisions = {"func_a": ResolutionAction.SKIP}
    plan = app._generate_execution_plan(sample_module, decisions, strip_requested=True)

    p_a = plan["func_a"]
    assert p_a.hydrate_yaml is False
    assert p_a.update_code_fingerprint is False
    assert p_a.update_doc_fingerprint is False
    assert p_a.strip_source_docstring is False


def test_plan_for_no_conflict(app, sample_module):
    """测试场景：无冲突的函数 (在decisions中不存在)"""
    decisions = {"func_b": ResolutionAction.SKIP}  # func_a is no-conflict
    plan = app._generate_execution_plan(sample_module, decisions, strip_requested=True)

    # func_a 应该被正常处理
    p_a = plan["func_a"]
    assert p_a.hydrate_yaml is True
    assert p_a.update_code_fingerprint is True
    assert p_a.update_doc_fingerprint is True
    assert p_a.strip_source_docstring is True
    
    # func_b 应该被跳过
    p_b = plan["func_b"]
    assert p_b.hydrate_yaml is False
    assert p_b.strip_source_docstring is False