#!/usr/bin/env bash
# Deploy the web service on gmt (docs/DEPLOY.md). After Chatbot's scripts/deploy.sh.
#   scripts/deploy.sh staging BRANCH     # staging: run origin/BRANCH in /srv/pdf-to-doc-staging, then the smoke test
#   scripts/deploy.sh staging --stop     # stop staging
#   scripts/deploy.sh                    # production: fast-forward /srv/pdf-to-doc to the checked origin/main, (re)build
#   scripts/deploy.sh check A B          # only print whether commits A and B differ in files the server uses
#   BRANCH=x scripts/deploy.sh           # production deploys origin/x instead of origin/main
# A production deploy first checks that the files the server uses are what staging last ran and
# passed its smoke test with. DEPLOY_WITHOUT_STAGING=1 skips that check: for hotfixes and rollbacks only.
# Commit and push first: only what is on origin reaches the server (gmt pulls with a read-only deploy key).
# .env exists only on the server and is never touched here.
set -euo pipefail
HOST="${HOST:-gmt}"
PRODUCTION_DIR=/srv/pdf-to-doc
STAGING_DIR=/srv/pdf-to-doc-staging
STAGING_SITE=https://pdf-staging.tail46a117.ts.net
cd "$(dirname "$0")/.."

usage() { sed -n '2,7p' scripts/deploy.sh | sed 's/^# \{0,1\}//'; exit 2; }

# Paths the server never uses, so changing them needs no staging round. Every other path counts,
# new ones included. scripts: run from a developer's machine, or once by hand on gmt.
SERVER_UNUSED=(':(exclude)docs' ':(exclude).scratch' ':(exclude).claude' ':(exclude).impeccable' ':(exclude).github'
               ':(exclude)tests' ':(exclude)corpus' ':(exclude)scripts' ':(exclude,glob)*.md')

server_diff() {  # the files the server uses that differ between commits $1 and $2
  git -c core.quotepath=false diff --name-only "$1" "$2" -- . "${SERVER_UNUSED[@]}"
}

check() {  # check A B: print whether the files the server uses differ; exit 1 when they do. Changes nothing.
  local a b files
  a=$(git rev-parse -q --verify "$1^{commit}") || { echo "unknown commit: $1"; exit 2; }
  b=$(git rev-parse -q --verify "$2^{commit}") || { echo "unknown commit: $2"; exit 2; }
  files=$(server_diff "$a" "$b")
  if [ -z "$files" ]; then
    echo "same: no file the server uses differs between $1 and $2"
  else
    echo "differ: files the server uses that differ between $1 and $2:"; sed 's/^/  /' <<<"$files"; exit 1
  fi
}

staging_check() {  # refuse (exit 1) unless commit $1 has the same server-used files as staging's last passed run
  local staged files
  # Read-only on gmt. The remote side always succeeds ("none" when there is no record), so a failure is ssh's.
  staged=$(ssh -n "$HOST" "git -C $STAGING_DIR rev-parse -q --verify refs/staging/passed || echo none") || {
    echo "refusing: cannot read staging's record on $HOST (ssh failed)"; exit 1; }
  if [ "$staged" = none ]; then
    echo "refusing: staging has no record of a passed smoke test; run scripts/deploy.sh staging BRANCH first"; exit 1
  fi
  [[ "$staged" =~ ^[0-9a-f]{40}$ ]] || { echo "refusing: unexpected reply from $HOST: $staged"; exit 1; }
  git cat-file -e "$staged^{commit}" 2>/dev/null || git fetch -q origin "$staged" 2>/dev/null || {
    echo "refusing: staging last passed with $staged, which cannot be fetched from origin"; exit 1; }
  files=$(server_diff "$staged" "$1")
  if [ -n "$files" ]; then
    echo "refusing: files the server uses differ from what staging last passed with ($(git rev-parse --short "$staged")):"
    sed 's/^/  /' <<<"$files"
    echo "deploy this commit to staging first; for a hotfix or rollback only: DEPLOY_WITHOUT_STAGING=1 scripts/deploy.sh"
    exit 1
  fi
  echo "staging check passed: staging last passed with $(git rev-parse --short "$staged") and the same server files"
}

local_checks() {  # $1 = branch about to be deployed
  # ssh hands its arguments to gmt's shell, so only plain branch names may travel there.
  [[ "$1" =~ ^[A-Za-z0-9._/-]+$ && "$1" != -* ]] || { echo "refusing branch name '$1': use letters, digits, . _ / -"; exit 2; }
  [ -z "$(git status --porcelain)" ] || echo "warning: uncommitted changes on this machine will not be deployed"
  git fetch -q origin
  if git rev-parse -q --verify "$1" >/dev/null && git rev-parse -q --verify "origin/$1" >/dev/null; then
    [ "$(git rev-parse "$1")" = "$(git rev-parse "origin/$1")" ] || echo "warning: local $1 differs from origin/$1; push first"
  fi
}

