from stitcher.spec import ModuleDef, DocstringRendererProtocol
from .internal.stub_generator import StubGenerator


class PythonStubGenerator:
    def __init__(self):
        self._delegate = StubGenerator()

    def set_renderer(self, renderer: DocstringRendererProtocol) -> None:
        self._delegate.set_renderer(renderer)

    def generate(self, module: ModuleDef) -> str:
        return self._delegate.generate(module)
