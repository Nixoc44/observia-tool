# Déployer Observia sur Unraid

Docker est la bonne option pour Observia (analyses MCP, tâches longues, stockage persistant). Vercel ne convient que pour une démo UI.

## Prérequis Unraid

- **Docker** activé (Settings → Docker → Enable)
- Plugin **Compose** (optionnel mais recommandé) ou accès SSH
- Ports libre : `3080` (modifiable dans `.env`)

## Option A — SSH (recommandé)

### 1. Activer SSH sur Unraid

Settings → Management Access → **Telnet / SSH** → Enable SSH → port `22`

### 2. Se connecter depuis ton PC

```bash
ssh root@192.168.1.101
```

> **Ne partagez jamais votre mot de passe root dans un chat ou à un agent IA.**

### 3. Lancer l'installation

```bash
curl -fsSL https://raw.githubusercontent.com/Nixoc44/observia-tool/cursor/vercel-deploy-08f9/deploy/unraid/install.sh -o /tmp/observia-install.sh
chmod +x /tmp/observia-install.sh
INSTALL_DIR=/mnt/user/appdata/observia /tmp/observia-install.sh
```

### 4. Ouvrir l'application

http://192.168.1.101:3080

---

## Option B — Interface Docker Unraid (sans SSH)

### 1. Copier le projet sur le NAS

Via partage réseau `\\192.168.1.101\appdata\` :

```
/mnt/user/appdata/observia/repo/   ← clone du dépôt GitHub
/mnt/user/appdata/observia/data/   ← base SQLite (créé auto)
/mnt/user/appdata/observia/.env    ← variables (voir .env.example)
```

### 2. Depuis le terminal Unraid (ou SSH)

```bash
cd /mnt/user/appdata/observia/repo
cp deploy/unraid/.env.example /mnt/user/appdata/observia/.env
# Éditer SECRET_KEY dans .env
docker compose -f docker-compose.unraid.yml --env-file /mnt/user/appdata/observia/.env up -d --build
```

---

## Variables d'environnement

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Clé de chiffrement des tokens (obligatoire) |
| `APPDATA_PATH` | Chemin persistant SQLite (défaut: `./data`) |
| `OBSERVIA_PORT` | Port web (défaut: `3080`) |

---

## Commandes utiles

```bash
cd /mnt/user/appdata/observia/repo

# Voir les logs
docker compose -f docker-compose.unraid.yml logs -f

# Redémarrer
docker compose -f docker-compose.unraid.yml restart

# Arrêter
docker compose -f docker-compose.unraid.yml down

# Mettre à jour
git pull
docker compose -f docker-compose.unraid.yml up -d --build
```

---

## Reverse proxy (optionnel)

Si tu utilises **Nginx Proxy Manager** ou le proxy Unraid, pointe vers `http://192.168.1.101:3080`.

---

## Pourquoi pas Vercel pour la prod ?

| | Vercel | Docker (Unraid) |
|---|--------|-----------------|
| UI web | ✅ | ✅ |
| API CRUD | ✅ | ✅ |
| Analyses MCP Dynatrace | ❌ | ✅ |
| Données persistantes | ❌ (/tmp) | ✅ |
| Tâches longues | ❌ | ✅ |
