#!/usr/bin/env bash
# One-time setup of the Applyon backend on a fresh Google Compute Engine VM (Ubuntu or Debian).
#
#   curl -fsSL https://raw.githubusercontent.com/nagadattasaikondoju-ship-it/auto-job-applier-os/main/infra/gcp/setup.sh | sudo bash
#
# Installs Docker, clones the repo to /opt/applyon, asks for the secrets once (stored in
# /opt/applyon/infra/gcp/.env, readable by root only), starts the API, worker, Redis and HTTPS, and
# installs a 5-minute job that redeploys whenever main changes. Safe to run again: it keeps .env.
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/nagadattasaikondoju-ship-it/auto-job-applier-os.git}"
BRANCH="${BRANCH:-main}"
APP_DIR=/opt/applyon
DEPLOY_DIR="$APP_DIR/infra/gcp"
ENV_FILE="$DEPLOY_DIR/.env"

say() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }

if [ "$(id -u)" -ne 0 ]; then
  echo "Run with sudo: curl -fsSL <this script's URL> | sudo bash" >&2
  exit 1
fi

say "Adding 2 GB of swap (headroom for image builds and Chromium)"
if ! swapon --show | grep -q /swapfile; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile >/dev/null
  swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

say "Installing Docker and git"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi
command -v git >/dev/null 2>&1 || (apt-get update -y && apt-get install -y git)
systemctl enable --now docker

say "Getting the code"
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" fetch --quiet origin "$BRANCH"
  git -C "$APP_DIR" checkout --quiet "$BRANCH"
  git -C "$APP_DIR" reset --quiet --hard "origin/$BRANCH"
else
  git clone --quiet --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

if [ ! -f "$ENV_FILE" ]; then
  say "Settings (asked once; saved to $ENV_FILE)"
  ask() {  # ask VAR "Question" [default] [secret]
    local var=$1 question=$2 default=${3:-} secret=${4:-} answer
    if [ -n "$secret" ]; then
      read -rsp "$question: " answer </dev/tty; echo
    else
      read -rp "$question${default:+ [$default]}: " answer </dev/tty
    fi
    printf -v "$var" '%s' "${answer:-$default}"
  }
  ask DATABASE_URL "Neon connection string (postgresql://...)" "" secret
  ask GEMINI_API_KEY "Gemini API key" "" secret
  ask JSEARCH_API_KEY "OpenWebNinja (JSearch) API key, or Enter to skip" "" secret
  ask FIREBASE_PROJECT_ID "Firebase project ID" "applyon-dc680"
  ask FRONTEND_URL "Website URL" "https://applyon-rho.vercel.app"

  # Default API address: <external-ip>.sslip.io, a free hostname that resolves to this VM, so Caddy
  # can get an HTTPS certificate without buying a domain. Point your own domain here later if you like.
  EXTERNAL_IP=$(curl -fsS -H 'Metadata-Flavor: Google' \
    http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip || true)
  DEFAULT_DOMAIN=""
  [ -n "$EXTERNAL_IP" ] && DEFAULT_DOMAIN="${EXTERNAL_IP//./-}.sslip.io"
  ask API_DOMAIN "API domain name" "$DEFAULT_DOMAIN"
  if [ -z "$API_DOMAIN" ]; then
    echo "An API domain is required (couldn't read this VM's external IP)." >&2
    exit 1
  fi

  # Migrations need a direct connection: Neon's pooled host ("ep-x-pooler.…") runs in transaction
  # mode, which breaks the prepared statements they use. The direct host is the same name without -pooler.
  DIRECT_DATABASE_URL="${DATABASE_URL/-pooler./.}"

  umask 077
  # Single quotes: Docker Compose then uses the values literally (no $ interpolation)
  cat > "$ENV_FILE" <<ENV
APP_ENV='production'
API_DOMAIN='$API_DOMAIN'
API_BASE_URL='https://$API_DOMAIN'
FRONTEND_URL='$FRONTEND_URL'
CORS_ORIGINS='["$FRONTEND_URL","http://localhost:3000"]'
ALLOW_DEV_LOGIN='false'
DATABASE_URL='$DATABASE_URL'
DIRECT_DATABASE_URL='$DIRECT_DATABASE_URL'
GEMINI_API_KEY='$GEMINI_API_KEY'
JSEARCH_API_KEY='$JSEARCH_API_KEY'
FIREBASE_PROJECT_ID='$FIREBASE_PROJECT_ID'
FIELD_ENCRYPTION_KEY='$(openssl rand -base64 32)'
JWT_SECRET_KEY='$(openssl rand -hex 32)'
ENV
  chmod 600 "$ENV_FILE"
else
  say "Keeping existing settings in $ENV_FILE"
fi

say "Building and starting (the first build takes about 10 minutes)"
cd "$DEPLOY_DIR"
docker compose up -d --build

say "Installing automatic updates (every 5 minutes, from $BRANCH)"
chmod +x "$DEPLOY_DIR/update.sh"
cat > /etc/cron.d/applyon-update <<CRON
*/5 * * * * root BRANCH=$BRANCH $DEPLOY_DIR/update.sh >> /var/log/applyon-update.log 2>&1
CRON

API_DOMAIN=$(grep '^API_DOMAIN=' "$ENV_FILE" | cut -d"'" -f2)
say "Waiting for the API to answer"
for _ in $(seq 1 60); do
  if curl -fsS "https://$API_DOMAIN/health/ready" >/dev/null 2>&1; then
    curl -fsS "https://$API_DOMAIN/health/ready"; echo
    say "Done. API: https://$API_DOMAIN"
    exit 0
  fi
  sleep 10
done
echo "The API didn't answer at https://$API_DOMAIN yet. Check: cd $DEPLOY_DIR && docker compose logs --tail 50" >&2
exit 1
