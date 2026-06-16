"""
test_oj_flow.py — 完整 OJ 流程测试脚本（含 AI + 弹窗处理）
镜像 OJ_GUI 的提交逻辑，用于验证"已AC但未提交"弹窗 + 通关弹窗流程。
"""
import time
import re
import json
import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from openai import OpenAI
import requests

# ================= 配置（从 oj_config.json 读取，与 OJ_GUI 一致） =================
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oj_config.json")
def load_oj_config():
    default = {
        "oj_url": "http://oj.dhu.edu.cn",
        "username": "weishi_corroding@163.com",
        "password": "Dh_411411",
        "api_key": "sk-e00efab0672a406e9a1bf9b865145064",
        "api_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
    }
    if not os.path.exists(CONFIG_FILE):
        print(f"[配置] 未找到 {CONFIG_FILE}，使用默认配置")
        return default
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        for k, v in default.items():
            cfg.setdefault(k, v)
        print(f"[配置] 已加载: {CONFIG_FILE}")
        return cfg
    except Exception as e:
        print(f"[配置] 加载失败: {e}，使用默认配置")
        return default

config = load_oj_config()
# 规范化 OJ_URL：移除 hash 部分（如 /#/user/index），只保留裸地址
OJ_URL = config["oj_url"].split("/#")[0].rstrip("/")
if not OJ_URL:
    OJ_URL = "http://oj.dhu.edu.cn"
USERNAME = config["username"]
PASSWORD = config["password"]
EXAM_ID = "410"
CLASS_ID = 263

os.environ['DEEPSEEK_API_KEY'] = config["api_key"]
client = OpenAI(
    api_key=config["api_key"],
    base_url=config["api_url"]
)
AI_MODEL = config["model"]
print(f"[配置] AI 模型: {AI_MODEL}")

# ================= 工具函数 =================

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

def debug_dialogs(driver, label=""):
    """扫描页面所有已知弹窗/按钮/状态元素并输出"""
    print(f"\n  --- [调试] {label} ---")
    checks = [
        ("已AC但未提交(文本)", "//*[contains(text(), '已AC') and contains(text(), '未提交')]"),
        ("已AC但未提交(完整)", "//p[contains(text(), '已AC')]"),
        ("我要抽题按钮", "//button[span[contains(text(), '我要抽题')]]"),
        ("已通关文本", "//div[contains(text(), '已通关')]"),
        ("提交代码按钮", "//button[span[contains(text(), '提交代码')]]"),
        ("n-dialog弹窗", "//div[contains(@class, 'n-dialog')]"),
        ("dialog提交按钮", "//div[contains(@class, 'n-dialog__action')]//button[span[contains(text(), '提交')]]"),
        ("坚持提交按钮", "//button[span[contains(text(), '坚持提交')]]"),
        ("结果tab", "//div[@data-name='result']"),
        ("状态列", "//td[@data-col-key='status']"),
    ]
    for name, xpath in checks:
        try:
            els = driver.find_elements(By.XPATH, xpath)
            if els:
                for i, el in enumerate(els[:2]):
                    visible = el.is_displayed() if el.is_displayed() else False
                    text = (el.text or el.get_attribute('value') or '')[:60]
                    print(f"    [FOUND] {name}[{i}]: visible={visible} text='{text}'")
            else:
                print(f"    [NONE]  {name}")
        except Exception as e:
            print(f"    [ERR]   {name}: {e}")
    # 输出当前 URL
    try:
        print(f"    URL: {driver.current_url}")
    except:
        pass
    print("")

def wait_and_click(driver, by, value, timeout=10):
    try:
        element = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, value)))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.2)
        element.click()
        return element
    except Exception as e:
        log(f"  点击失败 ({timeout}s 超时): {e}")
        return None

def wait_and_input(driver, by, value, text, timeout=10, press_enter=False):
    element = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
    element.clear()
    element.send_keys(text)
    if press_enter:
        element.send_keys(Keys.ENTER)

# ================= AI =================

