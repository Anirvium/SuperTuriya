# Reviewer-only external-v2 gold

The independent author places one `v2-NNN.json` gold file here for each visible
case. This directory is used only for validation, scoring, and adjudication. It
must not be mounted or copied into the model runtime.

Each label requires a unique `V2_GOLD_CANARY_*` marker. The raw-prediction
artifact is rejected during scoring if any private marker appears in it.

Do not commit genuine private gold to a public submission repository. Supply it
to the benchmark reviewer through a separate permitted channel and retain only
its frozen hashes in public evidence when confidentiality is required.
