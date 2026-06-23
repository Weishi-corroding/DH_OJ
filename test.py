import time
import re
import pyperclip  # 必须安装: pip install pyperclip
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from openai import OpenAI
import os

# ================= 配置区域 =================
# DeepSeek API Key — 请通过环境变量 DEEPSEEK_API_KEY 设置，或直接修改下方默认值
os.environ.setdefault('DEEPSEEK_API_KEY', 'your-api-key-here')

# 账号信息
OJ_URL = "http://oj.dhu.edu.cn"
USERNAME = "your-username"
PASSWORD = "your-password"

# 初始化 DeepSeek 客户端
# (逻辑已确认与测试脚本一致)
client = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com"
)

# ================= 辅助函数 =================

def get_ai_solution(prompt_content, current_code=None, error_msg=None):
    """调用 DeepSeek 获取代码或修复代码"""
    system_prompt = (
        "你是一个C++算法竞赛专家。请直接输出可编译的完整C++代码。"
        "要求："
        "1. 使用标准输入输出 (cin/cout)。"
        "2. 不要包含 ```cpp 或 ``` 等 Markdown 标记，直接输出纯代码。"
        "3. 不需要任何解释性文字。"
        "4. 代码应兼容 MinGW 编译器。"
        "5. 每一行结束后应用\n进行换行。"
    )
    
    user_content = f"题目描述如下：\n{prompt_content}"
    
    # 如果是修复模式，追加错误信息
    if error_msg and current_code:
        user_content = (
            f"我之前的代码如下：\n{current_code}\n\n"
            f"OJ系统报错/运行结果如下：\n{error_msg}\n\n"
            f"请分析错误原因并修正代码，直接输出修正后的完整纯代码。"
        )

    mode_str = "修复模式" if error_msg else "生成模式"
    print(f">>> [DeepSeek] 正在请求 AI ({mode_str})...")
    
    try:
        response = client.chat.completions.create(
            model="deepseek-reasoner",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            stream=False
        )
        content = response.choices[0].message.content
        print(">>> AI 响应成功。")
        return content
    except Exception as e:
        print(f"!!! AI 调用失败: {e}")
        return None

def wait_and_click(driver, by, value, timeout=10):
    """等待元素可点击并点击"""
    try:
        element = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, value)))
        element.click()
        return element
    except:
        return None

def wait_and_input(driver, by, value, text, timeout=10, press_enter=False):
    """等待输入框并输入"""
    element = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
    element.clear()
    element.send_keys(text)
    if press_enter:
        element.send_keys(Keys.ENTER)

def clean_problem_text(driver):
    """提取题目描述"""
    try:
        # 确保在题目详情页，提取文本
        content_div = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".n-tab-pane:not([style*='display: none'])"))
        )
        return content_div.get_attribute('innerText')
    except:
        return ""

def draw_modal(driver):
    driver.find_element(By.XPATH, "//div[@class='n-base-selection']").click()
    time.sleep(0.2)
    options = driver.find_elements(By.CSS_SELECTOR, ".n-base-select-option__content")
    target_opt = None
    max_major, max_minor = -1, -1

    for opt in options:
        match = re.search(r'\((\d+)\.(\d+)\)', opt.text)
        if match:
            maj, min_ = int(match.group(1)), int(match.group(2))
            if maj > max_major or (maj == max_major and min_ > max_minor):
                max_major, max_minor = maj, min_
                target_opt = opt

    if target_opt: target_opt.click()
    else: options[-1].click()
    time.sleep(0.5)
    wait_and_click(driver, By.XPATH, "//button[.//span[contains(text(), '我要抽题')]]")
    print("已点击抽题，等待加载...")  
def solve_modal(driver):
    try:
        WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, "//div[contains(text(), '切换到题目类别')]")))
        print("检测到抽题弹窗，正在自动选择...")
        try:
            driver.find_element(By.XPATH,"//label[.//div[contains(text(), '切换到题目类别')]]").click()
        except: pass
        draw_modal(driver)
    except:
        try:
            WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, "//p[contains(text(), '切换到题目类别')]")))
            print("检测到抽题弹窗，正在自动选择...")
            draw_modal(driver)
        except:
            return  # 无弹窗，直接返回 
            # 智能选择最大章节 (5.1 > 3.3)
            
            

    # ================= 主程序 =================

