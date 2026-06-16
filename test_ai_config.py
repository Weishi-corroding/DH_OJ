"""
验证 AI 调用逻辑：从 oj_config.json 读取配置并调用 DeepSeek API
"""
import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oj_config.json")

# 读取配置
print(f"读取配置: {CONFIG_FILE}")
with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    cfg = json.load(f)

print(f"  API URL: {cfg.get('api_url')}")
print(f"  Model:   {cfg.get('model')}")
print(f"  Key:     {cfg.get('api_key')[:8]}...{cfg.get('api_key')[-4:]}")

# 调用 AI
from openai import OpenAI
client = OpenAI(api_key=cfg["api_key"], base_url=cfg["api_url"])

print("\n发送测试请求...")
resp = client.chat.completions.create(
    model=cfg["model"],
    messages=[
        {"role": "system", "content": "只输出 'Hello, AI works!' 即可"},
        {"role": "user", "content": "测试"},
    ],
    stream=False,
)
print(f"响应: {resp.choices[0].message.content}")
print("\n[OK] AI 调用验证通过")
