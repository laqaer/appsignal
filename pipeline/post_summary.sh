#!/usr/bin/env bash
# Post one operating summary per UTC day. Exit 1 when the refresh or snapshot is unhealthy.
set -euo pipefail
if [[ "${GITHUB_ACTIONS:-}" != "true" ]]; then
  echo "Skipping issue post outside GitHub Actions."
  exit 0
fi
cd "$(dirname "$0")/.."
DAY=$(date -u +%F)
TITLE="AppSignal daily operating summary"
RESULT=$(mktemp)
RUNF=$(mktemp)
gh run list --workflow refresh.yml --limit 1 --json conclusion,status,createdAt > "$RUNF"
NUM=$(gh issue list --state open --limit 50 --json number,title \
  --jq ".[] | select(.title==\"${TITLE}\") | .number" | head -n 1 || true)
ALREADY=()
if [[ -n "${NUM}" ]]; then
  BODY=$(gh issue view "$NUM" --json body,comments --jq "[.body] + [.comments[].body] | join(\"\n\")")
  if grep -F "<!-- appsignal-summary:${DAY} -->" <<< "$BODY" >/dev/null; then
    ALREADY=(--already)
  fi
fi
python3 pipeline/summary.py --decide --day "$DAY" --event "${GITHUB_EVENT_NAME}" \
  "${ALREADY[@]}" --refresh-json "$RUNF" > "$RESULT"
POST=$(python3 -c 'import json,sys; print("yes" if json.load(open(sys.argv[1]))["post"] else "no")' "$RESULT")
UNHEALTHY=$(python3 -c 'import json,sys; print("yes" if json.load(open(sys.argv[1]))["unhealthy"] else "no")' "$RESULT")
if [[ "$POST" == "yes" ]]; then
  python3 -c 'import json,sys; open(sys.argv[2],"w",encoding="utf-8").write(json.load(open(sys.argv[1]))["body"])' "$RESULT" "$RESULT.body"
  if [[ -n "${NUM}" ]]; then
    gh issue comment "$NUM" --body-file "$RESULT.body"
  else
    gh issue create --title "$TITLE" --body-file "$RESULT.body"
  fi
fi
if [[ "$UNHEALTHY" == "yes" ]]; then
  echo "Operating summary is unhealthy."
  python3 -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1]))["reasons"]))' "$RESULT"
  exit 1
fi
echo "Operating summary ok (post=${POST})."
