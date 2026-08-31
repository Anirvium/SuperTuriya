# Person-A Import: Mechanical Corrections

Date: 30 August 2026

The imported Person-A bundle had aggregate content SHA-256
`29cd8d18eb8282d2659848ac16cfbb4e3ff86f28f3108bddf3ca3efb477b198f`.
All 16 visible cases passed the hardened case validator unchanged. All 16
private-gold files passed the hardened gold schema, but their 37 repair
`target_id` references used configuration keys or trajectory step IDs rather
than the frozen typed-operation target identifiers.

After explicit owner authorization, the repository operator made only these
mechanical private-gold substitutions:

| Count | Operation | Imported target | Frozen target |
| ---: | --- | --- | --- |
| 8 | `retrieval.filter` | `workflow_config.retrieval_filter` | `context.region` |
| 6 | `tool_argument.constraint` | `workflow_config.quantity_constraint` | `fulfill.quantity` |
| 4 | `approval_rule.add` | `workflow_config.approval_rule` | `fulfill.approval` |
| 7 | `tool_result.validation` | `workflow_config.result_validation` | `catalog.status` |
| 6 | `route.condition` | `workflow_config.enforce_order` | `workflow.order` |
| 6 | `recovery_step.insert` | case-specific finalization step IDs | `finalizer.attach_evidence` |

Corrected 32-file aggregate content SHA-256:
`886b436b7d0e849077a861a58c912965160487f64dfd8be6bc77504b024fe74a`.

No visible case, operation, failure class, decisive invariant, critical step,
adjudication note, canary, expected state, workflow configuration, prompt,
repair mapping, verifier rule, or SUT source was changed. These corrections do
not constitute Reviewer-B semantic approval and do not authorize benchmark
freeze, prediction, or scoring.
