"""
test_oj_flow.py — 精简版：仅测试 登录 → 参加 → 开始答题 → 抽题弹窗处理
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

# ================= 配置 =================
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oj_config.json")
with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)

OJ_URL = config["oj_url"].split("/#")[0].rstrip("/") or "http://oj.dhu.edu.cn"
USERNAME = config["username"]
PASSWORD = config["password"]

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

def debug_dialogs(driver, label=""):
    print(f"\n  --- [调试] {label} ---")
    checks = [
        ("切换类别文本", "//*[contains(text(), '切换到题目类别')]"),
        ("恭喜通关文本", "//*[contains(text(), '恭喜您，已通关')]"),
        ("进行类别选择", "//*[contains(text(), '进行类别选择')]"),
        ("选择框.n-select", ".n-select"),
        ("选择框.n-base-selection", ".n-base-selection"),
        ("下拉菜单portal", ".n-select-menu"),
        ("选项(.n-select-menu .n-base-select-option)", ".n-select-menu .n-base-select-option"),
        ("我要抽题按钮", "//button[span[contains(text(), '我要抽题')]]"),
        ("暂且返回按钮", "//button[span[contains(text(), '暂且返回')]]"),
        ("n-card.n-modal", ".n-card.n-modal"),
    ]
    for name, sel in checks:
        try:
            if sel.startswith("//") or sel.startswith(".//"):
                els = driver.find_elements(By.XPATH, sel)
            else:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
            if els:
                for i, el in enumerate(els[:3]):
                    visible = el.is_displayed()
                    text = (el.text or '')[:60]
                    rect = el.rect
                    print(f"    [FOUND] {name}[{i}]: visible={visible} text='{text}' pos=({rect['x']:.0f},{rect['y']:.0f}) size={rect['width']:.0f}x{rect['height']:.0f}")
            else:
                print(f"    [NONE]  {name}")
        except Exception as e:
            print(f"    [ERR]   {name}: {e}")
    print(f"    URL: {driver.current_url}")
    print("")

def handle_draw_modal(driver):
    """处理抽题弹窗（带详细调试信息）"""
    print(f"\n  === [调试] 进入 handle_draw_modal ===")
    try:
        # 1. 弹窗检测
        n_modal = driver.find_elements(By.CSS_SELECTOR, ".n-card.n-modal")
        print(f"    n-card.n-modal: {len(n_modal)}")
        for m in n_modal:
            header = m.find_element(By.CSS_SELECTOR, '.n-card-header__main').text if m.find_elements(By.CSS_SELECTOR, '.n-card-header__main') else '?'
            print(f"      弹窗标题: '{header}' 内容(前80): '{(m.text or '')[:80]}'")

        if not n_modal:
            n_dialog = driver.find_elements(By.CSS_SELECTOR, ".n-dialog")
            if not n_dialog:
                print("    无弹窗，返回")
                return False
            print(f"    使用 n-dialog 替代")

        log("检测到抽题弹窗")

        # 2. 找到所有选择框并逐一处理
        selectors = driver.find_elements(By.CSS_SELECTOR, ".n-select .n-base-selection")
        print(f"    弹窗内选择框总数: {len(selectors)}")
        for idx, sel in enumerate(selectors):
            print(f"      sel[{idx}]: display={sel.is_displayed()} text='{sel.text[:40]}' pos=({sel.rect['x']:.0f},{sel.rect['y']:.0f})")

        for idx, sel in enumerate(selectors):
            if not sel.is_displayed():
                print(f"    sel[{idx}] 不可见，跳过")
                continue

            print(f"\n    --- 处理选择框 [{idx}]: '{sel.text[:40]}' ---")

            # 3. 打开下拉
            try:
                sel.click()
                print(f"    点击打开")
            except:
                driver.execute_script("arguments[0].click();", sel)
                print(f"    JS点击打开")
            time.sleep(0.5)

            # 4. 获取 portal 中的选项
            options = driver.find_elements(By.CSS_SELECTOR, ".n-select-menu .n-base-select-option")
            print(f"    portal选项: {len(options)}")
            for oi, o in enumerate(options):
                cls = o.get_attribute("class") or ""
                print(f"      [{oi}] text='{o.text[:50]}' visible={o.is_displayed()}")

            if not options:
                # fallback: 任意可见的 n-base-select-option
                all_opts = driver.find_elements(By.XPATH,
                    "//div[contains(@class, 'n-base-select-option') and contains(@class, 'n-base-select-option--show-checkmark')]")
                visible_opts = [o for o in all_opts if o.is_displayed()]
                print(f"    fallback选项(可见): {len(visible_opts)}")
                for oi, o in enumerate(visible_opts[:5]):
                    print(f"      [{oi}] text='{o.text[:50]}'")
                options = visible_opts

            # 5. 选择第一个有效选项
            picked = False
            for opt in options:
                if opt.is_displayed() and opt.text.strip():
                    print(f"    选择: '{opt.text[:50]}'")
                    try:
                        ac = ActionChains(driver)
                        ac.move_to_element(opt).pause(0.1).click().perform()
                        print(f"    => ActionChains.click")
                    except:
                        driver.execute_script("""
                            arguments[0].dispatchEvent(new MouseEvent('mousedown', {
                                bubbles: true, cancelable: true, view: window
                            }));
                        """, opt)
                        print(f"    => JS mousedown")
                    time.sleep(0.5)
                    picked = True
                    break

            if not picked:
                print(f"    [WARN] 选择框[{idx}] 无可用选项")

            # 检查下拉是否关闭
            still_open = driver.find_elements(By.CSS_SELECTOR, ".n-select-menu")
            if still_open:
                print(f"    [WARN] 下拉菜单未关闭")

        print(f"\n    --- 所有选择框处理完毕 ---")

        # 6. 点击"我要抽题"
        time.sleep(0.5)
        draw_btn = driver.find_elements(By.XPATH, "//button[span[contains(text(), '我要抽题')]]")
        if draw_btn and draw_btn[0].is_displayed():
            try:
                draw_btn[0].click()
            except:
                driver.execute_script("arguments[0].click();", draw_btn[0])
            log("已点击'我要抽题'")
        else:
            print(f"    [WARN] 未找到'我要抽题'按钮")
            for b in driver.find_elements(By.XPATH, "//button"):
                print(f"      button: text='{b.text[:40]}' display={b.is_displayed()}")

        time.sleep(3)

        # 7. 验证结果
        still_modal = driver.find_elements(By.CSS_SELECTOR, ".n-card.n-modal")
        if still_modal:
            print(f"    [WARN] 点击抽题后弹窗仍在，内容: '{still_modal[0].text[:100]}'")
            debug_dialogs(driver, "点击我要抽题后")
        else:
            log("[OK] 弹窗已关闭，抽题成功")

        print(f"  === [调试] handle_draw_modal 结束 ===\n")
        return True
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  === [调试] handle_draw_modal 异常结束 ===\n")
        return False

# ================= 主流程 =================

def main():
    print(f"\n{'='*60}")
    print("  OJ 抽题弹窗测试（精简版）")
    print(f"{'='*60}\n")

    driver = webdriver.Edge()
    driver.maximize_window()

    try:
        # 1. 登录
        log("登录...")
        driver.get(OJ_URL)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='登录账号']"))
        ).send_keys(USERNAME)
        pw = driver.find_element(By.XPATH, "//input[@placeholder='请输入密码']")
        pw.clear()
        pw.send_keys(PASSWORD)
        pw.send_keys(Keys.ENTER)
        log("登录提交完成")
        time.sleep(3)

        # 2. 考试列表
        log("进入考试列表...")
        try:
            driver.find_element(By.XPATH, "//a[@href='#/user/exam-list']").click()
        except:
            driver.get(f"{OJ_URL}/#/user/exam-list")
        time.sleep(2)

        # 3. 参加
        log("参加考试...")
        buttons = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//button[span[contains(text(), '参加')]]"))
        )
        buttons[0].click()
        time.sleep(2)

        # 4. 开始做题
        log("开始做题...")
        start_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[span[contains(text(), '开始做题')]]"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", start_btn)
        time.sleep(0.2)
        start_btn.click()
        time.sleep(3)

        # 5. 处理抽题弹窗（核心测试目标）
        log("处理抽题弹窗...")
        debug_dialogs(driver, "进入页面后")
        handle_draw_modal(driver)

        # 6. 等待观察
        log("测试结束，请手动检查浏览器状态")
        input("\n按回车关闭浏览器...")

    except Exception as e:
        import traceback
        traceback.print_exc()
        input("\n异常，按回车关闭...")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
