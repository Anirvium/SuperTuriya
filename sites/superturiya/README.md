# SuperTuriya public website

A buildless product website and browser-local, recorded synthetic playground.

- `dist/index.html`: product introduction
- `dist/demo/index.html`: interactive playground
- `dist/docs/index.html`: field guide and privacy
- `dist/assets/demo-data.json`: synthetic Python-engine records with content hash
- `dist/assets/workbench.js`: recorded playground or local Python operator adapter
- `.openai/hosting.json`: Site identity and static deployment configuration

The public site has no operator credentials, writable backend, model API calls,
analytics scripts, customer uploads, or persistent user records. Activation is
simulated in tab memory. The Python reference implementation is maintained in
https://github.com/Anirvium/SuperTuriya/tree/launch/cosmic-workbench-2026-11-21.

Preview using a static server from `dist`. Serve the operator mode through the
Python runtime in the parent project. Do not expose the operator API as a public
demo. Use the parent project's export, synchronization, validation, and visual-QA
scripts to update the evidence and shared workbench.
