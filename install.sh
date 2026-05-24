#!/bin/bash

echo "=== git-deploy installer ==="

# Check Python 3
if ! command -v python3 &>/dev/null; then
  echo "Error: python3 not found. Install it first."
  exit 1
fi

# Install pyyaml
if python3 -c "import yaml" 2>/dev/null; then
  echo "pyyaml already installed"
else
  echo "Installing pyyaml..."
  apt-get install -y python3-yaml -qq 2>/dev/null
  if ! python3 -c "import yaml" 2>/dev/null; then
    echo "Error: could not install pyyaml. Run: apt-get install python3-yaml"
    exit 1
  fi
fi

# Clone or update
if [ -d /opt/git-deploy/.git ]; then
  echo "Updating existing installation..."
  cd /opt/git-deploy && git pull -q
else
  echo "Installing to /opt/git-deploy..."
  rm -rf /opt/git-deploy
  git clone https://github.com/zennimit/git-deploy.git /opt/git-deploy -q
fi

# Config
mkdir -p /etc/git-deploy
if [ ! -f /etc/git-deploy/config.yaml ]; then
  SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  sed "s/CHANGE_ME/$SECRET/" /opt/git-deploy/config.example.yaml > /etc/git-deploy/config.yaml
  chmod 600 /etc/git-deploy/config.yaml
  echo "Created /etc/git-deploy/config.yaml with generated secret"
else
  echo "Config already exists at /etc/git-deploy/config.yaml (kept)"
  SECRET=$(python3 -c "
import yaml
with open('/etc/git-deploy/config.yaml') as f:
    print(yaml.safe_load(f).get('webhook_secret', 'CHECK_CONFIG'))
")
fi

# systemd
cp /opt/git-deploy/git-deploy.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable git-deploy -q
systemctl restart git-deploy

# Firewall
if command -v ufw &>/dev/null; then
  ufw allow 9000/tcp -q 2>/dev/null || true
fi

SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "<your-server-ip>")

echo ""
echo "=== git-deploy installed ==="
echo ""
echo "  Webhook URL:    http://$SERVER_IP:9000/webhook"
echo "  Webhook secret: $SECRET"
echo "  Config file:    /etc/git-deploy/config.yaml"
echo ""
echo "Next steps:"
echo "  1. Edit /etc/git-deploy/config.yaml to add your projects"
echo "  2. In each GitHub repo → Settings → Webhooks → Add webhook:"
echo "     - Payload URL: http://$SERVER_IP:9000/webhook"
echo "     - Content type: application/json"
echo "     - Secret: $SECRET"
echo "     - Events: Just the push event"
echo "  3. Push to test!"