def get_ai_solution(prompt_content, current_code=None, error_msg=None):
    """调用 DeepSeek 生成/修复代码（与 OJ_GUI 一致）"""
    system_prompt = (
        "你是一个C++算法竞赛专家。请直接输出可编译的完整C++代码(使用MinGW标准)，"
        "不要包含markdown标记(如```cpp)，不要包含任何解释性文字，不要输出注释。"
        "参考题解仅供思路参考，保留核心功能即可，不要照搬其结构。"
    )
    user_content = prompt_content
    if error_msg:
        user_content = (
            f"我之前的代码如下：\n{current_code}\n\n"
            f"报错信息如下：\n{error_msg}\n\n"
            f"请根据报错修正代码，直接输出修正后的完整代码。"
        )
    mode = "修复" if error_msg else "生成"
    log(f"请求 AI {mode}代码...")
    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            stream=False
        )
        content = response.choices[0].message.content
        content = content.replace("```cpp", "").replace("```", "").strip()
        log(f"AI 代码{mode}完成")
        return content
    except Exception as e:
        log(f"AI 调用失败: {e}")
        return None

# ================= 题目获取 =================

def get_problem_via_api(driver):
    """使用 requests 获取题目数据（含参考题解），失败则 fallback 到 DOM 提取"""
    try:
        # 等待 URL 中包含 problems/ 或 training/（最多10秒）
        url = ""
        for _ in range(10):
            url = driver.current_url
            if 'problems/' in url or 'training/' in url:
                break
            time.sleep(1)
        log(f"当前 URL: {url}")

        # 尝试从 URL 提取 problem_id (exam模式: problems/123)
        match = re.search(r'problems/(\d+)', url)
        is_training = 'training/' in url

        # 提取 token
        token_raw = driver.execute_script(
            "return localStorage.getItem('DHU_OJ_ACCESS_TOKEN_USER');"
        )
        if not token_raw:
            log("未找到 Token")
            return None

        try:
            token_data = json.loads(token_raw)
            token_value = token_data.get("value")
        except:
            token_value = token_raw

        cookies = {}
        for c in driver.get_cookies():
            if c['name'] == 'JSESSIONID':
                cookies['JSESSIONID'] = c['value']
                break

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Authorization": token_value,
            "Content-Type": "application/json",
            "Origin": "https://oj.dhu.edu.cn",
            "Referer": "https://oj.dhu.edu.cn/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0",
        }

        if match:
            # ---- Exam 模式: 通过 API 获取 ----
            problem_id = match.group(1)
            payload = {"examId": EXAM_ID, "id": str(problem_id), "classId": CLASS_ID}
            log(f"请求 API (examId={EXAM_ID}, problemId={problem_id}, classId={CLASS_ID})...")
            resp = requests.post(
                "https://oj.dhu.edu.cn/api/problems/getProblemByIdAndExamIdAndClassId",
                headers=headers, cookies=cookies, json=payload, timeout=15,
            )
            resp.raise_for_status()
            res_json = resp.json()
            if res_json.get("code") == 0:
                data = res_json.get("data", {})
                log(f"题目: {data.get('title')}")
                source_code = data.get("sourceCode", "")
                problem_prompt = (
                    f"标题: {data.get('title')}\n"
                    f"描述: {data.get('description')}\n"
                    f"输入要求: {data.get('inputRequirement')}\n"
                    f"输出要求: {data.get('outputRequirement')}\n"
                    f"样例输入: {data.get('sampleInput')}\n"
                    f"样例输出: {data.get('sampleOuput')}"
                )
                if source_code:
                    problem_prompt += (
                        f"\n参考题解:\n{source_code}\n"
                        f"[注] 以上解答仅供参考，保留核心功能即可，无需包含注释。"
                    )
                    log("已包含参考题解")
                return problem_prompt
            else:
                log(f"API 异常: {res_json}")
        elif is_training:
            # ---- Training 模式: 通过 DOM 提取 ----
            log("Training页面，使用DOM提取题目...")
            try:
                # 找题目描述区域
                desc_div = driver.find_element(By.CSS_SELECTOR, ".n-tab-pane:not([style*='display: none'])")
                text = desc_div.get_attribute('innerText')
                # 提取标题
                title_el = driver.find_elements(By.CSS_SELECTOR, "h1, h2, h3, .n-page-header__title")
                title = title_el[0].text if title_el else "未知题目"
                log(f"题目(从DOM): {title}")
                return f"标题: {title}\n描述: {text[:3000]}"
            except Exception as e:
                log(f"DOM提取失败: {e}")

        # API + DOM 都失败
        log("获取题目失败")
        return None
    except Exception as e:
        log(f"获取题目异常: {e}")
        return None

