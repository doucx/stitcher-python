好的，测试通过意味着我们的代码重构是正确的。现在 `stitcher check` 报告了大量的文档不一致问题，这完全在预料之中，因为我们重命名了很多东西但还没有更新它们的文档。

## [WIP] 使代码库的文档与实现再次同步

### 错误分析
`stitcher check` 的输出非常清晰，指出了以下几类问题：
1.  **悬空文档 (Dangling Docs)**: 在 `.stitcher.yaml` 文件中存在对 `run_hydrate` 和 `run_eject` 的文档，但这些方法在代码中已经不存在了。
2.  **签名漂移 (Signature Drift)**: `run_strip` 方法的签名已经改变（增加了 `files` 参数），但其文档没有更新。
3.  **文档缺失 (Missing Docs)**: 所有新引入或重命名的符号（如 `run_pump`, `run_inject`, `PumpResult` 等）都没有对应的文档。

### 目标
1.  全面更新所有受影响的 `.stitcher.yaml` 文件。
2.  删除悬空的文档条目。
3.  为所有新的和重命名的符号添加准确的文档。
4.  更新签名已变更的方法的文档。
5.  最终目标是让 `stitcher check --non-interactive` 能够干净地通过。

### 标签
#intent/fix #flow/ready #priority/high #comp/docs #scope/core #ai/instruct #task/domain/cli #task/object/command-pump #task/action/rename-and-refactor #task/state/continue

---

### Script

#### Acts 1: 更新 `stitcher-application` 的核心文档

这是最主要的变更，涉及 `StitcherApp`、新的 `PumpResult` 数据类以及相关协议。

~~~~~act
write_file
packages/stitcher-application/src/stitcher/app/core.stitcher.yaml
~~~~~
~~~~~yaml
FileCheckResult: |-
  Data container representing the outcome of a consistency check for a single file.
FileCheckResult.auto_reconciled_count: |-
  The count of documentation improvements that were automatically reconciled.
FileCheckResult.error_count: |-
  Total number of critical issues (errors) discovered in the file.
FileCheckResult.errors: |-
  A collection of errors keyed by their category (e.g., 'conflict', 'mismatch').
FileCheckResult.infos: |-
  A collection of informational messages keyed by their category (e.g., 'doc_improvement').
FileCheckResult.is_clean: |-
  Returns True if the file has no issues and no reconciliation was performed.
FileCheckResult.path: |-
  The relative path to the source file that was inspected.
FileCheckResult.reconciled: |-
  The count of signature mismatches that were automatically updated during the check.
FileCheckResult.reconciled_count: |-
  Total number of issues that were reconciled (interactively or automatically).
FileCheckResult.warning_count: |-
  Total number of non-blocking issues (warnings) discovered in the file.
FileCheckResult.warnings: |-
  A collection of warnings keyed by their category (e.g., 'missing', 'untracked').
PumpResult: |-
  Data container for the result of a `run_pump` operation.
PumpResult.redundant_files: |-
  A list of files that now contain redundant docstrings after a successful pump.
PumpResult.success: |-
  Indicates whether the pump operation completed without unresolved conflicts.
StitcherApp: |-
  The central orchestrator for all Stitcher operations.

  This class coordinates the scanner, document manager, signature manager, and
  stub generator to execute high-level commands like check, generate, and pump.
StitcherApp.run_check: |-
  Verify the structural and content consistency between source code and external YAML documentation.

  Args:
    force_relink: If True, automatically update the signature baseline for functions that have changed.
    reconcile: If True, automatically accept both signature and doc changes.
StitcherApp.run_from_config: |-
  Execute the main stub generation workflow based on the configuration found in pyproject.toml.

  This includes scanning source files, processing plugins, and generating .pyi files.
StitcherApp.run_init: |-
  Initialize Stitcher for a project by creating the first batch of .stitcher.yaml files.

  This command scans the codebase and extracts existing docstrings to seed the documentation store.
StitcherApp.run_inject: |-
  Inject documentation from .stitcher.yaml files back into the source code as docstrings.

  This operation modifies source files in-place and is intended for "injecting" from
  the Stitcher workflow back to standard Python development.
StitcherApp.run_pump: |-
  Extract new or modified docstrings from source code and update the .stitcher.yaml files.

  Args:
    strip: If True, remove the extracted docstrings from the source code immediately.
    force: If True, overwrite existing YAML content with source content in case of conflict.
    reconcile: If True, prefer existing YAML content and ignore source content in case of conflict.
  Returns:
    A PumpResult object indicating success and listing files with now-redundant docstrings.
