#!/bin/bash

# === CONFIG ===
USER="thyregod"
HOST="10.0.16.197"
PROJECT="TM-Fleet"
REMOTE_PATH="/home/$USER/$PROJECT"
LOCAL_PATH="C:/Users/Thyregod/PycharmProjects/$PROJECT"

echo "🚦 Stopping service..."
ssh "$USER@$HOST" "sudo systemctl stop tm-fleet"

echo "🧹 Removing old project..."
ssh "$USER@$HOST" "rm -rf $REMOTE_PATH"

echo "📤 Copying project to Raspberry Pi..."
scp -r "$LOCAL_PATH" "$USER@$HOST:$REMOTE_PATH"

echo "🐍 Rebuilding virtual environment..."
ssh "$USER@$HOST" << EOF
  cd $REMOTE_PATH
  python3 -m venv venv
  source venv/bin/activate
  pip install flask
EOF

echo "🔁 Restarting service..."
ssh "$USER@$HOST" "sudo systemctl daemon-reload && sudo systemctl restart tm-fleet"

echo "✅ Deployed and running!"
echo "🌍 Visit: http://$HOST:5000"
