---
name: dependency-maintenance
description: Review GitHub Actions version updates without changing the data pipeline or publishing authority.
---

# Dependency maintenance

Inspect the exact base/head and workflow diff. The current static site and Python
pipeline have no package manifest; this policy covers GitHub Actions only. Do not
add a package manager or dependencies to manufacture npm/pip coverage.

For an Actions update, verify the upstream repository, release notes, runtime
requirements, input/output changes and token permissions. Minor/patch grouping is
not a safety approval. Major updates remain individual PRs requiring explicit
acceptance. Security fixes take priority over the routine weekly schedule.

Do not invoke scheduled refresh, mutate the committed data/database, trigger Pages
publication, add secrets, widen token permissions, or use privileged
pull_request_target execution to validate an updater PR. Keep refresh/publication
separate from review. Record missing PR checks rather than claiming CI is green.

YAML alone does not enable security alerts/updates. Report settings as observed or
unverified. Return exact-head evidence, compatibility risks, rollback and an
accept/repair recommendation. No merge or deployment authority is granted.