# ================= 页面操作 =================

def handle_draw_modal(driver):
    """处理抽题弹窗（带详细调试信息）"""
    print(f"\n  --- [调试] 进入 handle_draw_modal ---")
    try:
        # 1. 扫描所有弹窗/卡片
        modals = driver.find_elements(By.CSS_SELECTOR, ".n-card.n-modal")
        print(f"    n-card.n-modal 数量: {len(modals)}")
        for i, m in enumerate(modals):
            print(f"      modal[{i}]: display={m.is_displayed()}, text='{(m.text or '')[:80]}'")

        all_n_modals = driver.find_elements(By.CSS_SELECTOR, ".n-modal")
        print(f"    .n-modal 数量: {len(all_n_modals)}")
        for i, m in enumerate(all_n_modals):
            print(f"      n-modal[{i}]: display={m.is_displayed()}, text='{(m.text or '')[:80]}'")

        modal = driver.find_elements(By.CSS_SELECTOR, ".n-card.n-modal")
        if not modal:
            print("    未找到 n-card.n-modal，尝试 .n-dialog")
            modal = driver.find_elements(By.CSS_SELECTOR, ".n-dialog")
            if not modal:
                print("    无抽题弹窗，返回 False")
                print(f"  --- [调试] handle_draw_modal 结束: 无弹窗 ---\n")
                return False

        log("检测到抽题弹窗")

        # 2. 尝试点击 "切换" 标签
        try:
            switch_tab = driver.find_element(By.XPATH, "//div[contains(text(), '切换到题目类别')]")
            print(f"    找到'切换到题目类别': text='{switch_tab.text}' display={switch_tab.is_displayed()}")
            switch_tab.click()
            time.sleep(0.3)
        except Exception as e:
            print(f"    无'切换到题目类别'或点击失败: {e}")

        # 3. 查看选择框
        selections = driver.find_elements(By.CSS_SELECTOR, ".n-base-selection")
        print(f"    .n-base-selection 总数: {len(selections)}")
        for i, s in enumerate(selections):
            print(f"      sel[{i}]: display={s.is_displayed()}, size={s.size}, text='{(s.text or '')[:40]}'")

        # 4. 尝试打开下拉
        sel_to_click = None
        for s in selections:
            if s.is_displayed() and s.size['width'] > 0 and s.size['height'] > 0:
                sel_to_click = s
                break
        if not sel_to_click and selections:
            sel_to_click = selections[0]

        if sel_to_click:
            print(f"    点击选择框")
            try:
                sel_to_click.click()
            except:
                print("    正常点击失败，尝试 JS 点击")
                driver.execute_script("arguments[0].click();", sel_to_click)
            time.sleep(0.5)

            # 5. 检查 portal 中的选项（Naive UI 渲染到 v-binder-follower-container）
            options = driver.find_elements(By.CSS_SELECTOR, ".n-select-menu .n-base-select-option")
            print(f"    portal 选项数量: {len(options)}")
            if not options:
                options = driver.find_elements(By.XPATH,
                    "//div[contains(@class, 'n-base-select-option') and contains(@class, 'n-base-select-option--show-checkmark')]")
                print(f"    fallback 选项数量: {len(options)}")

            for i, o in enumerate(options):
                print(f"      option[{i}]: text='{o.text}', display={o.is_displayed()}, tag={o.tag_name}, classes={o.get_attribute('class')[:80]}")

            if options:
                print(f"    选择第一个选项: '{options[0].text}'")
                # Naive UI n-select 需要 mousedown 事件，用 ActionChains 模拟完整鼠标操作
                try:
                    from selenium.webdriver.common.action_chains import ActionChains
                    actions = ActionChains(driver)
                    actions.move_to_element(options[0])
                    actions.pause(0.1)
                    actions.click()
                    actions.perform()
                    print(f"    使用 ActionChains 点击成功")
                except:
                    # 回退：JS 派发 mousedown 事件
                    driver.execute_script("""
                        arguments[0].dispatchEvent(new MouseEvent('mousedown', {
                            bubbles: true, cancelable: true, view: window
                        }));
                    """, options[0])
                    print(f"    使用 JS mousedown 回退")
                time.sleep(0.5)
            else:
                print("    [警告] 无任何选项可选！")
        else:
            print("    [警告] 无可用的 .n-base-selection！")

        # 6. 点击 "我要抽题"
        print("    点击'我要抽题'...")
        draw_btn = driver.find_elements(By.XPATH, "//button[span[contains(text(), '我要抽题')]]")
        print(f"    我要抽题按钮数量: {len(draw_btn)}")
        for i, b in enumerate(draw_btn):
            print(f"      btn[{i}]: display={b.is_displayed()}, text='{b.text}'")

        if draw_btn:
            try:
                draw_btn[0].click()
            except:
                driver.execute_script("arguments[0].click();", draw_btn[0])
            log("已点击'我要抽题'")
            time.sleep(3)

            # 7. 检查点击后是否仍然有弹窗（选择类别失败的标志）
            still_modal = driver.find_elements(By.CSS_SELECTOR, ".n-card.n-modal")
            if still_modal:
                print(f"    [警告] 点击后仍有 {len(still_modal)} 个弹窗！内容: '{still_modal[0].text[:100]}'")
                print(f"    [警告] 类别选择可能无效，弹窗未关闭")
                debug_dialogs(driver, "抽题后仍有弹窗")
            else:
                log("弹窗已关闭")
        else:
            print("    [警告] 未找到'我要抽题'按钮")
            debug_dialogs(driver, "我要抽题按钮缺失")

        print(f"  --- [调试] handle_draw_modal 结束 ---\n")
        return True
    except Exception as e:
        log(f"抽题弹窗异常: {e}")
        import traceback
        traceback.print_exc()
        print(f"  --- [调试] handle_draw_modal 异常结束 ---\n")
        return False