StitcherApp.run_strip: |-
  Remove all docstrings from the source code files defined in the configuration or a specific list of files.

  This is a destructive operation used to enforce a "pure code" style where docs live strictly in YAML.

  Args:
    files: An optional list of specific files to strip. If None, uses config.
~~~~~

~~~~~act
write_file
packages/stitcher-application/src/stitcher/app/handlers/noop_handler.stitcher.yaml
~~~~~
~~~~~yaml
"NoOpInteractionHandler": |-
  A non-interactive handler that resolves conflicts based on CLI flags.
  This preserves the original behavior for CI/CD environments.
"NoOpInteractionHandler.process_interactive_session": |-
  Processes a list of conflicts non-interactively based on the handler's configuration.
~~~~~

~~~~~act
write_file
packages/stitcher-application/src/stitcher/app/protocols.stitcher.yaml
~~~~~
~~~~~yaml
"InteractionContext": |-
  Data packet passed to the handler to request a user decision.
"InteractionContext.conflict_type": |-
  The type of conflict detected.
"InteractionContext.file_path": |-
  The relative path to the file containing the conflict.
"InteractionContext.fqn": |-
  The fully qualified name of the symbol with the conflict.
"InteractionHandler": |-
  Protocol for handling user interactions during a check.
"InteractionHandler.process_interactive_session": |-
  Processes a list of conflicts, returning a list of chosen actions.
  The length of the returned list MUST match the input list.
~~~~~

#### Acts 2: 更新 `stitcher-cli` 的文档

这里主要是更新 `main.py` 和 `handlers.py` 的文档。

~~~~~act
write_file
packages/stitcher-cli/src/stitcher/cli/main.stitcher.yaml
~~~~~
~~~~~yaml
"app": |-
  The main Typer application instance for the CLI.
"check": |-
  Verify consistency between code and docs.

  Args:
    force_relink: [Non-interactive] For 'Signature Drift' errors, forces relinking.
    reconcile: [Non-interactive] For 'Co-evolution' errors, accepts both changes.
    non_interactive: Force non-interactive mode, failing on unresolved conflicts.
"cli_renderer": |-
  The CLI-specific renderer instance used by the message bus.
"generate": |-
  Generate .pyi stubs based on pyproject.toml config.
"init": |-
  Initialize Stitcher in the current project.
"inject": |-
  Inject docstrings from .stitcher.yaml files back into code.
"pump": |-
  Extract new docstrings from source code and merge them into .stitcher.yaml.

  Args:
    strip: If True, remove docstrings from source after successful pumping.
    force: If True, overwrite YAML with source docstrings on conflict.
    reconcile: If True, keep YAML docstrings on conflict.
    non_interactive: Force non-interactive mode, failing on unresolved conflicts.
"strip": |-
  Remove docstrings from source files.
~~~~~

~~~~~act
write_file
packages/stitcher-cli/src/stitcher/cli/handlers.stitcher.yaml
~~~~~
~~~~~yaml
"TyperInteractionHandler": |-
  An interactive handler using Typer/Click for user prompts.
"TyperInteractionHandler.process_interactive_session": |-
  Processes a list of conflicts by interactively prompting the user for a resolution for each one.
~~~~~

#### Acts 3: 更新 `stitcher-spec` 的文档

最后，更新 `fingerprint.py` 和 `models.py` 的文档。

~~~~~act
write_file
packages/stitcher-spec/src/stitcher/spec/fingerprint.stitcher.yaml
~~~~~
~~~~~yaml
FINGERPRINT_KEY_PATTERN: |-
  The regular expression that all Fingerprint keys must match.
Fingerprint: |-
  A dynamic, self-validating container for symbol fingerprints.
  It enforces that all keys adhere to the strict naming axiom.
Fingerprint.from_dict: |-
  Constructs a Fingerprint from a dictionary.
  Validates all keys immediately. Any invalid key raises InvalidFingerprintKeyError.
Fingerprint.get: |-
  Gets a value for a key, validating the key's format.
Fingerprint.items: |-
  Returns an iterator over the (key, value) pairs of the fingerprint.
Fingerprint.to_dict: |-
  Returns a copy of the internal hashes.
InvalidFingerprintKeyError: |-
  Raised when a key does not conform to the Fingerprint naming axiom.
~~~~~

~~~~~act
write_file
packages/stitcher-spec/src/stitcher/spec/models.stitcher.yaml
~~~~~
~~~~~yaml
"Argument": |-
  Represents a function or method argument.
"Argument.annotation": |-
  The type annotation of the argument.
"Argument.default": |-
  The string representation of the argument's default value.
"Argument.kind": |-
  The kind of argument (e.g., positional, keyword-only).
