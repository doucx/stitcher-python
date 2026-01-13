from typing import Dict, Any
from ruamel.yaml import YAML
import json
from io import StringIO


class SidecarUpdater:
    def update_keys(
        self, content: str, rename_map: Dict[str, str], is_yaml: bool
    ) -> str:
        """
        Loads a sidecar file (YAML or JSON), renames top-level keys
        according to the rename_map, and returns the updated content.
        """
        if is_yaml:
            return self._update_yaml_keys(content, rename_map)
        else:
            return self._update_json_keys(content, rename_map)

    def _update_yaml_keys(self, content: str, rename_map: Dict[str, str]) -> str:
        parser = YAML()
        data = parser.load(content)
        if not isinstance(data, dict):
            return content

        new_data = {rename_map.get(k, k): v for k, v in data.items()}

        string_stream = StringIO()
        parser.dump(new_data, string_stream)
        return string_stream.getvalue()

    def _update_json_keys(self, content: str, rename_map: Dict[str, str]) -> str:
        try:
            data = json.loads(content)
            if not isinstance(data, dict):
                return content
        except json.JSONDecodeError:
            return content

        new_data = {rename_map.get(k, k): v for k, v in data.items()}
        return json.dumps(new_data, indent=2, sort_keys=True)