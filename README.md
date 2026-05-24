# git-deploy

Lightweight git-push-to-deploy for any VPS. Push to GitHub, your server auto-pulls and restarts. Like Railway, but for $5 servers.

One webhook listener handles all your projects. Config maps GitHub repos to project directories.

## Install

```bash
curl -sSL https://raw.githubusercontent.com/zennimit/git-deploy/main/install.sh | sudo bash
```

## Configure

Edit `/etc/git-deploy/config.yaml`:

```yaml
listen_port: 9000
webhook_secret: "auto-generated-during-install"

projects:
  yourname/my-app:
    branch: main
    directory: /opt/my-app
    deploy_command: "git pull origin main && sudo systemctl restart my-app"

  yourname/api-server:
    branch: main
    directory: /opt/api-server
    deploy_command: "git pull origin main && pip install -r requirements.txt && sudo systemctl restart api-server"
```

Config reloads on every webhook, so add projects without restarting.

## Add a project

1. Clone your repo on the server: `git clone https://github.com/you/project.git /opt/project`
2. Add the project to `/etc/git-deploy/config.yaml`
3. In your GitHub repo: Settings → Webhooks → Add webhook
   - **Payload URL:** `http://<server-ip>:9000/webhook`
   - **Content type:** `application/json`
   - **Secret:** the secret from install output (or from config.yaml)
   - **Events:** Just the push event

Push and it deploys.

## How it works

```
git push → GitHub webhook POST → git-deploy (port 9000)
                                      ↓
                                verify HMAC signature
                                      ↓
                                lookup repo in config.yaml
                                      ↓
                                cd <directory> && deploy_command
                                      ↓
                                done (2-3 seconds)
```

## Health check

```bash
curl http://localhost:9000/health
```

## Logs

```bash
journalctl -u git-deploy -f
```

## Update git-deploy itself

```bash
cd /opt/git-deploy && git pull && sudo systemctl restart git-deploy
```
