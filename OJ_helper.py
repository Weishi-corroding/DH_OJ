import os
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from openai import OpenAI

# ================= 配置区域 =================
# DeepSeek API Key (按照要求设置)
os.environ['DEEPSEEK_API_KEY'] = 'sk-e00efab0672a406e9a1bf9b865145064'

# 账号信息
OJ_URL = "http://oj.dhu.edu.cn"
USERNAME = "weishi_corroding@163.com"
PASSWORD = "Dh_411411"

# 初始化 DeepSeek 客户端
client = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com"
)

# ================= 辅助函数 =================

def get_ai_solution(prompt_content, current_code=None, error_msg=None):
    """调用 DeepSeek 获取代码或修复代码"""
    system_prompt = "你是一个C++算法竞赛专家。请直接输出可编译的完整C++代码(使用MinGW标准)，不要包含markdown标记(如```cpp)，不要包含任何解释性文字。"
    
    user_content = prompt_content
    if error_msg:
        user_content = f"我之前的代码如下：\n{current_code}\n\n报错信息如下：\n{error_msg}\n\n请根据报错修正代码，直接输出修正后的完整代码。"

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            stream=False
        )
        content = response.choices[0].message.content
        # 清理可能存在的 markdown 标记
        content = content.replace("```cpp", "").replace("```", "").strip()
        return content
    except Exception as e:
        print(f"AI 调用失败: {e}")
        return None

def wait_and_click(driver, by, value, timeout=10):
    element = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, value)))
    element.click()
    return element

def wait_and_input(driver, by, value, text, timeout=10):
    element = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
    element.clear()
    element.send_keys(text)

def clean_problem_text(driver):
    """提取题目描述、输入、输出、样例"""
    try:
        # 确保在题目详情页
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//div[contains(text(), '问题描述')]")))
        
        # 获取所有文本内容
        content_div = driver.find_element(By.XPATH, "//div[contains(@class, 'n-tab-pane')][1]")
        full_text = content_div.get_attribute('innerText')
        return full_text
    except:
        return "无法提取题目内容"

# ================= 主程序 =================

