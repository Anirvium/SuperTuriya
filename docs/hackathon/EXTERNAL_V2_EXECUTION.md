# External-v2 Execution and Handoff

Status: implementation complete; independent cases pending.

Claim scope: independently authored cloud-operations scenario families over one
frozen canonical simulator, not cross-domain external validity.

## Completed engineering

The external-v2 pipeline is now executable from source freeze through final
evidence manifest without changing the core SuperTuriya architecture:

```text
hash-frozen system under test
  -> independent author packet
  -> visible cases + separately returned private labels
  -> mechanical validation and independent review
  -> immutable benchmark freeze
  -> cases-only same-model predictions
  -> raw artifact persisted and hashed
  -> evaluator-only private-label scoring
  -> comparison / ablation metrics
  -> paired case-level uncertainty interval
  -> versioned evidence manifest
```

The prediction stage reads visible cases and public hash manifests only. It has
been tested with all private label files physically removed. The scoring stage
accepts only an already persisted raw artifact and rejects any output containing
a private-label canary.

## Handoff artifact

Generate the file that can be sent to an independent author:

```bash
make v2-author-packet
```

Output: `output/external_v2_author_packet.zip`.

It contains the author README, visible/private schemas, frozen failure taxonomy,
protocol, reviewer instructions, visible/private templates, and a manifest with
hashes of every other member. It contains no system prompts, repair mappings,
model outputs, credentials, existing cases, or existing labels.

## Human-only dependency

The project owner must identify:

1. an independent author for 12-16 cases; and
2. a different reviewer for the completed case/gold package.

SuperTuriya's implementer must not author those final cases, advise case-specific
answers, inspect intermediate model results, or tune the frozen system after
authoring begins.

## Final execution

```bash
make v2-validate
make v2-freeze AUTHOR_ID='<author>' REVIEWER_ID='<reviewer>'
make v2-verify
make v2-predict OUTPUT='evidence/external_validity/v2/raw_live_comparison.json'
make v2-score \
  RAW='evidence/external_validity/v2/raw_live_comparison.json' \
  OUTPUT='evidence/external_validity/v2/scored_live_comparison.json'
make v2-evidence-manifest EVIDENCE_ROOT='evidence/external_validity/v2'
```

Use a different output filename for every experiment. Evidence commands fail
closed instead of overwriting an existing artifact.
