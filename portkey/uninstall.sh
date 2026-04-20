#!/bin/bash
#
# Portkey Gateway Uninstall Script for OpenShift
# Usage: ./uninstall.sh [NAMESPACE] [OPTIONS]
#
# Options:
#   --delete-namespace    Also delete the namespace
#   --force               Skip confirmation prompt
#

set -e

# Default configuration
NAMESPACE="${1:-hacohen-portkey}"
RELEASE_NAME="portkey-gateway"
DELETE_NAMESPACE="false"
FORCE="false"

# Parse additional arguments
shift 2>/dev/null || true
while [[ $# -gt 0 ]]; do
    case $1 in
        --delete-namespace)
            DELETE_NAMESPACE="true"
            shift
            ;;
        --force|-f)
            FORCE="true"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "============================================"
echo "Portkey Gateway Uninstall Script"
echo "============================================"
echo "Namespace:        ${NAMESPACE}"
echo "Release:          ${RELEASE_NAME}"
echo "Delete Namespace: ${DELETE_NAMESPACE}"
echo ""

# Check prerequisites
command -v oc >/dev/null 2>&1 || { echo "Error: 'oc' command not found. Please install OpenShift CLI."; exit 1; }
command -v helm >/dev/null 2>&1 || { echo "Error: 'helm' command not found. Please install Helm 3."; exit 1; }

# Verify OpenShift connection
echo "Checking OpenShift connection..."
oc whoami || { echo "Error: Not logged into OpenShift. Run 'oc login' first."; exit 1; }
echo ""

# Confirm deletion
if [[ "${FORCE}" != "true" ]]; then
    if [[ "${DELETE_NAMESPACE}" == "true" ]]; then
        read -p "Are you sure you want to delete Portkey Gateway AND namespace '${NAMESPACE}'? [y/N] " -n 1 -r
    else
        read -p "Are you sure you want to delete Portkey Gateway from namespace '${NAMESPACE}'? [y/N] " -n 1 -r
    fi
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
    echo ""
fi

# Step 1: Uninstall Helm release
echo "[1/3] Uninstalling Helm release '${RELEASE_NAME}'..."
helm uninstall "${RELEASE_NAME}" --namespace "${NAMESPACE}" 2>/dev/null || echo "Helm release not found or already removed."
echo ""

# Step 2: Delete PVCs
echo "[2/3] Cleaning up Persistent Volume Claims..."
oc delete pvc -l app.kubernetes.io/instance="${RELEASE_NAME}" -n "${NAMESPACE}" --ignore-not-found=true
# Also delete Ollama PVC if exists
oc delete pvc "${RELEASE_NAME}-ollama" -n "${NAMESPACE}" --ignore-not-found=true 2>/dev/null || true
echo ""

# Step 3: Delete namespace (optional)
if [[ "${DELETE_NAMESPACE}" == "true" ]]; then
    echo "[3/3] Deleting namespace '${NAMESPACE}'..."
    oc delete namespace "${NAMESPACE}" --ignore-not-found=true
    echo ""
else
    echo "[3/3] Skipping namespace deletion (use --delete-namespace to remove)."
    echo ""
fi

echo "============================================"
echo "Uninstall Complete!"
echo "============================================"
echo ""

if [[ "${DELETE_NAMESPACE}" == "true" ]]; then
    echo "The namespace '${NAMESPACE}' and all its resources have been deleted."
else
    echo "The Portkey Gateway release has been removed from namespace '${NAMESPACE}'."
    echo "The namespace still exists. To delete it:"
    echo "  oc delete namespace ${NAMESPACE}"
fi
echo ""

