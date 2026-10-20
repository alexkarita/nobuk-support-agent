import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options=types.HttpOptions(timeout=20_000),  # 20 seconds per call
)

print("Models your key can see:")
names = []
try:
    for m in client.models.list():
        name = m.name.replace("models/", "")
        if "flash" in name or "lite" in name:
            names.append(name)
            print(" ", name)
except Exception as e:
    print("List failed:", type(e).__name__, e)

print("\nTesting each model once:")
for name in names:
    try:
        r = client.models.generate_content(model=name, contents="Say hello in 3 words")
        print(f"  OK    {name}: {r.text.strip()}")
    except Exception as e:
        print(f"  FAIL  {name}: {type(e).__name__} {str(e)[:90]}")