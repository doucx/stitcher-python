from typing import Dict, Any
from needle.spec import ResourceLoaderProtocol


class MemoryLoader(ResourceLoaderProtocol):
    """
    A resource loader that sources data from an in-memory dictionary.

    Ideal for testing, dynamic configuration, or runtime overrides.
    """

    def __init__(self, data: Dict[str, Dict[str, Any]]):
        """
        Initializes the loader with data.

        Args:
            data: A dictionary where keys are language codes and values are
                  dictionaries of FQN -> value.
                  e.g., {"en": {"app.title": "My App"}}
        """
        self._data = data

    def load(self, lang: str) -> Dict[str, Any]:
        """
        Loads resources for a specific language from memory.
        """
        # Return a copy to simulate I/O snapshotting and prevent
        # ChainMap from reflecting dynamic changes in source data immediately.
        return self._data.get(lang, {}).copy()