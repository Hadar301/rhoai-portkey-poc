#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="hacohen-portkey"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PF_PID=""

cleanup() {
    echo
    echo "[cleanup] Stopping background processes..."
    if [[ -n "$PF_PID" ]] && kill -0 "$PF_PID" 2>/dev/null; then
        kill "$PF_PID" 2>/dev/null || true
        wait "$PF_PID" 2>/dev/null || true
    fi
    # Kill any remaining port-forwards on 6379
    local pids
    pids=$(lsof -ti:6379 2>/dev/null || true)
    if [[ -n "$pids" ]]; then
        kill $pids 2>/dev/null || true
    fi
    # Kill any orphaned oc port-forward processes started by this script
    pkill -f "oc port-forward svc/portkey-redis-master" 2>/dev/null || true
    echo "[cleanup] Done."
}
trap cleanup EXIT INT TERM HUP

echo "============================================================"
echo "  Portkey AI Gateway - Full Demo Suite"
echo "============================================================"
echo

# --- pre-flight checks ---
echo "[pre-flight] Verifying cluster connectivity..."
oc whoami --show-server >/dev/null 2>&1 || { echo "ERROR: not logged into an OpenShift cluster"; exit 1; }
oc project "$NAMESPACE" >/dev/null 2>&1 || { echo "ERROR: cannot switch to project $NAMESPACE"; exit 1; }

echo "[pre-flight] Checking pods..."
oc get pods -n "$NAMESPACE" --no-headers | grep -v Completed

GATEWAY_READY=$(oc get pods -n "$NAMESPACE" -l app.kubernetes.io/name=portkey-gateway --no-headers 2>/dev/null | awk '{print $2}' | head -1)
if [[ "$GATEWAY_READY" != "1/1" ]]; then
    echo "WARNING: Portkey gateway pod is not ready ($GATEWAY_READY)"
fi

# --- Redis setup ---
echo
echo "[setup] Fetching Redis password..."
REDIS_PASSWORD=$(oc get secret portkey-redis -n "$NAMESPACE" -o jsonpath='{.data.redis-password}' | base64 -d)
export REDIS_PASSWORD

echo "[setup] Starting Redis port-forward (6379)..."
EXISTING_PF=$(lsof -ti:6379 2>/dev/null || true)
if [[ -n "$EXISTING_PF" ]]; then
    echo "[setup] Killing existing process on port 6379 (pid $EXISTING_PF)..."
    kill $EXISTING_PF 2>/dev/null || true
    sleep 1
fi
oc port-forward svc/portkey-redis-master 6379:6379 -n "$NAMESPACE" &>/dev/null &
PF_PID=$!
sleep 2

if ! kill -0 "$PF_PID" 2>/dev/null; then
    echo "ERROR: Redis port-forward failed to start"
    exit 1
fi
echo "[setup] Redis port-forward running (pid $PF_PID)"

# --- run demos ---
cd "$REPO_DIR"

run_demo() {
    local name="$1"
    shift
    echo
    echo "============================================================"
    echo "  DEMO: $name"
    echo "============================================================"
    if uv run "$@"; then
        echo
        echo "  >> $name: PASSED"
    else
        echo
        echo "  >> $name: FAILED (exit $?)"
    fi
}

run_demo "Guardrails"          python demos/guardrails/guardrails_demo.py --scenario all
run_demo "Fallback"            python demos/fallback/fallback_demo.py --scenario all
run_demo "Load Balancing"      python demos/load_balance/load_balance_demo.py --scenario all
run_demo "Redis Caching"       python demos/caching/redis_caching_demo.py --clear-cache
run_demo "Semantic Caching"    python demos/caching/semantic_caching_demo.py
run_demo "LlamaStack"          python demos/llamastack/llamastack_demo.py
run_demo "RHOAI Connectivity (Ollama)"       python demos/rhoai/connectivity_test.py --provider ollama
run_demo "RHOAI Connectivity (vLLM/Granite)" python demos/rhoai/connectivity_test.py --provider rhoai-primary

echo
echo "============================================================"
echo "  All demos finished."
echo "============================================================"
