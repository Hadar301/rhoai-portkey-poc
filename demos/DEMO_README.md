# Shared Demo Elements

This file contains common elements referenced by individual demo documentation files to eliminate duplication.

## Common Prerequisites

### Base Requirements
- Portkey AI Gateway deployed on OpenShift
- Python 3.12+
- Required packages: `portkey-ai>=2.1.0`, `tabulate>=0.9.0`

### Provider-Specific Requirements
- **Ollama**: Ollama deployment accessible via gateway (included by default in Helm chart)
- **RHOAI**: KServe InferenceService models accessible via gateway (see [RHOAI Integration Guide](../docs/RHOAI-INTEGRATION.md))
- **External LLMs**: API keys configured in Helm values.yaml

## Common Installation Pattern

The demo is located in the `demos/{feature}` directory:

```bash
cd demos/{feature}
```

All dependencies are already defined in the project's `pyproject.toml`.

## Common Configuration Code

### Portkey Client Initialization

```python
from portkey_ai import Portkey

client = Portkey(
    base_url=GATEWAY_API_URL,
    api_key="not-needed-for-self-hosted",
    config=config  # Feature-specific configuration
)

response = client.chat.completions.create(
    model="llama3",  # Or your model name
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=100
)
```

## Common References

### Portkey Documentation
- [Portkey Config Object Reference](https://portkey.ai/docs/api-reference/inference-api/config-object)
- [Portkey Python SDK](https://github.com/Portkey-AI/portkey-python-sdk)
- [Portkey Gateway GitHub](https://github.com/Portkey-AI/gateway)

### Project Documentation
- [RHOAI Integration Guide](../docs/RHOAI-INTEGRATION.md)
- [Comparison Matrix](../docs/COMPARISON-MATRIX.md)
- [Project README](../README.md)

## Common File Structure Pattern

Each demo directory contains:
- `{feature}_demo.py` - Main demo script with CLI interface
- `config.py` - Feature-specific configuration helpers (shared across features)
- `{feature}_demo.md` - This documentation file

## Standard Usage Pattern

### Run All Tests
```bash
uv run python {feature}_demo.py
```

### Run Specific Scenarios
```bash
uv run python {feature}_demo.py --scenario {scenario_name}
```

### Provider Selection
```bash
# Use Ollama (default)
uv run python {feature}_demo.py --provider ollama

# Use RHOAI model
uv run python {feature}_demo.py --provider rhoai-primary

# Use external provider
uv run python {feature}_demo.py --provider openai
```