#!/bin/bash
#
# Portkey Gateway Installation Script for OpenShift
# Usage: ./install.sh [NAMESPACE] [OPTIONS]
#
# Options:
#   --no-ollama    Skip Ollama deployment
#   --model NAME   Specify Ollama model (default: llama3)
#

set -e

# Default configuration
NAMESPACE="${1:-hacohen-portkey}"
RELEASE_NAME="portkey-gateway"
HELM_CHART="./helm"
OLLAMA_ENABLED="true"
OLLAMA_MODEL="llama3"

# Parse additional arguments
shift 2>/dev/null || true
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-ollama)
            OLLAMA_ENABLED="false"
            shift
            ;;
        --model)
            OLLAMA_MODEL="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "============================================"
echo "Portkey Gateway Installation Script"
echo "============================================"
echo "Namespace:     ${NAMESPACE}"
echo "Release:       ${RELEASE_NAME}"
echo "Ollama:        ${OLLAMA_ENABLED}"
if [[ "${OLLAMA_ENABLED}" == "true" ]]; then
    echo "Ollama Model:  ${OLLAMA_MODEL}"
fi
echo ""

# Check prerequisites
command -v oc >/dev/null 2>&1 || { echo "Error: 'oc' command not found. Please install OpenShift CLI."; exit 1; }
command -v helm >/dev/null 2>&1 || { echo "Error: 'helm' command not found. Please install Helm 3."; exit 1; }

# Verify OpenShift connection
echo "Checking OpenShift connection..."
oc whoami || { echo "Error: Not logged into OpenShift. Run 'oc login' first."; exit 1; }
echo ""

# Step 1: Create namespace
echo "[1/3] Creating namespace '${NAMESPACE}'..."
oc create namespace "${NAMESPACE}" --dry-run=client -o yaml | oc apply -f -
echo ""

# Step 2: Update Helm dependencies
echo "[2/3] Updating Helm dependencies..."
cd "$(dirname "$0")"
helm dependency update "${HELM_CHART}"
echo ""

# Step 3: Deploy with Helm
echo "[3/3] Deploying Portkey Gateway with Helm..."
helm upgrade --install "${RELEASE_NAME}" "${HELM_CHART}" \
    --namespace "${NAMESPACE}" \
    --set ollama.enabled="${OLLAMA_ENABLED}" \
    --set ollama.model="${OLLAMA_MODEL}" \
    --wait --timeout 10m

echo ""
echo "============================================"
echo "Installation Complete!"
echo "============================================"
echo ""

# Display status
echo "Pod Status:"
oc get pods -n "${NAMESPACE}"
echo ""

# Wait for gateway pods to be ready
echo "Waiting for gateway pods to be ready..."
oc wait --for=condition=ready pod -l app.kubernetes.io/name=portkey-gateway -n "${NAMESPACE}" --timeout=120s 2>/dev/null || echo "Warning: Gateway pods not ready yet."
echo ""

# Display URLs
GATEWAY_URL=$(oc get route "${RELEASE_NAME}" -n "${NAMESPACE}" -o jsonpath='{.spec.host}' 2>/dev/null || echo "Not found")

echo "============================================"
echo "Access Information"
echo "============================================"
echo ""
echo "Gateway URL:     https://${GATEWAY_URL}"
echo "Gateway UI:      https://${GATEWAY_URL}/public/"
echo ""

if [[ "${OLLAMA_ENABLED}" == "true" ]]; then
    echo "Ollama Model:    ${OLLAMA_MODEL}"
    echo ""
    echo "Note: Ollama is downloading the model in the background."
    echo "      This may take several minutes depending on model size."
    echo ""
    echo "Check Ollama status:"
    echo "  oc get pods -n ${NAMESPACE} -l app.kubernetes.io/component=ollama"
    echo ""
    echo "Test Ollama via Portkey Gateway:"
    echo "  curl -X POST \"https://${GATEWAY_URL}/v1/chat/completions\" \\"
    echo "    -H \"Content-Type: application/json\" \\"
    echo "    -H \"x-portkey-provider: ollama\" \\"
    echo "    -H \"x-portkey-custom-host: http://${RELEASE_NAME}-ollama:11434\" \\"
    echo "    -d '{\"model\": \"${OLLAMA_MODEL}\", \"messages\": [{\"role\": \"user\", \"content\": \"Hello!\"}]}'"
    echo ""
fi

echo "For more information, see the Helm notes:"
echo "  helm get notes ${RELEASE_NAME} -n ${NAMESPACE}"
echo ""

