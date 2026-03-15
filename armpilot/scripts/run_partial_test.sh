#!/bin/bash
# SmolVLA HTTP パス 部分テスト手順
# Track 1 VM なしで SmolVLA パス全体を手動確認する

set -e
BACKEND_DIR="$(cd "$(dirname "$0")/../backend" && pwd)"
SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$BACKEND_DIR/.venv/bin/python"

echo "=== Step 1: pytest integration tests ==="
cd "$BACKEND_DIR"
"$PYTHON" -m pytest ../tests/test_smolvla_integration.py -m integration -v
echo ""

echo "=== Step 2: Dummy SmolVLA サーバーを起動 (バックグラウンド) ==="
DUMMY_SMOLVLA_PORT=9999 PYTHONPATH="$BACKEND_DIR" "$PYTHON" "$SCRIPTS_DIR/dummy_smolvla_server.py" &
DUMMY_PID=$!
sleep 1

echo "=== Step 3: ヘルスチェック ==="
curl -s http://localhost:9999/health | python3 -m json.tool

echo ""
echo "=== Step 4: POST /predict サンプル ==="
curl -s -X POST http://localhost:9999/predict \
  -H "Content-Type: application/json" \
  -d '{"instruction":"pick up the red cup gently","joint_state":[0,0,0,0,0,0],"image_b64":null}' \
  | python3 -m json.tool

echo ""
echo "=== Step 5: バックエンドを USE_SMOLVLA=true で起動して E2E 確認 ==="
echo "別ターミナルで以下を実行:"
echo ""
echo "  cd $BACKEND_DIR"
echo "  SMOLVLA_ENDPOINT_URL=http://localhost:9999 USE_SMOLVLA=true \\"
echo "    uvicorn main:app --reload --port 8000"
echo ""
echo "  # さらに別ターミナルで:"
echo "  npx wscat -c ws://localhost:8000/ws"
echo '  {"type": "command", "text": "pick up the red cup"}'
echo ""

kill $DUMMY_PID 2>/dev/null
echo "Dummy サーバー停止 (PID $DUMMY_PID)"
