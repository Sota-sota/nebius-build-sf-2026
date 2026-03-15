#!/bin/bash
# Deploy SmolVLA server to Nebius GPU VM
# Usage: ./deploy.sh <VM_IP>
#
# Prerequisites on local machine:
#   - SSH key configured for Nebius VM
#   - HuggingFace cache at ~/.cache/huggingface/hub/

set -e

VM_IP="${1:?Usage: ./deploy.sh <VM_IP>}"
REMOTE_DIR="/home/ubuntu/smolvla_server"
HF_CACHE="$HOME/.cache/huggingface/hub"

echo "=== Deploying SmolVLA server to $VM_IP ==="

# 1. Create remote directory
ssh ubuntu@$VM_IP "mkdir -p $REMOTE_DIR"

# 2. Copy server files
scp smolvla_server.py requirements.txt ubuntu@$VM_IP:$REMOTE_DIR/

# 3. Copy HuggingFace model cache (avoids re-downloading ~2GB on VM)
echo "Copying HuggingFace model cache (this may take a while)..."
rsync -av --progress \
  "$HF_CACHE/models--lerobot--smolvla_base" \
  "$HF_CACHE/models--lerobot-edinburgh-white-team--smolvla_svla_so101_pickplace" \
  ubuntu@$VM_IP:"$HF_CACHE/" 2>/dev/null || echo "[WARN] Some models not found locally, VM will download from HF"

# 4. Install dependencies on VM
ssh ubuntu@$VM_IP "
  cd $REMOTE_DIR
  pip install -q -r requirements.txt
"

# 5. Start server (via nohup so it persists after SSH disconnect)
ssh ubuntu@$VM_IP "
  cd $REMOTE_DIR
  pkill -f smolvla_server || true
  nohup uvicorn smolvla_server:app --host 0.0.0.0 --port 8001 > server.log 2>&1 &
  echo 'Server starting... PID:' \$!
  sleep 3
  curl -s http://localhost:8001/health || echo 'Not ready yet, check server.log'
"

echo ""
echo "=== Deployment complete ==="
echo "Endpoint : http://$VM_IP:8001"
echo "Health   : http://$VM_IP:8001/health"
echo "Logs     : ssh ubuntu@$VM_IP 'tail -f $REMOTE_DIR/server.log'"
echo ""
echo "Set in .env:"
echo "  SMOLVLA_ENDPOINT_URL=http://$VM_IP:8001"
