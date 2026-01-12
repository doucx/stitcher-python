import difflib


class Differ:
    def generate_text_diff(
        self, a: str, b: str, label_a: str = "old", label_b: str = "new"
    ) -> str:
        return "\n".join(
            difflib.unified_diff(
                a.splitlines(),
                b.splitlines(),
                fromfile=label_a,
                tofile=label_b,
                lineterm="",
            )
        )
