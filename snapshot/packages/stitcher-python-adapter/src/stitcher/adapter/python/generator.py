from stitcher.spec import ModuleDef
from stitcher.io import StubGenerator

class PythonStubGenerator:
    def __init__(self):
        self._delegate = StubGenerator()

    def generate(self, module: ModuleDef) -> str:
        return self._delegate.generate(module)