简要回答
这是一个 **Needle Runtime (FS Loader)** 的逻辑缺陷，而非 JSON 文件的位置问题。

问题根源在于 `FileSystemLoader` 目前通过 `os.walk` 扫描目录时，简单粗暴地将所有 JSON 文件的内容合并到了顶层，**丢失了文件路径所隐含的命名空间信息**（即 FQN 前缀）。

例如，文件 `needle/en/check/file.json` 中的 `fail` 键，本应被加载为 `check.file.fail`，但实际上被加载为了 `fail`，导致 `stitcher_nexus` 无法通过全限定名找到它。

无需移动文件，我将修复 `FileSystemLoader` 的扫描逻辑，使其根据文件的相对路径自动合成正确的 FQN 前缀。

## [WIP] fix(runtime): 修复 FileSystemLoader 缺失 FQN 路径合成逻辑的问题

### 用户需求
修复 `stitcher` CLI 输出中显示原始键（如 `cli.app.description`）而非本地化字符串的问题。

### 评论
这是一个典型的“实现与规范脱节”的问题。Needle SST v2 规范明确要求加载器负责利用物理路径合成 FQN（例如 `cli/app.json` -> `cli.app.*`），但当前代码仅实现了简单的扁平化合并。修复此问题将恢复 CLI 的多语言能力。

### 目标
1.  修改 `pyneedle-runtime` 中的 `FileSystemLoader`。
2.  在扫描目录时，根据文件相对于资源根目录的路径计算 FQN 前缀。
3.  特别处理 `__init__.json`，将其从前缀路径中移除（遵循 Python 包语义）。
4.  将前缀应用到加载的所有键上，确保 `check/file.json` 中的 `fail` 键正确映射为 `check.file.fail`。

### 基本原理
通过在加载层动态合成 FQN，我们保持了物理存储的整洁（开发者不需要在每个 JSON 文件里重复写 `check.file` 前缀），同时保证了运行时内存视图的正确性。这完全符合 SST v2 架构设计。

### 标签
#intent/fix #flow/ready #priority/high #comp/runtime #concept/loader #scope/core #ai/instruct #task/domain/runtime #task/object/fs-loader #task/action/fix #task/state/begin

---

### Script

#### Acts 1: 修复 FileSystemLoader 的 FQN 合成逻辑

我们将重写 `_scan_directory_to_dict` 方法（以及未使用的 `_scan_directory` 方法以保持一致性），加入路径前缀计算逻辑。

~~~~~act
patch_file
packages/pyneedle-runtime/src/needle/loaders/fs_loader.py
~~~~~
~~~~~python.old
    def _scan_directory_to_dict(self, root_path: Path) -> Dict[str, str]:
        """Scans a directory and merges all found files into a single dictionary."""
        data: Dict[str, str] = {}
        for dirpath, _, filenames in os.walk(root_path):
            for filename in sorted(filenames):
                file_path = Path(dirpath) / filename
                for handler in self.handlers:
                    if handler.match(file_path):
                        content = handler.load(file_path)
                        str_content = {str(k): str(v) for k, v in content.items()}
                        data.update(str_content)
                        break
        return data

    def _scan_directory(self, root_path: Path) -> List[Tuple[Path, Dict[str, str]]]:
        """
        Scans a directory for supported files.
        Returns a list of layers. 
        Note: The order of files within a directory is OS-dependent, 
        but we process them deterministically if needed.
        """
        layers = []
        # We walk top-down.
        for dirpath, _, filenames in os.walk(root_path):
            # Sort filenames to ensure deterministic loading order
            for filename in sorted(filenames):
                file_path = Path(dirpath) / filename
                for handler in self.handlers:
                    if handler.match(file_path):
                        # Handler is responsible for flattening
                        content = handler.load(file_path)
                        # Ensure content is strictly Dict[str, str]
                        str_content = {str(k): str(v) for k, v in content.items()}
                        layers.append((file_path, str_content))
                        break # Only use the first matching handler per file
        return layers
~~~~~
~~~~~python.new
    def _scan_directory_to_dict(self, root_path: Path) -> Dict[str, str]:
        """Scans a directory and merges all found files into a single dictionary."""
        data: Dict[str, str] = {}
        for dirpath, _, filenames in os.walk(root_path):
            for filename in sorted(filenames):
                file_path = Path(dirpath) / filename
                for handler in self.handlers:
                    if handler.match(file_path):
                        content = handler.load(file_path)
                        prefix = self._calculate_prefix(file_path, root_path)

                        for k, v in content.items():
                            str_k = str(k)
                            full_key = f"{prefix}.{str_k}" if prefix else str_k
                            data[full_key] = str(v)
                        break
        return data

    def _scan_directory(self, root_path: Path) -> List[Tuple[Path, Dict[str, str]]]:
        """
        Scans a directory for supported files.
        Returns a list of layers.
        Note: The order of files within a directory is OS-dependent,
        but we process them deterministically if needed.
        """
        layers = []
        # We walk top-down.
        for dirpath, _, filenames in os.walk(root_path):
            # Sort filenames to ensure deterministic loading order
            for filename in sorted(filenames):
                file_path = Path(dirpath) / filename
                for handler in self.handlers:
                    if handler.match(file_path):
                        # Handler is responsible for flattening
                        content = handler.load(file_path)
                        prefix = self._calculate_prefix(file_path, root_path)

                        # Ensure content is strictly Dict[str, str] and prepend prefix
                        str_content = {}
                        for k, v in content.items():
                            str_k = str(k)
                            full_key = f"{prefix}.{str_k}" if prefix else str_k
                            str_content[full_key] = str(v)

                        layers.append((file_path, str_content))
                        break  # Only use the first matching handler per file
        return layers

    def _calculate_prefix(self, file_path: Path, root_path: Path) -> str:
        rel_path = file_path.relative_to(root_path)
        # Remove suffix (e.g. .json)
        parts = list(rel_path.with_suffix("").parts)
        # Handle __init__ convention: remove it from prefix
        if parts and parts[-1] == "__init__":
            parts.pop()
        return ".".join(parts)
~~~~~

### 下一步建议

由于 `stitcher` CLI 已经包含了自己的资源（在 `stitcher-cli` 和 `stitcher-common` 中），修复加载逻辑后，直接运行 `stitcher --help` 或 `stitcher check` 应该就能看到正确的文本输出。

你可以通过运行以下命令验证修复效果：
1.  `stitcher --help` (应显示 "验证代码结构与文档的一致性。" 而不是 `cli.command.check.help`)
2.  `stitcher check` (错误信息应显示具体描述)
