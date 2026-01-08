import os
import sys
from openai import OpenAI

# ================= 配置区域 =================
# 这里填入你之前提供的 Key
API_KEY = 'sk-e00efab0672a406e9a1bf9b865145064'
BASE_URL = "https://api.deepseek.com"
MODEL_NAME = "deepseek-chat"

# 设置环境变量 (或者直接传给 client 也可以)
os.environ['DEEPSEEK_API_KEY'] = API_KEY

def test_ai_connection():
    print(f"[-] 正在初始化 OpenAI 客户端...")
    print(f"    Base URL: {BASE_URL}")
    print(f"    API Key:  {API_KEY[:8]}******")
    
    try:
        client = OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL
        )
    except Exception as e:
        print(f"\n[!] 客户端初始化失败: {e}")
        return

    # 模拟题目
    test_prompt = "请写一个 C++ 程序，输出 Hello World。"
    
    system_prompt = (
        "你是一个C++算法竞赛专家。请直接输出可编译的完整C++代码。"
        "要求：使用标准输入输出 (cin/cout)，不要包含 markdown 标记。"
    )

    print(f"[-] 正在发送请求给模型: {MODEL_NAME} ...")
    
    try:
        # 发起请求
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": test_prompt},
            ],
            stream=False
        )
        
        # 获取结果
        content = response.choices[0].message.content
        print("\n[+] 请求成功！AI 回复内容如下：")
        print("="*40)
        print(content)
        print("="*40)
        
    except Exception as e:
        print("\n[!] 请求发生错误 (Error Details):")
        print("-" * 30)
        # 打印详细错误类型
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        
        # 如果是 OpenAI 的特定错误，通常包含更多信息
        if hasattr(e, 'status_code'):
             print(f"HTTP 状态码: {e.status_code}")
        if hasattr(e, 'response'):
             print(f"服务端响应: {e.response}")
        if hasattr(e, 'body'):
             print(f"错误详情 Body: {e.body}")
        print("-" * 30)

if __name__ == "__main__":
    test_ai_connection()