"Argument.name": |-
  The name of the argument.
"ArgumentKind": |-
  Corresponds to inspect._ParameterKind.
"ArgumentKind.KEYWORD_ONLY": |-
  A keyword-only argument.
"ArgumentKind.POSITIONAL_ONLY": |-
  A positional-only argument.
"ArgumentKind.POSITIONAL_OR_KEYWORD": |-
  A standard positional or keyword argument.
"ArgumentKind.VAR_KEYWORD": |-
  A variable keyword argument (**kwargs).
"ArgumentKind.VAR_POSITIONAL": |-
  A variable positional argument (*args).
"Attribute": |-
  Represents a module-level or class-level variable.
"Attribute.annotation": |-
  The type annotation of the attribute.
"Attribute.docstring": |-
  The docstring associated with the attribute (e.g., via a comment).
"Attribute.name": |-
  The name of the attribute.
"Attribute.value": |-
  The string representation of the attribute's value.
"ClassDef": |-
  Represents a class definition.
"ClassDef.attributes": |-
  A list of attributes defined in the class.
"ClassDef.bases": |-
  A list of base classes.
"ClassDef.decorators": |-
  A list of decorators applied to the class.
"ClassDef.docstring": |-
  The docstring of the class.
"ClassDef.methods": |-
  A list of methods defined in the class.
"ClassDef.name": |-
  The name of the class.
"ConflictType": |-
  Enumeration of possible conflict types detected by `check`.
"ConflictType.CO_EVOLUTION": |-
  Both the code signature and the documentation content have changed.
"ConflictType.DOC_CONTENT_CONFLICT": |-
  The docstring content in the source code differs from the content in the YAML file.
"ConflictType.SIGNATURE_DRIFT": |-
  The code signature has changed, but the documentation content has not.
"FunctionDef": |-
  Represents a function or method definition.
"FunctionDef.args": |-
  A list of arguments for the function.
"FunctionDef.compute_fingerprint": |-
  Computes a stable hash of the function signature (excluding docstring).
  Includes: name, args (name, kind, annotation, default), return annotation,
  async status, and static/class flags.
"FunctionDef.decorators": |-
  A list of decorators applied to the function.
"FunctionDef.docstring": |-
  The docstring of the function.
"FunctionDef.is_async": |-
  Flag indicating if the function is async.
"FunctionDef.is_class": |-
  Flag indicating if the function is a classmethod.
"FunctionDef.is_static": |-
  Flag indicating if the function is a staticmethod.
"FunctionDef.name": |-
  The name of the function.
"FunctionDef.return_annotation": |-
  The return type annotation of the function.
"ModuleDef": |-
  Represents a parsed Python module (a single .py file).
"ModuleDef.attributes": |-
  A list of attributes defined at the module level.
"ModuleDef.classes": |-
  A list of classes defined in the module.
"ModuleDef.docstring": |-
  The docstring of the module.
"ModuleDef.dunder_all": |-
  The string representation of the __all__ variable.
"ModuleDef.file_path": |-
  The relative path to the module file.
"ModuleDef.functions": |-
  A list of functions defined at the module level.
"ModuleDef.get_undocumented_public_keys": |-
  Returns a list of public keys (FQNs) that do not have a docstring.
"ModuleDef.imports": |-
  A list of import statements found in the module.
"ModuleDef.is_documentable": |-
  Checks if the module contains any content that would warrant a doc file.
"Resolution": |-
  Represents a single, atomic resolution decision made by the user.
"Resolution.action": |-
  The action chosen by the user to resolve the conflict.
"Resolution.conflict_type": |-
  The type of conflict that was detected.
"Resolution.fqn": |-
  The fully qualified name of the symbol that has a conflict.
"ResolutionAction": |-
  Enumeration of actions a user can take to resolve a conflict.
"ResolutionAction.ABORT": |-
  Abort the entire operation.
"ResolutionAction.HYDRATE_KEEP_EXISTING": |-
  For doc content conflicts, keep the existing YAML content (YAML wins).
"ResolutionAction.HYDRATE_OVERWRITE": |-
  For doc content conflicts, overwrite the YAML with source code content (Code wins).
"ResolutionAction.RECONCILE": |-
  Accept both the new signature and new documentation as the correct baseline.
"ResolutionAction.RELINK": |-
  Accept the new signature but keep the existing (unchanged) documentation.
"ResolutionAction.SKIP": |-
  Skip resolving this conflict for now.
"ResolutionPlan": |-
  A container for a list of resolution decisions, representing the complete plan
  to be executed.
"ResolutionPlan.resolutions": |-
  The list of atomic resolution decisions.
~~~~~
