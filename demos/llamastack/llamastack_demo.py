from llama_stack_client import LlamaStackClient


"""
Portkey doesn't automatically aggregate models from all backends - you need one client per provider to list their models separately.
"""
client = LlamaStackClient(
    base_url="https://portkey-gateway-hacohen-portkey.apps.ai-dev02.kni.syseng.devcluster.openshift.com/v1",
    api_key="not-needed",
    default_headers={
        "x-portkey-provider": "ollama",
        "x-portkey-custom-host": "http://portkey-gateway-ollama:11434"
    }
)


models = client.models.list()
print("Available Models:", models)
print("Total Available Models:", len(models))

# Then use it normally
response = client.chat.completions.create(
    model="llama3",
    messages=[{"role": "user", "content": "Hello!"}]
)

print("\nResponse:", response.choices[0].message.content)
