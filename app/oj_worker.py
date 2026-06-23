# -*- coding: utf-8 -*-
"""OJ 自动化 Worker（QThread）。

承载所有 Selenium + AI 主流程：登录 → 进入考试 → 抽题 → 题面获取（API 优先）→
AI/缓存生成代码 → 填入 CodeMirror → 提交 → 结果判定 → AC 后继续下一题。

GUI 侧通过 `RunPage` 创建该 worker 并桥接信号：
    log_signal      - 转发至 LogPage
    paused_signal   - 通知 RunPage 切换为"继续"按钮
    notify_signal   - PushPlus 未启用时的兜底通知（GUI 用系统托盘展示）
    finished        - QThread 自带，结束时清理 UI
"""

import json
import os
import random
import re
import time

from PyQt5.QtCore import QThread, pyqtSignal

import requests
from openai import OpenAI
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from app.constants import DECOY_HEADERS, SOLUTIONS_FILE


class OJWorker(QThread):
    log_signal = pyqtSignal(str, str)
    finished = pyqtSignal()
    paused_signal = pyqtSignal()  # 进入暂停时发射，让 GUI 切换为'继续'按钮
    notify_signal = pyqtSignal(str, str)  # 需要用户注意时发射（标题, 内容）

    def __init__(self, config, delay_seconds=0, parent=None):
        super().__init__(parent)
        self.config = config
        self.delay_seconds = delay_seconds
        self._stop_flag = False
        self._pause_flag = False
        self._persist_submit = True  # 是否自动点击'坚持提交'，由 GUI 同步
        self._last_problem_data = None  # API 返回的题目原始数据，第 2 次尝试时复用
        self._last_problem_id = None  # 当前题目 id，用于读写本地题解缓存
        self._last_cached_code = None  # 本题命中本地缓存时的原始代码（不含反查重头文件）
        self._solutions_cache = self._load_solutions()  # {problem_id: {code, title, savedAt}}
        self.driver = None
        self._pushplus_token = config.get("pushplus_token", "") if config.get("pushplus_enabled") else ""
        self._pushplus_enabled = config.get("pushplus_enabled", False)

    def stop(self):
        self._stop_flag = True
        self._pause_flag = False  # 解除暂停以让 _wait_if_paused 立即退出
        # 立即关闭浏览器，打断 Selenium 阻塞操作
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

    def resume(self):
        """从暂停状态恢复（清除 pause flag，让 _wait_if_paused 退出）"""
        self._pause_flag = False

    def set_persist_submit(self, value: bool):
        """GUI 在 checkbox 切换时同步过来"""
        self._persist_submit = bool(value)

    def _wait_if_paused(self):
        """阻塞直到 _pause_flag=False 或 _stop_flag=True"""
        while self._pause_flag and not self._stop_flag:
            time.sleep(0.1)

    def log(self, msg, level="info"):
        self.log_signal.emit(msg, level)

    def _send_pushplus_notification(self, title, content):
        """通过 PushPlus 推送通知到微信（静默失败，不抛异常）。
        若 PushPlus 未启用，则改为发射 notify_signal 由 GUI 展示原生通知。
        """
        if not self._pushplus_enabled or not self._pushplus_token:
            # 未启用 PushPlus → 用 Windows 原生通知代替
            self.notify_signal.emit(title, content)
            return
        try:
            resp = requests.post(
                "https://www.pushplus.plus/send",
                json={
                    "token": self._pushplus_token,
                    "title": title,
                    "content": content,
                },
                timeout=10
            )
            if resp.status_code == 200:
                self.log(f"PushPlus 通知已发送: {title}", "system")
            else:
                self.log(f"PushPlus 通知发送失败: HTTP {resp.status_code}", "warning")
        except Exception as e:
            self.log(f"PushPlus 通知异常: {e}", "warning")

    def run(self):
        try:
            self._run_oj()
        except Exception as e:
            self.log(f"程序异常: {e}", "error")
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            self.finished.emit()

    def _handle_draw_modal(self, driver):
        """处理抽题弹窗：检测弹窗 → 选择所有下拉框 → 点击抽题（含JS回退 + portal检测）"""
        try:
            modal = driver.find_elements(By.CSS_SELECTOR, ".n-card.n-modal")
            if not modal:
                modal = driver.find_elements(By.CSS_SELECTOR, ".n-dialog")
                if not modal:
                    return False

            self.log("检测到抽题弹窗，自动选择选项...", "system")

            # 找到所有选择框并逐一选择第一个选项
            selectors = driver.find_elements(By.CSS_SELECTOR, ".n-select .n-base-selection")
            for sel in selectors:
                if not sel.is_displayed():
                    continue

                # 打开下拉（若被拦截则用 JS 回退）
                try:
                    sel.click()
                except:
                    driver.execute_script("arguments[0].click();", sel)
                time.sleep(0.5)

                # 获取 portal 中的选项
                options = driver.find_elements(By.CSS_SELECTOR, ".n-select-menu .n-base-select-option")
                if not options:
                    options = [o for o in driver.find_elements(By.XPATH,
                        "//div[contains(@class, 'n-base-select-option') and contains(@class, 'n-base-select-option--show-checkmark')]")
                        if o.is_displayed()]

                # 选择第一个可见有文本的选项
                for opt in options:
                    if opt.is_displayed() and opt.text.strip():
                        self.log(f"选择: {opt.text[:40]}", "info")
                        try:
                            ActionChains(driver).move_to_element(opt).pause(0.1).click().perform()
                        except:
                            driver.execute_script("""
                                arguments[0].dispatchEvent(new MouseEvent('mousedown', {
                                    bubbles: true, cancelable: true, view: window
                                }));
                            """, opt)
                        time.sleep(0.3)
                        break

            # 点击"我要抽题"
            time.sleep(0.3)
            draw_btn = driver.find_elements(By.XPATH, "//button[span[contains(text(), '我要抽题')]]")
            if draw_btn:
                try:
                    draw_btn[0].click()
                except:
                    driver.execute_script("arguments[0].click();", draw_btn[0])
                self.log("已点击'我要抽题'", "success")
            else:
                self.log("未找到'我要抽题'按钮", "warning")

            time.sleep(2)

            # 验证弹窗已关闭
            still_modal = driver.find_elements(By.CSS_SELECTOR, ".n-card.n-modal")
            if still_modal:
                self.log("抽题后弹窗未关闭（可能类别选择无效）", "warning")
            else:
                self.log("抽题弹窗已关闭", "success")
            return True
        except Exception as e:
            self.log(f"抽题弹窗处理异常: {e}", "warning")
            return False

    def _handle_persist_submit_warning(self, timeout=3):
        """检测'坚持提交'按钮（抄袭警告）。
        返回值:
            'auto_clicked'   - 自动点击成功
            'paused_resumed' - 用户暂停后已恢复，由 _recover_after_resume 处理后续
            'none'           - 无警告
        """
        try:
            warn = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, "//button[span[contains(text(), '坚持提交')]]"))
            )
        except:
            return 'none'

        if self._persist_submit:
            try:
                warn.click()
            except:
                self.driver.execute_script("arguments[0].click();", warn)
            self.log("已点击'坚持提交'", "success")
            time.sleep(1)
            return 'auto_clicked'

        # 不勾选 → 暂停等待用户处理
        self.log("⏸ 检测到抄袭警告，已暂停。请在浏览器中手动处理后点击'继续'。", "warning")
        self._send_pushplus_notification(
            "OJ自动化 - 抄袭警告",
            f"检测到抄袭警告，需要您手动处理。\n\n"
            f"请在浏览器中手动处理（可改写代码后自行提交），\n"
            f"然后在 OJ Helper 中点击「继续」恢复自动流程。"
        )
        self._pause_flag = True
        self.paused_signal.emit()
        self._wait_if_paused()
        if self._stop_flag:
            return 'none'
        self.log("▶ 用户已点击继续，开始容错恢复...", "system")
        return 'paused_resumed'

    def _recover_after_resume(self):
        """用户点'继续'后，根据当前 DOM 状态把流程带回标准循环。
        返回:
            'next_problem' - 已进入下一题或抽题成功，应跳出内层循环
            'done'         - 已通关，整个外层循环结束
            'retry_outer'  - 应让内层循环再跑一轮结果检查
        """
        d = self.driver
        time.sleep(0.5)

        # 通关弹窗的'我要抽题'按钮还在
        try:
            next_btn = d.find_elements(By.XPATH, "//button[span[contains(text(), '我要抽题')]]")
            if next_btn and next_btn[0].is_displayed():
                self.log("[恢复] 通关弹窗仍在，自动点击'我要抽题'", "info")
                try:
                    next_btn[0].click()
                except:
                    d.execute_script("arguments[0].click();", next_btn[0])
                time.sleep(2)
                self._handle_draw_modal(d)
                return 'next_problem'
        except:
            pass

        # 已通关全部题目
        try:
            if d.find_elements(By.XPATH, "//div[contains(text(), '已通关')]"):
                self.log("[恢复] 检测到已通关", "success")
                return 'done'
        except:
            pass

        # 抽题弹窗（用户已进入通关弹窗后但未选选项）
        try:
            if self._handle_draw_modal(d):
                return 'next_problem'
        except:
            pass

        # AC 确认弹窗仍在（用户没点提交）
        try:
            ac_btn = d.find_elements(By.XPATH,
                "//div[contains(@class, 'n-dialog__action')]//button[span[contains(text(), '提交')]]")
            if ac_btn and ac_btn[0].is_displayed():
                self.log("[恢复] AC 确认弹窗仍在，自动点击'提交'", "info")
                try:
                    ac_btn[0].click()
                except:
                    d.execute_script("arguments[0].click();", ac_btn[0])
                time.sleep(2)
                # 二次警告：再走一遍处理（若用户依然未勾选会再次暂停）
                self._handle_persist_submit_warning(timeout=2)
                return 'retry_outer'
        except:
            pass

        # 抄袭警告还在（用户没动）
        try:
            if d.find_elements(By.XPATH, "//button[span[contains(text(), '坚持提交')]]"):
                self.log("[恢复] '坚持提交'按钮仍在，按当前勾选状态再处理一次", "info")
                self._handle_persist_submit_warning(timeout=2)
                return 'retry_outer'
        except:
            pass

        # 默认：未识别到任何已知弹窗 → 假定用户已处理完毕进入下一题
        self.log("[恢复] 未识别到弹窗状态，进入新一轮解题循环", "info")
        return 'next_problem'

    def _fill_code_editor(self, code):
        """填入代码到编辑器，使用多种方法回退"""
        # ---- 方法 1: 点击编辑器容器激活 + JS 注入 ----
        try:
            # 找所有 .cm-editor，筛选可见的那个
            all_editors = self.driver.find_elements(By.CSS_SELECTOR, ".cm-editor")
            editor_outer = None
            for e in all_editors:
                if e.is_displayed() and e.size['width'] > 0 and e.size['height'] > 0:
                    editor_outer = e
                    break
            if not editor_outer:
                editor_outer = all_editors[0] if all_editors else None
            if not editor_outer:
                raise Exception("未找到 .cm-editor 元素")

            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", editor_outer)
            time.sleep(0.5)

            try:
                editor_outer.click()
                time.sleep(0.3)
            except:
                self.driver.execute_script("arguments[0].click();", editor_outer)
                time.sleep(0.3)

            # 找可见的 .cm-content
            all_contents = self.driver.find_elements(By.CSS_SELECTOR, ".cm-content")
            cm_content = None
            for c in all_contents:
                if c.is_displayed() and c.size['width'] > 0:
                    cm_content = c
                    break
            if not cm_content:
                cm_content = all_contents[0] if all_contents else None
            if not cm_content:
                raise Exception("未找到 .cm-content 元素")

            self.driver.execute_script("""
                var el = arguments[0];
                el.innerText = arguments[1];
                el.dispatchEvent(new Event('input', {bubbles: true, cancelable: true}));
            """, cm_content, code)
            self.log("代码填入成功 (方法1: JS注入)", "success")
            return True
        except Exception as e:
            self.log(f"方法1失败: {e}", "warning")

        # ---- 方法 2: pyperclip 剪贴板粘贴 ----
        try:
            import pyperclip
            pyperclip.copy(code)
            editor_outer = self.driver.find_element(By.CSS_SELECTOR, ".cm-editor")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", editor_outer)
            editor_outer.click()
            time.sleep(0.3)
            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
            time.sleep(0.2)
            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
            time.sleep(0.3)
            self.log("代码填入成功 (方法2: 剪贴板)", "success")
            return True
        except Exception as e:
            self.log(f"方法2失败: {e}", "warning")

        # ---- 方法 3: 直接 send_keys ----
        try:
            content = WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".cm-content"))
            )
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", content)
            content.click()
            content.send_keys(Keys.CONTROL, 'a')
            content.send_keys(code)
            self.log("代码填入成功 (方法3: send_keys)", "success")
            return True
        except Exception as e:
            self.log(f"方法3失败: {e}", "warning")

        return False

    def _make_wait_click(self, driver):
        """返回一个绑定到指定 driver 的 wait_and_click 闭包（带 scrollIntoView + 异常防护）"""
        def wc(by, value, timeout=10):
            try:
                element = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, value)))
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                time.sleep(0.2)
                element.click()
                return element
            except Exception as e:
                self.log(f"点击失败 ({value}): {e}", "warning")
                return None
        return wc

    def _make_wait_input(self, driver):
        """返回一个绑定到指定 driver 的 wait_and_input 闭包"""
        def wi(by, value, text, timeout=10):
            element = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
            element.clear()
            element.send_keys(text)
        return wi

    def _load_solutions(self):
        """读取本地题解缓存，返回 {problem_id: {code, title, savedAt}}。文件缺失或损坏时返回空 dict。"""
        try:
            if os.path.exists(SOLUTIONS_FILE):
                with open(SOLUTIONS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
        except Exception:
            pass
        return {}

    def _save_solution(self, problem_id, title, code):
        """把 AC 通过的代码按题目 id 写入本地缓存（覆盖式），并持久化到磁盘。"""
        if not problem_id or not code:
            return
        problem_id = str(problem_id)
        try:
            self._solutions_cache[problem_id] = {
                "code": code,
                "title": title or "",
                "savedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            with open(SOLUTIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._solutions_cache, f, ensure_ascii=False, indent=2)
            self.log(f"已保存题解到本地缓存 (题目 id={problem_id})", "success")
        except Exception as e:
            self.log(f"保存本地题解失败: {e}", "warning")

    def _decoy_preamble(self):
        """返回 50 个乱序的 #include 行（含末尾换行），用于在提交前拼到代码最前面，
        让相同答案的字符级指纹/前缀重合度足够低，规避 OJ 抄袭警告。"""
        headers = list(DECOY_HEADERS)
        random.shuffle(headers)
        return "".join(f"#include <{h}>\n" for h in headers)

    def _wrap_with_decoy(self, code):
        """把 _decoy_preamble() 拼到 code 最前面。code 已自带 include 也无妨——
        重复包含标准库头文件在 C++ 里是合法的（有 include guard）。"""
        return self._decoy_preamble() + code

    def _format_problem_prompt(self, data, include_source=True):
        """根据 API 返回的题目 data 拼装 prompt。
        include_source=True 时附加'参考题解'段；False 时只给题面+输入输出+样例。
        """
        prompt = (
            f"标题: {data.get('title')}\n"
            f"描述: {data.get('description')}\n"
            f"输入要求: {data.get('inputRequirement')}\n"
            f"输出要求: {data.get('outputRequirement')}\n"
            f"样例输入: {data.get('sampleInput')}\n"
            f"样例输出: {data.get('sampleOuput')}"
        )
        source_code = data.get("sourceCode") or ""
        if include_source and source_code:
            prompt += (
                f"\n参考题解:\n{source_code}\n"
                f"[注] 以上解答仅供参考，保留核心功能即可，无需包含注释。"
            )
        return prompt

    def _get_problem_via_api(self):
        """使用 requests 调用 OJ REST API 获取题目数据，返回带 sourceCode 的 prompt。
        同时把原始 data dict 缓存到 self._last_problem_data，供第 2 次尝试时
        生成无参考题解的干净 prompt。"""
        try:
            url = self.driver.current_url
            exam_id = 410
            problem_id = re.search(r'problems/(\d+)', url).group(1)
            class_id = 263
            self._last_problem_id = problem_id

            # 获取 Token
            token_raw = self.driver.execute_script(
                "return localStorage.getItem('DHU_OJ_ACCESS_TOKEN_USER');"
            )
            if not token_raw:
                self.log("未能获取 Token", "error")
                return None

            try:
                token_data = json.loads(token_raw)
                token_value = token_data.get("value")
            except:
                token_value = token_raw

            # 获取 JSESSIONID
            all_cookies = self.driver.get_cookies()
            jsessionid = next(
                (c['value'] for c in all_cookies if c['name'] == 'JSESSIONID'), ""
            )

            headers = {
                "Accept": "application/json, text/plain, */*",
                "Authorization": token_value,
                "Content-Type": "application/json",
                "Origin": "https://oj.dhu.edu.cn",
                "Referer": "https://oj.dhu.edu.cn/",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0"
                ),
            }
            cookies = {"JSESSIONID": jsessionid}
            payload = {
                "examId": str(exam_id),
                "id": str(problem_id),
                "classId": class_id,
            }

            self.log("正在通过 API 获取题目数据...", "system")
            resp = requests.post(
                "https://oj.dhu.edu.cn/api/problems/getProblemByIdAndExamIdAndClassId",
                headers=headers,
                cookies=cookies,
                json=payload,
                timeout=15,
            )
            resp.raise_for_status()
            res_json = resp.json()

            if res_json.get("code") == 0:
                data = res_json.get("data", {})
                self.log(f"题目: {data.get('title')}", "info")

                # 缓存原始数据用于第 2 次尝试（去除参考题解）
                self._last_problem_data = data
                self._last_cached_code = None  # 默认无缓存，下方命中再赋值

                # 优先使用本地题解缓存作为参考题解（命中则覆盖 API 的 sourceCode）
                cached = self._solutions_cache.get(str(problem_id))
                if cached and cached.get("code"):
                    data["sourceCode"] = cached["code"]
                    self._last_cached_code = cached["code"]
                    self.log("发现本地题解缓存，使用本地答案作为参考题解", "success")
                elif data.get("sourceCode"):
                    self.log("已包含参考题解", "info")

                return self._format_problem_prompt(data, include_source=True)
            else:
                self.log(f"API 返回异常: {res_json}", "error")
                return None

        except Exception as e:
            self.log(f"API 获取题目失败: {e}", "error")
            return None

    def _run_oj(self):
        # 初始化 DeepSeek 客户端
        client = OpenAI(
            api_key=self.config["api_key"],
            base_url=self.config["api_url"]
        )

        self.log("正在启动 Edge 浏览器...", "system")
        self.driver = webdriver.Edge()
        self.driver.maximize_window()

        wait_and_click = self._make_wait_click(self.driver)
        wait_and_input = self._make_wait_input(self.driver)

        def get_ai_solution(prompt_content, current_code=None, error_msg=None):
            system_prompt = "你是一个C++算法竞赛专家。请直接输出可编译的完整C++代码(使用MinGW标准)，不要包含markdown标记(如```cpp)，不要包含任何解释性文字，不要输出注释。参考题解仅供思路参考，保留能完成题目的最小核心功能即可，不要照搬其结构。\n\n【输出格式硬性要求】严格遵循题目「输出范例/样例输出」所示格式，逐字符对齐：\n1. 范例里每行末尾的换行符必须保留——包括最后一行；范例最后一行若有换行就必须输出换行，若没有就不要多输出。\n2. 数值与分隔符之间的空格数（含末尾是否有空格）、标点、大小写、全角/半角必须与范例一致。\n3. 不要自行追加任何提示性文字（如 \"Result:\"、\"答案是\" 等），除非范例里出现。\n4. 多组测试数据之间的空行、首尾空行也必须与范例完全一致。\n输出与范例不一致即视为答案错误，请逐项核对后再产出代码。"
            user_content = prompt_content
            if error_msg:
                user_content = f"我之前的代码如下：\n{current_code}\n\n题目要求是：\n{prompt_content}\n\n报错信息如下：\n{error_msg}\n\n请根据报错修正代码，直接输出修正后的完整代码。"
            try:
                response = client.chat.completions.create(
                    model=self.config["model"],
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    stream=False
                )
                content = response.choices[0].message.content
                content = content.replace("```cpp", "").replace("```", "").strip()
                return content
            except Exception as e:
                self.log(f"AI 调用失败: {e}", "error")
                return None

        # ---- 主流程 ----
        if self._stop_flag:
            return

        self.driver.get(self.config["oj_url"])

        # 检查页面是否正常加载（检测 502 / 空白页等异常）
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='登录账号']"))
            )
        except:
            page_source = self.driver.page_source[:300] if self.driver.page_source else "(空)"
            current_title = self.driver.title
            self.log(f"页面加载异常 — 标题: '{current_title}'", "error")
            self.log(f"页面内容片段: {page_source}", "error")
            if "502" in page_source or "Bad Gateway" in page_source:
                self.log(
                    "OJ 服务器返回 502 Bad Gateway，可能是服务器维护或网络问题。\n"
                    "请尝试：1. 手动打开 http://oj.dhu.edu.cn 检查是否可访问\n"
                    "      2. 等待一段时间后重试",
                    "error"
                )
            elif "404" in page_source or "Not Found" in page_source:
                self.log("OJ 地址不可达（404），请检查 OJ_URL 配置", "error")
            else:
                self.log("登录页面未能正常加载，请手动检查", "error")
            self.log("请在浏览器中手动检查页面状态，然后按回车继续或关闭窗口...", "warning")
            # 给用户机会手动处理
            for _ in range(60):
                if self._stop_flag:
                    return
                time.sleep(1)
                try:
                    # 检测用户是否已手动到达登录页
                    self.driver.find_element(By.XPATH, "//input[@placeholder='登录账号']")
                    self.log("检测到登录页，继续执行...", "success")
                    break
                except:
                    continue
            else:
                self.log("等待超时，终止流程", "error")
                return

        self.log("正在登录...", "info")
        wait_and_input(By.XPATH, "//input[@placeholder='登录账号']", self.config["username"])
        password_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='请输入密码']"))
        )
        password_input.clear()
        password_input.send_keys(self.config["password"])
        time.sleep(0.5)
        password_input.send_keys(Keys.ENTER)
        self.log("登录提交完成", "success")

        if self._stop_flag:
            return

        # 进入考试列表
        try:
            wait_and_click(By.XPATH, "//a[@href='#/user/exam-list']", timeout=5)
        except:
            self.driver.get(f"{self.config['oj_url']}/#/user/exam-list")
        time.sleep(1)

        # 点击第一个"参加"按钮
        self.log("正在参加考试...", "info")
        try:
            buttons = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//button[span[contains(text(), '参加')]]"))
            )
            buttons[0].click()
        except Exception as e:
            self.log(f"点击参加按钮失败: {e}", "error")
            return

        # 点击"参加"后必定转到考试概览页，直接点击"开始做题"
        self.log("点击【开始做题】...", "info")
        try:
            wait_and_click(By.XPATH, "//button[span[contains(text(), '开始做题')]]")
            time.sleep(3)
        except Exception as e:
            self.log(f"点击开始做题失败: {e}", "error")
            return

        # 进入后处理可能出现的抽题弹窗
        if not self._handle_draw_modal(self.driver):
            self.log("无抽题弹窗，已有题目", "info")

        # ---- 循环做题 ----
        while not self._stop_flag:
            # 暂停检查点
            self._wait_if_paused()
            if self._stop_flag:
                break

            # 获取题目（通过 API）
            self.log("正在获取题目详情...", "info")
            problem_prompt = self._get_problem_via_api()
            if not problem_prompt:
                self.log("API 获取题目失败，跳过", "error")
                break

            # 本地缓存命中 → 直接用缓存代码提交（跳过 AI 调用），并在开头拼一段乱序
            # #include 以规避抄袭警告；缓存未命中走原有的 AI 生成流程
            from_cache = bool(self._last_cached_code)
            if from_cache:
                current_code = self._last_cached_code
                self.log("使用本地题解直接提交，跳过 AI 调用", "success")
            else:
                self.log("正在请求 AI 生成代码...", "system")
                code = get_ai_solution(problem_prompt)
                if not code:
                    self.log("AI 生成失败，重试...", "error")
                    continue
                current_code = code
                self.log("AI 代码生成完成", "success")

            if self._stop_flag:
                break

            # 填入代码（多方法回退）；缓存命中时在最前面拼上反查重头文件
            code_to_submit = self._wrap_with_decoy(current_code) if from_cache else current_code
            if not self._fill_code_editor(code_to_submit):
                self.log("所有填入代码方法均失败", "error")

            # 选择语言 MinGW
            try:
                selections = self.driver.find_elements(By.CSS_SELECTOR, ".n-base-selection")
                for sel in selections:
                    try:
                        sel.click()
                        time.sleep(0.2)
                        mingw_opt = self.driver.find_elements(By.XPATH, "//div[contains(text(), 'MinGW')]")
                        if mingw_opt:
                            mingw_opt[0].click()
                            break
                    except:
                        continue
            except:
                pass

            # 延迟提交（提交前等待指定秒数，可中途取消）
            if self.delay_seconds > 0:
                self.log(f"⏳ 等待 {self.delay_seconds} 秒后提交...", "system")
                for _ in range(self.delay_seconds):
                    if self._stop_flag:
                        return
                    time.sleep(1)
                self.log("延迟结束，准备提交", "info")

            # 循环提交（最多 2 次尝试：第 1 次用带参考题解的 prompt，第 2 次用干净 prompt）
            solved = False
            submitted = False
            attempt = 1
            while not solved and not self._stop_flag:
                # 暂停检查点
                self._wait_if_paused()
                if self._stop_flag:
                    break

                # ---- 提交（仅在首次或修复后执行） ----
                if not submitted:
                    self.log("提交代码中...", "system")
                    submit_btn = wait_and_click(By.XPATH, "//button[span[contains(text(), '提交代码')]]")
                    if not submit_btn:
                        self.log("提交按钮未找到", "error")
                        break


                # ---- 等待判题 ----
                self.log("等待判题结果...", "info")
                time.sleep(3)

                # ---- 结果检查 ----

                # 1. "已AC但未提交"确认弹窗（AC后先弹此窗，提交后才出现"我要抽题"）
                ac_submit_btn = wait_and_click(By.XPATH,
                    "//div[contains(@class, 'n-dialog__action')]//button[span[contains(text(), '提交')]]",
                    timeout=30)

                if ac_submit_btn:
                    self.log("检测到'已AC但未提交'弹窗 → 已点击提交", "system")
                    time.sleep(2)

                    # 点击提交后可能出现抄袭警告 —— 走统一处理（支持暂停模式）
                    warning_result = self._handle_persist_submit_warning(timeout=3)
                    if self._stop_flag:
                        break
                    if warning_result == 'paused_resumed':
                        recovery = self._recover_after_resume()
                        if self._stop_flag:
                            break
                        if recovery == 'done':
                            solved = True
                            break
                        if recovery == 'next_problem':
                            solved = True
                            break  # 跳出内层 → 外层进入下一题
                        # 'retry_outer'：让内层下一轮重新检查 AC/通关
                        submitted = True  # 不再重复提交
                        continue

                # 2. "我要抽题"按钮（通关弹窗）
                next_btn = self.driver.find_elements(By.XPATH, "//button[span[contains(text(), '我要抽题')]]")
                if next_btn and next_btn[0].is_displayed():
                    self.log("✅ 题目通过 (AC)！进入下一题...", "success")
                    # 保存本题通过的代码到本地缓存，供下次作为参考题解
                    _title = (self._last_problem_data or {}).get("title")
                    self._save_solution(self._last_problem_id, _title, current_code)
                    next_btn[0].click()
                    solved = True
                    time.sleep(2)
                    # 通关弹窗关闭后可能出现抽题弹窗
                    self._handle_draw_modal(self.driver)
                    break

                # 3. "已通关"（全部题目完成）
                cleared = self.driver.find_elements(By.XPATH, "//div[contains(text(), '已通关')]")
                if cleared:
                    self.log("🎉 已通关当前题组！", "success")
                    solved = True
                    break

                # 4. 仍在排队/判题中 → 继续等待
                try:
                    result_tab = self.driver.find_element(By.XPATH, "//div[@data-name='result']")
                    result_tab.click()
                    time.sleep(1)
                    status_elem = self.driver.find_elements(By.XPATH, "//td[@data-col-key='status']")
                    if status_elem:
                        status_text = status_elem[0].text.lower()
                        if 'queue' in status_text or '等待' in status_text or 'judg' in status_text:
                            self.log(f"判题排队中 ({status_elem[0].text})，继续等待...", "info")
                            continue
                except:
                    pass

                # 5. 未通过 → 按 attempt 决定下一步（两次尝试 + 暂停回退）
                self.log(f"未通过（第 {attempt} 次尝试）", "warning")

                if attempt >= 2:
                    # 第 2 次仍失败 → 暂停等用户处理
                    self.log("⏸ 两次尝试均失败，已暂停。请手动处理后点击'继续'。", "warning")
                    self._send_pushplus_notification(
                        "OJ自动化 - 两次提交失败",
                        f"连续两次提交均未通过 OJ 判题，已暂停等待人工处理。\n\n"
                        f"请在浏览器中查看题目和错误信息，手动编写代码并提交，\n"
                        f"然后在 OJ Helper 中点击「继续」恢复自动流程。"
                    )
                    self._pause_flag = True
                    self.paused_signal.emit()
                    self._wait_if_paused()
                    if self._stop_flag:
                        break
                    self.log("▶ 用户已点击继续，开始容错恢复...", "system")
                    recovery = self._recover_after_resume()
                    if self._stop_flag:
                        break
                    # 不论 recovery 结果如何，本题已交给用户处理，标记 solved 跳出内层
                    solved = True
                    break

                # 第 1 次失败 → 第 2 次尝试：用干净 prompt（不带参考题解，不带报错）重新请求 AI
                self.log("第 2 次尝试：请求 AI 重新作答（不带参考题解、不带报错）...", "system")
                attempt = 2
                if not self._last_problem_data:
                    self.log("题目原始数据缺失，无法重新请求 AI → 暂停等待用户", "error")
                    self._send_pushplus_notification(
                        "OJ自动化 - 题目数据缺失",
                        f"第 1 次提交失败后，题目原始数据丢失，无法让 AI 重新作答。\n\n"
                        f"请在浏览器中查看题目，手动编写代码并提交，\n"
                        f"然后在 OJ Helper 中点击「继续」恢复自动流程。"
                    )
                    self._pause_flag = True
                    self.paused_signal.emit()
                    self._wait_if_paused()
                    if self._stop_flag:
                        break
                    recovery = self._recover_after_resume()
                    solved = True
                    break

                clean_prompt = self._format_problem_prompt(self._last_problem_data, include_source=False)
                new_code = get_ai_solution(clean_prompt)
                if not new_code:
                    self.log("AI 重新作答失败 → 暂停等待用户处理", "warning")
                    self._send_pushplus_notification(
                        "OJ自动化 - AI 重新作答失败",
                        f"AI 第 2 次生成代码失败（API 调用异常）。\n\n"
                        f"请在浏览器中手动编写代码并提交，\n"
                        f"然后在 OJ Helper 中点击「继续」恢复自动流程。"
                    )
                    self._pause_flag = True
                    self.paused_signal.emit()
                    self._wait_if_paused()
                    if self._stop_flag:
                        break
                    recovery = self._recover_after_resume()
                    solved = True
                    break

                current_code = new_code
                self.log("AI 重新作答完成，填入代码...", "success")
                if not self._fill_code_editor(current_code):
                    self.log("第 2 次填入代码失败", "error")
                    break
                submitted = False  # 让内层循环重新走"提交代码"按钮
                continue

        self.log("运行结束", "system")
