# -*- coding: utf-8 -*-
"""
独立脚本：登录 OJ -> 获取 classID
目标 classID = 265  (examId=419)
用法：python fetch_classid.py
"""

import time
import json
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

# ================= 配置 =================
OJ_URL = "http://oj.dhu.edu.cn"
USERNAME = "weishi_corroding@163.com"
PASSWORD = "Dh_411411"
EXAM_ID = "419"


def login_and_get_credentials(driver):
    """登录 OJ，返回 (token_value, jsessionid)"""
    driver.get(OJ_URL)
    print("[1] 正在登录...")

    # 输入账号
    username_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//input[@placeholder='登录账号']"))
    )
    username_input.clear()
    username_input.send_keys(USERNAME)

    # 输入密码
    password_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//input[@placeholder='请输入密码']"))
    )
    password_input.clear()
    password_input.send_keys(PASSWORD)
    time.sleep(0.3)
    password_input.send_keys(Keys.ENTER)
    print("[2] 登录提交完成，等待跳转...")
    time.sleep(3)

    # 获取 Token 来自 localStorage
    print("[3] 读取 Token...")
    token_raw = driver.execute_script(
        "return localStorage.getItem('DHU_OJ_ACCESS_TOKEN_USER');"
    )
    if not token_raw:
        print("  [!!] 未找到 Token，可能登录失败或页面未正确加载")
        # 尝试等待更久
        time.sleep(3)
        token_raw = driver.execute_script(
            "return localStorage.getItem('DHU_OJ_ACCESS_TOKEN_USER');"
        )
        if not token_raw:
            return None, None

    # 解析 Token (JSON 包装)
    try:
        token_data = json.loads(token_raw)
        token_value = token_data.get("value")
    except (json.JSONDecodeError, TypeError):
        token_value = token_raw

    print(f"  [OK] Token: {token_value[:20]}...{token_value[-8:]}")

    # 获取 JSESSIONID 来自 Cookies
    print("[4] 读取 JSESSIONID...")
    all_cookies = driver.get_cookies()
    jsessionid = ""
    for c in all_cookies:
        if c["name"] == "JSESSIONID":
            jsessionid = c["value"]
            break

    if not jsessionid:
        print("  [!!] 未找到 JSESSIONID")
        return token_value, None

    print(f"  [OK] JSESSIONID: {jsessionid[:20]}...")
    return token_value, jsessionid


def fetch_classid(token_value, jsessionid):
    """调用 API 获取 classID"""
    url = f"https://oj.dhu.edu.cn/api/classes/findClassInExamByStudentId?examId={EXAM_ID}"

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Authorization": token_value,
        "Connection": "keep-alive",
        "Referer": "https://oj.dhu.edu.cn/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36 Edg/149.0.0.0",
        "sec-ch-ua": '"Microsoft Edge";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }

    cookies = {"JSESSIONID": jsessionid}

    print(f"\n[5] 请求 API: {url}")
    print(f"    Authorization: {token_value[:20]}...{token_value[-8:]}")
    print(f"    JSESSIONID: {jsessionid[:20]}...")

    try:
        resp = requests.get(url, headers=headers, cookies=cookies, timeout=15)
        print(f"    状态码: {resp.status_code}")
        print(f"    响应内容: {resp.text[:500]}")

        if resp.status_code != 200:
            print(f"  [!!] API 请求失败")
            return None

        data = resp.json()
        print(f"\n[6] 解析结果:")
        print(f"    code: {data.get('code')}")
        print(f"    msg: {data.get('msg')}")

        if data.get("code") == 0:
            result = data.get("data", [])
            if isinstance(result, list):
                for item in result:
                    print(f"    classID: {item.get('id')}, name: {item.get('name')}")
            else:
                print(f"    data: {result}")
            return result
        else:
            print(f"  [!!] 业务错误: {data}")
            return None

    except Exception as e:
        print(f"  [!!] 请求异常: {e}")
        return None


def main():
    print("=" * 60)
    print("  OJ ClassID 获取工具")
    print(f"  ExamID: {EXAM_ID}")
    print("=" * 60)

    driver = webdriver.Edge()
    driver.maximize_window()

    try:
        token_value, jsessionid = login_and_get_credentials(driver)
        if not token_value or not jsessionid:
            print("\n[!!] 获取凭证失败，请检查登录状态")
            return

        result = fetch_classid(token_value, jsessionid)

        if result:
            print("\n[OK] 成功获取 classID 信息")
        else:
            print("\n[!!] 获取 classID 失败")

    except Exception as e:
        print(f"\n[!!] 程序异常: {e}")
    finally:
        print("\n按回车键关闭浏览器...")
        input()
        driver.quit()


if __name__ == "__main__":
    main()
