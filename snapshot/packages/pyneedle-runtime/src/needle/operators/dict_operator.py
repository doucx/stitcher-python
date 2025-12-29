from typing import Any, Dict, Union
from needle.spec import OperatorProtocol, SemanticPointerProtocol


class DictOperator(OperatorProtocol):
    """
    A Config Operator that provides values from an in-memory dictionary.
    """

    def __init__(self, data: Dict[str, Any]):
        self._data = data

    def __call__(self, key: Union[str, SemanticPointerProtocol]) -> Any:
        return self._data.get(str(key))