# Competition experiment ledger

Every official submission gets one immutable JSON record under `submissions/`. The
record ties a Kaggle submission ID and notebook version to the exact source, notebook
hash, profile, model, and score. Status and scores may be filled in when Kaggle finishes;
the identity and provenance fields must never be rewritten.

Public-game comparisons use the fixed game set embedded in the generated notebook and
must keep model, seed, budgets, runtime, and hardware equal. Promote a candidate only
after the paired report shows a score gain or a material efficiency gain without score
loss.
