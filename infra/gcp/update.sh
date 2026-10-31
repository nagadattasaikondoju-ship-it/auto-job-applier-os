#!/usr/bin/env bash
# Redeploy when the deploy branch has new commits. Run every 5 minutes by /etc/cron.d/applyon-update.
set -euo pipefail

APP_DIR=/opt/applyon
BRANCH="${BRANCH:-main}"
LOCK=/var/lock/applyon-update.lock

exec 9>"$LOCK"
flock -n 9 || exit 0  # a build is already running

git -C "$APP_DIR" fetch --quiet origin "$BRANCH"
if [ "$(git -C "$APP_DIR" rev-parse HEAD)" = "$(git -C "$APP_DIR" rev-parse "origin/$BRANCH")" ]; then
  exit 0
fi

echo "$(date -u +%FT%TZ) deploying $(git -C "$APP_DIR" rev-parse --short "origin/$BRANCH")"
git -C "$APP_DIR" reset --quiet --hard "origin/$BRANCH"
cd "$APP_DIR/infra/gcp"
docker compose up -d --build --remove-orphans
docker image prune -f >/dev/null
echo "$(date -u +%FT%TZ) done"
