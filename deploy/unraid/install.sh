#!/bin/bash
set -euo pipefail

# Installation Observia sur Unraid via SSH
# Exécuter depuis le dossier du projet cloné sur le NAS

INSTALL_DIR="${INSTALL_DIR:-/mnt/user/appdata/observia}"
REPO_URL="${REPO_URL:-https://github.com/Nixoc44/observia-tool.git}"
BRANCH="${BRANCH:-cursor/vercel-deploy-08f9}"

echo "==> Dossier d'installation: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR/data"

if [ ! -d "$INSTALL_DIR/repo/.git" ]; then
  echo "==> Clonage du dépôt..."
  git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$INSTALL_DIR/repo"
else
  echo "==> Mise à jour du dépôt..."
  git -C "$INSTALL_DIR/repo" fetch origin "$BRANCH"
  git -C "$INSTALL_DIR/repo" checkout "$BRANCH"
  git -C "$INSTALL_DIR/repo" pull origin "$BRANCH"
fi

if [ ! -f "$INSTALL_DIR/.env" ]; then
  echo "==> Création du fichier .env"
  cp "$INSTALL_DIR/repo/deploy/unraid/.env.example" "$INSTALL_DIR/.env"
  SECRET=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p)
  sed -i "s/remplace-par-une-cle-secrete-longue-et-aleatoire/$SECRET/" "$INSTALL_DIR/.env"
  echo "    SECRET_KEY généré automatiquement dans $INSTALL_DIR/.env"
fi

cd "$INSTALL_DIR/repo"
export $(grep -v '^#' "$INSTALL_DIR/.env" | xargs)

echo "==> Build et démarrage des conteneurs..."
docker compose -f docker-compose.unraid.yml up -d --build

IP=$(hostname -I 2>/dev/null | awk '{print $1}')
PORT="${OBSERVIA_PORT:-3080}"
echo ""
echo "✅ Observia démarré"
echo "   URL: http://${IP:-192.168.1.101}:${PORT}"
echo "   Données persistantes: $INSTALL_DIR/data"