def fill_code_editor(driver, code):
    """填入代码到编辑器（多方法回退）"""
    # 方法 1: JS 注入
    try:
        all_editors = driver.find_elements(By.CSS_SELECTOR, ".cm-editor")
        editor_outer = None
        for e in all_editors:
            if e.is_displayed() and e.size['width'] > 0 and e.size['height'] > 0:
                editor_outer = e
                break
        if not editor_outer:
            editor_outer = all_editors[0] if all_editors else None
        if not editor_outer:
            raise Exception("未找到 .cm-editor")

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", editor_outer)
        time.sleep(0.3)
        try:
            editor_outer.click()
        except:
            driver.execute_script("arguments[0].click();", editor_outer)
        time.sleep(0.2)

        all_contents = driver.find_elements(By.CSS_SELECTOR, ".cm-content")
        cm_content = None
        for c in all_contents:
            if c.is_displayed() and c.size['width'] > 0:
                cm_content = c
                break
        if not cm_content:
            cm_content = all_contents[0] if all_contents else None
        if not cm_content:
            raise Exception("未找到 .cm-content")

        driver.execute_script("""
            var el = arguments[0];
            el.innerText = arguments[1];
            el.dispatchEvent(new Event('input', {bubbles: true, cancelable: true}));
        """, cm_content, code)
        log("代码填入成功 (JS注入)")
        return True
    except Exception as e:
        log(f"JS注入失败: {e}")

    # 方法 2: pyperclip
    try:
        import pyperclip
        pyperclip.copy(code)
        editor = driver.find_element(By.CSS_SELECTOR, ".cm-editor")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", editor)
        editor.click()
        time.sleep(0.2)
        ActionChains(driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
        time.sleep(0.2)
        ActionChains(driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
        log("代码填入成功 (剪贴板)")
        return True
    except:
        pass

    # 方法 3: send_keys
    try:
        content = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".cm-content"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", content)
        content.click()
        content.send_keys(Keys.CONTROL, 'a')
        content.send_keys(code)
        log("代码填入成功 (send_keys)")
        return True
    except:
        pass

    return False

def select_mingw(driver):
    """选择 MinGW 编译器"""
    try:
        selections = driver.find_elements(By.CSS_SELECTOR, ".n-base-selection")
        for sel in selections:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", sel)
                sel.click()
                time.sleep(0.2)
                mingw_opts = driver.find_elements(By.XPATH, "//div[contains(text(), 'MinGW')]")
                if mingw_opts:
                    mingw_opts[0].click()
                    log("已选择 MinGW 编译器")
                    return True
            except:
                continue
        return False
    except Exception as e:
        log(f"选择编译器失败: {e}")
        return False

# ================= 主流程 =================

def main():
    print(f"\n{'='*60}")
    print("  OJ 完整流程测试（AI + 弹窗处理）")
    print(f"{'='*60}\n")

    driver = webdriver.Edge()
    driver.maximize_window()

    try:
        # ---- 1. 登录 ----
        log("登录...")
        driver.get(OJ_URL)
        wait_and_input(driver, By.CSS_SELECTOR, "input[placeholder='登录账号']", USERNAME)
        wait_and_input(driver, By.CSS_SELECTOR, "input[placeholder='请输入密码']", PASSWORD, press_enter=True)
        log("登录提交完成")
        time.sleep(3)

        # ---- 2. 考试列表 ----
        log("进入考试列表...")
        try:
            wait_and_click(driver, By.XPATH, "//a[@href='#/user/exam-list']", timeout=5)
        except:
            driver.get(f"{OJ_URL}/#/user/exam-list")
        time.sleep(2)

        # ---- 3. 参加第一个考试 ----
        log("参加考试...")
        buttons = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//button[span[contains(text(), '参加')]]"))
        )
        buttons[0].click()
        time.sleep(2)

        # ---- 4. 开始做题 ----
        log("开始做题...")
        wait_and_click(driver, By.XPATH, "//button[span[contains(text(), '开始做题')]]")
        time.sleep(3)

        # ---- 主循环（逐题解答） ----
        problem_count = 0
        while True:
            problem_count += 1
            print(f"\n{'='*60}")
            print(f"  第 {problem_count} 题")
            print(f"{'='*60}")

            # 5. 处理抽题弹窗
            handle_draw_modal(driver)
            # 等待题目页面加载完成
            log("等待题目页面加载...")
            time.sleep(3)

            # 6. 获取题目
            log("获取题目...")
            problem_prompt = get_problem_via_api(driver)
            if not problem_prompt:
                log("获取题目失败，终止")
                break

            # 7. AI 生成代码
            log("AI 生成代码...")
            current_code = get_ai_solution(problem_prompt)
            if not current_code:
                log("AI 生成失败，跳过本题")
                continue

            # 8. 填入代码
            if not fill_code_editor(driver, current_code):
                log("填入代码失败")

            # 9. 选择 MinGW
            select_mingw(driver)

            # ---- 10. 提交 + 弹窗处理循环（镜像 OJ_GUI） ----
            solved = False
            submitted = False
            while not solved:
                if not submitted:
                    log("提交代码中...")
                    btn = wait_and_click(driver, By.XPATH, "//button[span[contains(text(), '提交代码')]]")
                    if not btn:
                        log("提交按钮未找到")
                        break

                    # 确认弹窗
                    try:
                        confirm = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, "//div[@class='n-dialog__action']//button[span[contains(text(), '提交')]]"))
                        )
                        confirm.click()
                    except:
                        pass

                    # 抄袭警告
                    try:
                        warning = WebDriverWait(driver, 2).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[span[contains(text(), '坚持提交')]]"))
                        )
                        warning.click()
                    except:
                        pass

                    submitted = True

                # 等待判题
                log("等待判题结果...")
                time.sleep(3)

                # ---- 结果检查（与 OJ_GUI 对齐） ----

                # A. 等待"已AC但未提交"弹窗（最长 30s）
                log("检查'已AC但未提交'弹窗（等待30s）...")
                debug_dialogs(driver, "等待弹窗前")
                ac_submit_btn = wait_and_click(driver,
                    By.XPATH,
                    "//div[contains(@class, 'n-dialog__action')]//button[span[contains(text(), '提交')]]",
                    timeout=30)

                if ac_submit_btn:
                    log("[OK] 检测到'已AC但未提交'弹窗 → 已点击提交")
                    debug_dialogs(driver, "点击提交后")

                    # 点击提交后可能出现抄袭警告
                    try:
                        warn = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[span[contains(text(), '坚持提交')]]"))
                        )
                        warn.click()
                        log("已点击'坚持提交'")
                        debug_dialogs(driver, "点击坚持提交后")
                    except:
                        log("无抄袭警告弹窗")
                        debug_dialogs(driver, "无抄袭警告时")

                    time.sleep(2)
                else:
                    log("超时：30s内未出现'已AC但未提交'弹窗")
                    debug_dialogs(driver, "弹窗超时后")

                # B. "我要抽题"按钮（通关弹窗）
                log("检查'我要抽题'弹窗...")
                next_btn = driver.find_elements(By.XPATH, "//button[span[contains(text(), '我要抽题')]]")
                if next_btn and next_btn[0].is_displayed():
                    log("[AC] AC！进入下一题...")
                    next_btn[0].click()
                    solved = True
                    time.sleep(2)
                    debug_dialogs(driver, "点击我要抽题后")
                    handle_draw_modal(driver)
                    break
                else:
                    log("未找到'我要抽题'弹窗")
                    if next_btn:
                        log(f"  找到{len(next_btn)}个元素但不可见")

                # C. "已通关"（全部完成）
                log("检查'已通关'...")
                cleared = driver.find_elements(By.XPATH, "//div[contains(text(), '已通关')]")
                if cleared:
                    log("[AC] 已通关所有题目！")
                    solved = True
                    break
                else:
                    log("未找到'已通关'")

                # D. 仍在排队/判题中 → 切到结果tab看状态
                log("检查判题状态...")
                try:
                    rt = driver.find_element(By.XPATH, "//div[@data-name='result']")
                    rt.click()
                    log("已切换到结果tab")
                    time.sleep(0.5)
                    se = driver.find_elements(By.XPATH, "//td[@data-col-key='status']")
                    if se:
                        raw_text = se[0].text
                        log(f"结果tab状态: '{raw_text}'")
                        st = raw_text.lower()
                        if 'queue' in st or '等待' in st or 'judg' in st:
                            log(f"  仍在排队/判题中，继续等待...")
                            continue
                        else:
                            log(f"  状态已就绪: '{raw_text}'")
                    else:
                        log("结果tab中无状态列（可能尚未开始判题）")
                        debug_dialogs(driver, "结果tab无状态时")
                except Exception as e:
                    log(f"切到结果tab失败: {e}")
                    debug_dialogs(driver, "结果tab异常")

                # E. 未通过 → AI 修复
                log("未通过所有检查，进入AI修复流程")
                debug_dialogs(driver, "开始AI修复前")
                log("未通过，获取错误信息...")
                try:
                    rt = driver.find_element(By.XPATH, "//div[@data-name='result']")
                    rt.click()
                except:
                    pass

                try:
                    time.sleep(1)
                    se = driver.find_elements(By.XPATH, "//td[@data-col-key='status']")
                    if se:
                        log(f"状态: {se[0].text}")

                    err_area = driver.find_elements(By.XPATH,
                        "//div[contains(text(), '详细信息')]/following-sibling::div//textarea")
                    err_msg = ""
                    if err_area:
                        err_msg = err_area[0].get_attribute('value')
                    if not err_msg and se:
                        err_msg = f"状态: {se[0].text}"
                    elif not err_msg:
                        err_msg = "未知错误"

                    log(f"错误: {err_msg[:80]}")
                    log("请求 AI 修复...")
                    new_code = get_ai_solution(problem_prompt, current_code, err_msg)
                    if new_code:
                        current_code = new_code
                        # 替换编辑器内容
                        try:
                            editor = driver.find_element(By.CSS_SELECTOR, ".cm-content")
                            action = ActionChains(driver)
                            action.click(editor).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).send_keys(Keys.BACK_SPACE).perform()
                            driver.execute_script("arguments[0].innerText = arguments[1];", editor, current_code)
                            editor.send_keys(" ")
                            editor.send_keys(Keys.BACK_SPACE)
                        except:
                            fill_code_editor(driver, current_code)
                        submitted = False
                    continue
                except Exception as e:
                    log(f"获取错误失败: {e}")
                    break

            if solved:
                log("本题完成，继续下一题...")
                continue
            else:
                log("本题异常终止")
                break

    except Exception as e:
        log(f"主流程异常: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n{'='*60}")
        print("  测试完成")
        print(f"{'='*60}")
        try:
            input("\n按回车关闭浏览器...")
        except EOFError:
            pass
        driver.quit()

if __name__ == "__main__":
    main()
