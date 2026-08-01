#!/data/data/com.termux/files/usr/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# start-llm-1b.sh — Lance llama-server avec Qwen 2.5 1.5B sur port 8081
# À exécuter dans Termux : bash start-llm-1b.sh
# ─────────────────────────────────────────────────────────────────────────────

LLAMA_SERVER="/data/data/com.termux/files/home/llama.cpp/build/bin/llama-server"
MODEL="/data/data/com.termux/files/home/models/qwen2.5-1.5b-instruct-q4_k_m.gguf"
PORT=8081
LOG="/data/data/com.termux/files/home/llama-1b.log"

# Vérifier si déjà en cours
if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
  echo "✓ llama-server 1B déjà actif sur port $PORT"
  exit 0
fi

echo "Démarrage llama-server Qwen 2.5 1.5B sur port $PORT..."
nohup "$LLAMA_SERVER" \
  -m "$MODEL" \
  --host 0.0.0.0 \
  --port $PORT \
  -c 2048 \
  -t 4 \
  -b 512 \
  --alias qwen2.5-1.5b \
  > "$LOG" 2>&1 &

PID=$!
echo "PID=$PID — log: $LOG"

# Attendre que le serveur soit prêt
for i in $(seq 1 15); do
  sleep 1
  if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
    echo "✓ Serveur prêt sur port $PORT"
    exit 0
  fi
  echo -n "."
done

echo ""
echo "✗ Serveur pas encore prêt — vérifie $LOG"
