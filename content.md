#### Acts 1: 标准化消息定义文件中的键

我们将重写 `state.json` 文件，将所有短命名键替换为它们对应的完整 FQN。这会直接修复之前测试中 `L.check.issue.extra` 无法找到对应消息的问题。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/check/state.json
~~~~~
~~~~~json
{
  "check.state.relinked": "Re-linked signature for '{key}' in {path}",
  "check.state.reconciled": "Reconciled changes for '{key}' in {path}",
  "check.state.auto_reconciled": "Automatically updated {count} documentation hash(es) in {path}",
  "check.issue.extra": "Extra Doc: '{key}' is in docs but not in code.",
  "check.state.signature_drift": "Signature Drift: '{key}' code changed, docs may be stale.",
  "check.state.co_evolution": "Co-evolution: '{key}' both code and docs changed; intent unclear.",
  "check.state.doc_updated": "Doc Updated: '{key}' documentation was improved.",
  "check.state.untracked_code": "Untracked Code: '{key}' new public API without documentation."
}
~~~~~