def main():
    print("正在启动 Edge 浏览器...")
    driver = webdriver.Edge()
    driver.maximize_window()
    
    try:
        # 1. 登录流程
        driver.get(OJ_URL)
        try:
            wait_and_input(driver, By.CSS_SELECTOR, "input[placeholder='登录账号']", USERNAME)
            print(f"正在登录账号: {USERNAME}")
            # 输入密码并回车提交
            wait_and_input(driver, By.CSS_SELECTOR, "input[placeholder='请输入密码']", PASSWORD, press_enter=True)
            print("登录提交完成，等待跳转...")
            time.sleep(3)
        except Exception as e:
            print(f"登录异常: {e}")
            print("请手动登录，登录完成后按回车继续...")
            input()
        # 2. 进入考试列表
        driver.get(f"{OJ_URL}/#/user/exam-list")
        time.sleep(2)
        
        print("寻找并点击第二个【参加】按钮...")
        buttons = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//button[span[contains(text(), '参加')]]"))
        )
        if len(buttons) >= 2:
            buttons[1].click()
        else:
            buttons[0].click()
            
        print("点击【开始做题】...")
        wait_and_click(driver, By.XPATH, "//button[span[contains(text(), '开始做题')]]")
        time.sleep(2)

        # ================= 循环做题逻辑 =================
        while True:
            # A. 处理抽题/类别选择弹窗
            solve_modal(driver)

            # B. 读取题目
            print("--------------------------------------------------")
            print("正在读取题目...")
            problem_prompt = clean_problem_text(driver)
            
            # 容错：如果读取失败，尝试手动切回详情Tab
            if not problem_prompt:
                try:
                    driver.find_element(By.CSS_SELECTOR, "div[data-name='detail']").click()
                    time.sleep(1)
                    problem_prompt = clean_problem_text(driver)
                except: pass
            # C. AI 生成代码
            current_code = get_ai_solution(problem_prompt).replace("```cpp", "").replace("```", "")
            print(current_code)
            # D. 填入代码 & 提交 (直到通过)
            solved = False
            while not solved:
                    # 3. 【核心修改】剪贴板 + 键盘模拟写入
                    print("正在写入代码 (Ctrl+V)...")
                    pyperclip.copy(current_code.strip())
                    driver.switch_to.active_element.send_keys(Keys.CONTROL, 'a')  # 全选
                    driver.switch_to.active_element.send_keys(Keys.CONTROL, 'v')  # 粘贴
                    time.sleep(0.5)
                    # 4. 选择 MinGW 语言
                    try:
                        selections = driver.find_elements(By.CSS_SELECTOR, ".n-base-selection")
                        for sel in selections:
                            if sel.is_displayed():
                                sel.click()
                                time.sleep(0.2)
                                mingw = driver.find_elements(By.XPATH, "//div[contains(text(), 'MinGW')]")
                                if mingw:
                                    mingw[0].click()
                                    # 点击空白处关闭下拉
                                    ActionChains(driver).move_by_offset(0,0).click().perform()
                                    break
                    except: pass
                    # 5. 点击提交
                    print("点击提交...")
                    wait_and_click(driver, By.XPATH, "//button[span[contains(text(), '提交代码')]]")

                    # 6. 等待判题结果
                    print("等待判题结果...")
                    time.sleep(10)  # 初始等待
                    # 处理确认提交弹窗
                    try:
                        confirm_btn = WebDriverWait(driver, 15).until(
                            EC.element_to_be_clickable((By.XPATH, "//div[@class='n-dialog__action']//button[span[contains(text(), '提交')]]"))
                        )
                        confirm_btn.click()
                    except: pass
                    
                    # 处理抄袭警告 (坚持提交)
                    try:
                        wait_and_click(driver, By.XPATH, "//button[span[contains(text(), '坚持提交')]]", timeout=2)
                    except: pass

                    # 检查是否AC (看是否弹出了抽题按钮)
                    try:
                        WebDriverWait(driver, 15).until(
                            EC.presence_of_element_located((By.XPATH, "//div[contains(text(), '即将开始下一题')]"))
                        )
                        success_btn = driver.find_element(By.XPATH, "//div[contains(@class, 'n-modal')]//button[.//span[contains(text(), '我要抽题')]]")
                        if success_btn and success_btn.is_displayed():
                            print(">>> 题目通过 (AC)！进入下一题。")
                            driver.execute_script("arguments[0].click();", success_btn)
                            time.sleep(2)
                            break  # 跳出提交循环，进入下一题
                    except:
                        try:
                            WebDriverWait(driver, 15).until(
                            EC.presence_of_element_located((By.XPATH, "//div[contains(text(), '已通关')]"))
                        )
                            break
                    # 获取错误信息
                        except:
                            pass   
                        
                    
                    # 未 AC，获取错误信息
                    input("未通过，获取报错信息...")
                    

    except Exception as e:
        print(f"主程序崩溃: {e}")
    finally:
        print("脚本结束。")
        input("按回车键关闭浏览器...")
        driver.quit()

if __name__ == "__main__":
    main()