def main():
    # 启动 Edge (默认配置)
    driver = webdriver.Edge()
    driver.maximize_window()
    
    try:
        driver.get(OJ_URL)
        
        # 输入账号
        print("正在输入账号...")
        wait_and_input(driver, By.XPATH, "//input[@placeholder='登录账号']", USERNAME)
        
        # 输入密码
        print("正在输入密码...")
        password_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='请输入密码']"))
        )
        password_input.clear()
        password_input.send_keys(PASSWORD)
        time.sleep(0.5) # 稍微等待一下输入完成

        # --- 修复方案开始 ---
        print("尝试点击登录...")
        password_input.send_keys(Keys.ENTER)
            

        # 2. 进入考试流程
        # 点击或者直接跳转考试页面 (这里模拟点击)
        try:
            wait_and_click(driver, By.XPATH, "//a[@href='#/user/exam-list']", timeout=5)
        except:
            driver.get(f"{OJ_URL}/#/user/exam-list")
        
        time.sleep(1)
        
        # 点击第二个“参加”按钮
        # 注意：Selenium find_elements 索引从0开始，所以第二个是 [1]
        buttons = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//button[span[contains(text(), '参加')]]"))
        )
        if len(buttons) >= 2:
            buttons[1].click()
        else:
            print("未找到第二个参加按钮，尝试点击第一个...")
            buttons[0].click()
            
        # 点击“开始做题”
        wait_and_click(driver, By.XPATH, "//button[span[contains(text(), '开始做题')]]")
        time.sleep(2)

        # ================= 循环做题逻辑 =================
        while True:
            # 3. 处理可能出现的“抽题/类别选择”弹窗
            try:
                # 检查是否存在 Modal 弹窗
                modal = driver.find_elements(By.CSS_SELECTOR, ".n-card.n-modal")
                if modal:
                    print("检测到抽题弹窗...")
                    # 选择 "切换到题目类别" (Radio value=1 或者根据文本)
                    try:
                        radio_label = driver.find_element(By.XPATH, "//div[contains(text(), '切换到题目类别')]")
                        radio_label.click()
                    except:
                        pass # 可能已经是默认选中

                    # 点击下拉框
                    wait_and_click(driver, By.CSS_SELECTOR, ".n-select .n-base-selection")
                    time.sleep(0.5)

                    # 获取所有选项并分析
                    options = driver.find_elements(By.CSS_SELECTOR, ".n-base-select-option__content")
                    best_option = None
                    max_major = -1
                    max_minor = -1
                    
                    target_element = None

                    print("正在分析题目类别...")
                    for opt in options:
                        text = opt.text
                        # 正则匹配 (5.1) 这种格式
                        match = re.search(r'\((\d+)\.(\d+)\)', text)
                        if match:
                            major = int(match.group(1))
                            minor = int(match.group(2))
                            # 寻找a最大的，如果a一样找b最大的
                            if major > max_major or (major == max_major and minor > max_minor):
                                max_major = major
                                max_minor = minor
                                target_element = opt
                    
                    if target_element:
                        print(f"选择类别: {target_element.text}")
                        target_element.click()
                    else:
                        # 如果没解析出来，选最后一个
                        options[-1].click()
                    
                    time.sleep(0.5)
                    # 点击“我要抽题”
                    wait_and_click(driver, By.XPATH, "//button[span[contains(text(), '我要抽题')]]")
                    time.sleep(2)
            except Exception as e:
                print(f"抽题流程跳过或出错 (属于正常现象如果已经进入题目): {e}")

            # 4. 获取题目详情
            print("正在获取题目详情...")
            problem_prompt = clean_problem_text(driver)
            
            # 5. 让 AI 写代码
            print("正在请求 AI 生成代码...")
            code = get_ai_solution(problem_prompt)
            if not code:
                print("AI 生成失败，重试...")
                continue
            
            current_code = code

            # 6. 填入代码
            # CodeMirror 的处理比较特殊，直接 send_keys 到 contenteditable 元素
            try:
                # 找到代码编辑区
                editor = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".cm-content"))
                )
                
                # 全选删除旧代码
                action = ActionChains(driver)
                action.click(editor).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).send_keys(Keys.BACK_SPACE).perform()
                time.sleep(0.5)
                
                # 输入新代码 (由于代码可能很长，直接 send_keys 可能会慢，但在 CodeMirror 中必须模拟输入)
                # 为了防止缩进混乱，可以尝试通过 JS 设置，但这里先用 send_keys
                driver.execute_script("arguments[0].innerText = arguments[1];", editor, current_code)
                # 触发一下 input 事件让编辑器感知
                editor.send_keys(" ") 
                editor.send_keys(Keys.BACK_SPACE)
                
            except Exception as e:
                print(f"填入代码失败: {e}")

            # 7. 选择语言 MinGW
            try:
                # 查找语言选择下拉框 (通常显示 请选择 或者 当前语言)
                # 根据 HTML 提示，可能是 n-base-selection
                # 这里假设界面上有一个 title="MinGW" 的或者默认框，我们尝试寻找下拉触发器
                # 简便方法：遍历页面上的 selection 找到包含 MinGW 选项的那个
                selections = driver.find_elements(By.CSS_SELECTOR, ".n-base-selection")
                for sel in selections:
                    try:
                        sel.click()
                        time.sleep(0.2)
                        mingw_opt = driver.find_elements(By.XPATH, "//div[contains(text(), 'MinGW')]")
                        if mingw_opt:
                            mingw_opt[0].click()
                            break
                    except:
                        continue
            except:
                print("语言选择可能已默认或失败，尝试直接提交")

            # 8. 循环提交直到 AC
            solved = False
            while not solved:
                print("提交代码中...")
                # 点击提交代码
                submit_btn = wait_and_click(driver, By.XPATH, "//button[span[contains(text(), '提交代码')]]")
                
                # 9. 处理确认弹窗
                try:
                    # 等待确认弹窗
                    dialog_confirm = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//div[@class='n-dialog__action']//button[span[contains(text(), '提交')]]"))
                    )
                    dialog_confirm.click()
                except:
                    # 可能没有确认弹窗，或者已经是涉嫌抄袭弹窗
                    pass
                
                # 处理“涉嫌抄袭”提示 (坚持提交)
                try:
                    warning_btn = WebDriverWait(driver, 2).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[span[contains(text(), '坚持提交')]]"))
                    )
                    warning_btn.click()
                except:
                    pass

                # 10. 等待结果
                # 检测是否出现 "我要抽题" 按钮（代表AC了并弹出了成功框）
                # 或者检测 "运行结果" Tab 中的错误信息
                print("等待判题结果...")
                time.sleep(3) 

                try:
                    # 检查是否有成功进入下一题的按钮 (出现在成功弹窗中)
                    next_problem_btn = driver.find_elements(By.XPATH, "//button[span[contains(text(), '我要抽题')]]")
                    
                    if next_problem_btn and next_problem_btn[0].is_displayed():
                        print("题目通过 (AC)！进入下一题...")
                        next_problem_btn[0].click()
                        solved = True
                        time.sleep(2)
                        break
                    else:
                        raise Exception("未检测到通过弹窗")
                        
                except:
                    # 未通过，获取错误信息
                    print("未通过，获取错误日志...")
                    
                    # 切换到“运行结果” Tab
                    try:
                        result_tab = driver.find_element(By.XPATH, "//div[@data-name='result']")
                        result_tab.click()
                    except:
                        print("无法切换到运行结果标签")

                    # 获取错误详情 Textarea
                    try:
                        # 等待错误信息加载
                        time.sleep(1)
                        # 页面中可能有两个 textarea (输入代码的和输出错误的)，输出错误的在 tab-pane 里
                        # 根据 HTML: 详细信息后面的 textarea
                        error_area = driver.find_element(By.XPATH, "//div[contains(text(), '详细信息')]/following-sibling::div//textarea")
                        error_msg = error_area.get_attribute('value')
                        
                        if not error_msg:
                            # 可能是 Wrong Answer 但没有详细报错，或者编译错误
                            # 尝试获取表格中的状态
                            status = driver.find_element(By.XPATH, "//td[@data-col-key='status']").text
                            error_msg = f"运行状态: {status} (无详细日志，请检查逻辑)"
                        
                        print(f"错误信息: {error_msg[:50]}...")
                        
                        # AI 修复
                        print("请求 AI 修复代码...")
                        new_code = get_ai_solution(problem_prompt, current_code, error_msg)
                        current_code = new_code
                        
                        # 切回题目详情或者是直接在当前页面修改代码 (通常编辑器还在)
                        # 重新填入代码
                        editor = driver.find_element(By.CSS_SELECTOR, ".cm-content")
                        action = ActionChains(driver)
                        action.click(editor).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).send_keys(Keys.BACK_SPACE).perform()
                        driver.execute_script("arguments[0].innerText = arguments[1];", editor, current_code)
                        editor.send_keys(" ") 
                        editor.send_keys(Keys.BACK_SPACE)
                        
                        # 重新循环提交
                        continue
                        
                    except Exception as e:
                        print(f"获取错误结果失败: {e}")
                        # 极少数情况可能卡死，跳出内层循环尝试下一题或手动干预
                        break

    except Exception as e:
        print(f"程序运行出错: {e}")
    finally:
        # 保持浏览器开启以便查看
        input("按回车键结束程序并关闭浏览器...")
        driver.quit()

if __name__ == "__main__":
    main()