production() {
  local branch="${BRANCH:-main}" target
  local_checks "$branch"
  target=$(git rev-parse -q --verify "origin/$branch^{commit}") || { echo "origin/$branch not found"; exit 2; }
  if [ "${DEPLOY_WITHOUT_STAGING:-}" = 1 ]; then
    echo "WARNING: DEPLOY_WITHOUT_STAGING=1: deploying $(git rev-parse --short "$target") to production WITHOUT the staging check"
  else
    staging_check "$target"
  fi
  # gmt merges exactly the commit checked here, even if origin/$branch moves on in the meantime.
  ssh "$HOST" bash -s -- "$PRODUCTION_DIR" "$branch" "$target" <<'REMOTE'
set -euo pipefail
cd "$1"; BRANCH="$2"; TARGET="$3"
# Every compose command names the project, so a mistake here can never reach staging or Chatbot.
dc() { BUILD_COMMIT="$TARGET" docker compose -p pdf-to-doc -f compose.yaml "$@" </dev/null; }
git fetch -q origin "$BRANCH"
git merge -q --ff-only "$TARGET"
git log --oneline -1
dc build
# Running conversions are cancelled as the launcher stops; their visitors see that they ended.
dc up -d --remove-orphans
for i in $(seq 60); do
  dc exec -T web python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5)" \
    >/dev/null 2>&1 && break
  [ "$i" -lt 60 ] || { echo "the web app did not answer /health within a minute"; dc ps; exit 1; }
  sleep 1
done
dc ps
echo "production runs $(git rev-parse --short HEAD)"
REMOTE
}

staging_deploy() {
  local branch="$1" commit
  local_checks "$branch"
  commit=$(ssh "$HOST" bash -s -- "$STAGING_DIR" "$branch" <<'REMOTE'
set -euo pipefail
cd "$1"; BRANCH="$2"
# Every compose command names the staging project and its files, so a mistake can never reach production.
# The record of a passed smoke test (git ref refs/staging/passed) is cleared first, so that a deploy
# that fails anywhere leaves none.
git update-ref -d refs/staging/passed
git fetch -q origin "+refs/heads/$BRANCH:refs/remotes/origin/$BRANCH"
# -f discards any change to tracked files; ignored files such as .env stay. Nobody edits this checkout.
git checkout -q -f --detach "origin/$BRANCH"
COMMIT=$(git rev-parse HEAD)
dc() { BUILD_COMMIT="$COMMIT" docker compose -p pdf-to-doc-staging -f compose.yaml -f compose.staging.yaml "$@" </dev/null; }
# Refuse anything that could meet production: every container named for staging, and no port published.
cfg=$(dc config 2>/dev/null) || { echo "docker compose config failed in $1" >&2; exit 1; }
names=$(sed -n 's/^ *container_name: //p' <<<"$cfg")
if [ "$(wc -l <<<"$names")" -ne 3 ] || grep -qv '^staging-' <<<"$names" || grep -q '^ *published:' <<<"$cfg"; then
  echo "refusing: staging's containers must all be named staging-* and publish no port" >&2; exit 1
fi
dc build >&2
# Recreated each time, so that the web app's counts in memory, the daily allowance among them, start empty.
dc up -d --force-recreate --remove-orphans >&2
for i in $(seq 60); do
  dc exec -T web python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5)" \
    >/dev/null 2>&1 && break
  [ "$i" -lt 60 ] || { echo "the web app did not answer /health within a minute" >&2; dc ps >&2; exit 1; }
  sleep 1
done
dc ps >&2
echo "$COMMIT"
REMOTE
)
  echo "staging runs $branch at ${commit:0:7}; running the smoke test through $STAGING_SITE..."
  uv run python scripts/smoke_test.py "$STAGING_SITE" --commit "$commit" --ssh "$HOST" --environment staging
  # Recorded only now, and only for the commit the smoke test passed with.
  ssh -n "$HOST" "git -C $STAGING_DIR update-ref refs/staging/passed $commit"
  echo "staging passed its smoke test at ${commit:0:7}; production may deploy the same server files"
}

staging_stop() {
  ssh "$HOST" bash -s -- "$STAGING_DIR" <<'REMOTE'
set -euo pipefail
cd "$1"
dc() { BUILD_COMMIT=unused docker compose -p pdf-to-doc-staging -f compose.yaml -f compose.staging.yaml "$@" </dev/null; }
dc stop
dc ps -a
REMOTE
}

case "${1:-}" in
  "") production ;;
  check) [ $# -eq 3 ] || usage; check "$2" "$3" ;;
  staging)
    case "${2:-}" in
      --stop) staging_stop ;;
      ""|-*) usage ;;
      *) staging_deploy "$2" ;;
    esac ;;
  *) usage ;;
esac
