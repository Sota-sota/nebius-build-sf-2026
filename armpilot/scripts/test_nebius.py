import sys
sys.path.insert(0, "../backend")
from openai import OpenAI
from config import NEBIUS_API_KEY, NEBIUS_MODEL

client = OpenAI(base_url="https://api.tokenfactory.nebius.com/v1", api_key=NEBIUS_API_KEY)
r = client.chat.completions.create(
    model=NEBIUS_MODEL,
    messages=[{"role": "user", "content": "Say OK"}],
    max_tokens=10,
)
print("Nebius OK:", r.choices[0].message.content)
