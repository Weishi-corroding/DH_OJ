# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Personal academic/coding project with four distinct areas:

### 1. DHU OJ (Online Judge) Automation (Primary)
Automates solving C++ problems on [oj.dhu.edu.cn](http://oj.dhu.edu.cn) using AI-generated code via Selenium + Edge.

**Two automation scripts:**

- **`test.py`** — CLI version. Uses Selenium + subprocess `curl` to the OJ REST API with auth token from `localStorage` and `JSESSIONID` from cookies. Hardcoded credentials/API key at the top.

- **`main.py` + `app/` package** — PyQt5 desktop GUI. The only actively maintained entry point. Custom frameless window with Win11 styling, sidebar navigation, threaded execution, live logging, JSON config persistence. Supports multiple accounts and AI profiles via dropdown selectors with `+` to add new entries. Layout:
  ```
  main.py                  # entry: high-DPI setup + QApplication + MainWindow.show()
  app/
    constants.py           # colors, fonts, BASE_DIR, CONFIG_FILE, SOLUTIONS_FILE, DECOY_HEADERS
    draw_icons.py          # title-bar icon painters (min/max/close)
    widgets.py             # TitleBarButton, SidebarButton, Win11LineEdit/ComboBox/Button/CheckBox
    sidebar.py             # left nav rail
    config_page.py         # OJ accounts + AI profiles + PushPlus + import/export
    run_page.py            # status card + start/stop/continue + delay + persist-submit
    log_page.py            # color-coded log output
    oj_worker.py           # OJWorker (QThread): Selenium login → loop → AI/cache → submit
    main_window.py         # frameless MainWindow with sidebar + stacked pages
  ```

**Helper scripts:**
- `fetch_classid.py` — Helper to discover `classID` values for a given `examId` via the OJ REST API.

**Packaging:**
- `OJ_Helper.spec` — PyInstaller spec to build `main.py` into a single `dist/OJ_Helper.exe`.

### 2. C++ Solutions & Data Structures
- `OJ_StudentArraySort.cpp` — Student class with bubble sort by total score.
- `OJ_CalculateFinalandSort(Friend Function).cpp` — Weighted grade calculation, friend function sort.
- `OJ_EnterpriseIncomeTax.cpp` — Polymorphic tax: base `company` → `Service` (5%) / `Manufacture` (17%).
- `Oj.cpp` — Simple digit counting in strings.
- `test.cpp` — Full template-based sequential list (`SqList<T>`).
- `leetcode49.cpp` — Work-in-progress: Group Anagrams.

### 3. Stock / Financial Tools
- `Ashare.py` — Stock price fetcher from Tencent/Sina APIs.
- `calc_mv.py` — Portfolio market value calculator. Reads `20251212.csv`, fetches A-share prices via `akshare`.
- `scraper.py` — BeautifulSoup index scraper template.
- Data files: `20251212.csv`, `0202.xlsx`, `0822.xls`.

### 4. Python Practice Assignments
- `P1.py`–`P4.py` — Power calc, leap year, ID extraction, water bill.
- `新建 文本文档.txt` — BMI, cone volume, etc.

## GUI Architecture (`main.py` + `app/`)

The GUI lives in the `app/` package; `main.py` is a 30-line entry. Each module owns one class (or one tightly-related cluster); cross-module references go through `from app.<module> import <Name>`. See the layout block above for the file-to-class mapping.

### Widget Tree
```
MainWindow (QMainWindow)                          # Custom frameless, W10/11 style
├── TitleBarButton × 3                            # Close / minimize / maximize (QPainter-drawn)
├── Sidebar (QWidget)                             # Navigation rail
│   └── SidebarButton × 4                         # Nav entries, active-highlighted
└── QStackedWidget
    ├── ConfigPage (QWidget)                      # OJ credentials, API key, model, delay
    │   ├── Win11LineEdit (oj_url)                # Global field
    │   ├── Win11ComboBox (account selector)      # Dropdown of `accounts[*].username`
    │   ├── Win11Button "＋" (add account)        # Appends blank account
    │   ├── Win11LineEdit × 2                     # username / password (current account)
    │   ├── Win11ComboBox (AI profile selector)   # Dropdown of `ai_profiles[*].model`
    │   ├── Win11Button "＋" (add AI profile)     # Appends blank profile
    │   ├── Win11LineEdit × 3                     # api_key / api_url / model (current profile)
    │   ├── Win11CheckBox + Win11LineEdit         # PushPlus toggle + token
    │   └── Win11Button ("Import / Export / Save Config")
    ├── RunPage (QWidget)                         # Main control panel
    │   ├── Status card (dot + label)             # Ready / Running / Paused
    │   ├── Summary section (attempts, problems, pass rate)
    │   ├── Win11CheckBox ("Persist submit on warning")
    │   ├── Win11Button ("Start OJ" / "Stop" / "Continue")
    │   └── OJWorker (QThread, not a visual widget)
    └── LogPage (QWidget)                         # Scrollable log output
        └── QPlainTextEdit (read-only)            # Color-coded log levels (info/warning/error/success/system)
```

### Custom Win11-style Widgets
Buttons/checkboxes/sidebar are custom-drawn with QPainter; inputs/dropdowns use a thin QSS layer over native widgets:
- `TitleBarButton` — Paints close/minimize/maximize icons; hover/leave color transitions.
- `SidebarButton` — Vertical nav button with active indicator bar.
- `Win11LineEdit` — `QLineEdit` wrapped with top label + focus-line; QSS-styled border / focus state.
- `Win11ComboBox` — `QComboBox` wrapped the same way as `Win11LineEdit` (top label + focus-line). Exposes `addItem`/`clear`/`currentIndex`/`setCurrentIndex`/`setItemText`/`currentIndexChanged`. Used for the account and AI profile dropdowns in `ConfigPage`.
- `Win11Button` — Rounded rect button (QPainter) with primary/secondary variants, press/hover states. `set_bg()` for runtime recolor (used by the Pause/Continue button).
- `Win11CheckBox` — Toggle switch with animated thumb.

### Threading Model
```
Main thread (GUI)          OJWorker (QThread)
┌─────────────────┐        ┌────────────────────────────┐
│  RunPage         │──────→│  _run_oj()                  │
│  start_oj()      │ signal │  - Browser automation loop  │
│  stop_oj()       │←──────│  log_signal(text, level)    │
│  resume_oj()     │ signal │  - emits to LogPage         │
└─────────────────┘        └────────────────────────────┘
     │                           │
     │  _stop_flag = True        │  Checks _stop_flag at
     │  → driver.quit()          │  every blocking step
     │                           │
     │  _pause_flag = True       │  _wait_if_paused() loops
     │                           │  on time.sleep(0.1) until
     │                           │  _pause_flag=False
```

Clean cancellation: `stop()` sets both flags and calls `driver.quit()` to unblock Selenium.

## Core Automation Flow (`OJWorker._run_oj` in `app/oj_worker.py`)

### Main Loop State Machine
```
START → Login → Exam list → "参加" → "开始做题" → Handle draw modal
                                                      │
                                                      ▼
                                              ┌──────────────────┐
                                          ┌──→│ Get problem (API) │
                                          │   └────────┬─────────┘
                                          │            ▼
                                          │   ┌──────────────────┐
                                          │   │ AI generate code │
                                          │   └────────┬─────────┘
                                          │            ▼
                                          │   ┌──────────────────┐
                                          │   │ Fill CodeMirror   │
                                          │   │ (.cm-content)     │
                                          │   └────────┬─────────┘
                                          │            ▼
                                          │   ┌──────────────────┐
                                          │   │ Select MinGW      │
                                          │   └────────┬─────────┘
                                          │            ▼
                                          │   ┌──────────────────┐
                                          │   │ Submit code       │
                                          │   └────────┬─────────┘
                                          │            ▼
                                          │   ┌──────────────────────────────┐
                                          │   │ Result check (loop, 30s max) │
                                          │   └──────┬───────┬───────┬──────┘
                                          │          │       │       │
                     ┌────────────────────┼──────────┘       │       └──────────┐
                     ▼                    ▼                   ▼                  ▼
              ┌────────────┐     ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐
              │ AC dialog  │     │  "我要抽题"   │   │  "已通关"     │   │  Fail (scrape    │
              │ → submit → │     │  → next      │   │  → all done  │   │  "运行结果" tab) │
              │ plagiarism │     │  problem     │   │              │   └────────┬─────────┘
              │ warning?   │     └──────────────┘   └──────────────┘            │
              └─────┬──────┘                                                   ▼
                    ▼                                          ┌──────────────────────┐
         ┌──────────────────┐                                  │ Attempt 1: send error│
         │ Auto-click OR    │                                  │   back to AI for fix │
         │ Pause for user   │                                  │ Attempt 2: clean     │
         └──────────────────┘                                  │   prompt (no ref)    │
                                                               │ Attempt 2 fails →    │
                                                               │   pause for user     │
                                                               └──────────────────────┘
```

### Result Checking Order (in _run_oj)
1. **AC submit dialog** — `n-dialog__action` with "提交" button (AC achieved but not yet submitted). After clicking submit, checks for plagiarism warning.
2. **"我要抽题" button** — Success modal with next-problem button.
3. **"已通关" text** — All problems in the exam completed.
4. **Queuing state** — Checks "运行结果" tab for `queue`/`judging` status text; continues waiting.
5. **Failure** — Scrapes error details from the "运行结果" tab textarea → sends back to AI.

### Two-Attempt Retry Strategy
- **Attempt 1:** Sends full problem + reference solution to AI. The reference is the local cached solution if one exists for this problem id (see Local Solution Cache), otherwise the API-returned `sourceCode`. If it fails, scrapes the OJ error output and sends code + error back for repair.
- **Attempt 2:** If attempt 1 fails, requests a fresh solution from AI using a **clean prompt** (problem description only, no reference solution, no error context). If this also fails, `pause_flag = True` and the worker waits for user intervention.

### Delay Before Submit
`self.delay_seconds` (configurable in GUI) — waits N seconds before clicking submit. Checks `_stop_flag` each second, so the user can cancel during the delay.

### Plagiarism Warning Handling (`_handle_persist_submit_warning`)
- If `_persist_submit` is enabled (checkbox): auto-clicks "坚持提交" and continues.
- If disabled: sets `_pause_flag = True`, emits `paused_signal`, waits for user to handle manually. After resume, `_recover_after_resume()` inspects the DOM to determine next action.

### Pause/Resume Recovery (`_recover_after_resume`)
Called after the user clicks "Continue". Handles 5+ DOM states:
| DOM State | Action |
|-----------|--------|
| "我要抽题" button visible | Click it → handle draw modal → `'next_problem'` |
| "已通关" text visible | `'done'` — exit entire loop |
| Draw modal open | Handle selections → `'next_problem'` |
| AC confirm dialog still open | Click submit → `'retry_outer'` |
| None of the above | `'retry_outer'` — recheck results |

### Problem Fetching (`_get_problem_via_api`)
Two methods, tried in order:
1. **REST API** — POST to `/api/problems/getProblemByIdAndExamIdAndClassId` with auth token + JSESSIONID. Returns structured JSON (title, description, I/O spec, samples).
2. **DOM fallback** — Reads `n-list-item__content` elements from the problem page.

Problem data stored in `_last_problem_data` for potential retry (attempt 2); the URL-derived problem id is stored in `_last_problem_id` for the local solution cache.

### Local Solution Cache (`oj_solutions.json`)
AC'd solutions are cached locally and reused as the reference solution on later runs.
- **Storage:** `oj_solutions.json` (gitignored), resolved in the same exe-dir/script-dir way as `oj_config.json`. Schema: `{ "<problemId>": { "code", "title", "savedAt" } }`.
- **Load:** `_load_solutions()` reads the file into `self._solutions_cache` on worker init (returns `{}` on missing/corrupt file).
- **Save:** `_save_solution(problem_id, title, code)` writes/overwrites an entry and persists to disk. Called at the AC → next-problem moment (the "我要抽题" branch), storing `current_code` — the code that actually passed judging.
- **Reuse:** In `_get_problem_via_api`, a cache hit **overwrites `data["sourceCode"]`** with the cached code before the prompt is built, and stores the cached code in `self._last_cached_code`. The main loop then **skips the AI call entirely**, submits the cached code directly, and prepends a 50-line shuffled `#include` preamble (`DECOY_HEADERS` in `app/constants.py`, shuffled per submit by `_decoy_preamble()`) so the OJ plagiarism check sees a different prefix each time. The cached entry on disk is never decorated — only the byte stream sent to the editor.
- **Key caveat:** keyed by problem id only; `examId`/`classId` are hardcoded (410/263), so ids are assumed unique across exams.

### CodeMirror Code Injection (`_fill_code_editor`)
Three fallback methods:
1. `innerText = code` on `.cm-content` + space+backspace to trigger input event.
2. `execCommand('insertText')` JavaScript.
3. `pyperclip.copy()` + Ctrl+A, Ctrl+V (fallback if first two fail).

### Draw Modal Handling (`_handle_draw_modal`)
Two-step n-select interaction (Naive UI):
1. For each visible `.n-base-selection`, click to open the dropdown portal.
2. Find `.n-base-select-option` in the portal → `ActionChains.move_to_element().click()`, fallback to `mousedown` MouseEvent dispatch.

After all selections made, click "我要抽题" and verify the modal closes.

### Wait Helpers
- `_make_wait_click(driver)` — Returns `wc(by, value, timeout)` closure using `WebDriverWait + element_to_be_clickable`, then clicks with JS fallback.
- `_make_wait_input(driver)` — Returns `wi(by, value, text, timeout)` closure that waits for element, clears, and sends keys.

## Auth Flow (Shared Pattern)
1. Selenium Edge browser navigates to `oj.dhu.edu.cn`
2. Fills login form (credentials from config)
3. Extracts `DHU_OJ_ACCESS_TOKEN_USER` from `localStorage` (JSON-wrapped JWT)
4. Reads `JSESSIONID` from cookies
5. Uses both in REST API calls or continues browser-based interaction

## Configuration

All secrets (OJ password, DeepSeek API key) live in **`oj_config.json`** (gitignored). Nested schema with multiple accounts and AI profiles:

```json
{
  "oj_url": "https://oj.dhu.edu.cn/#/user/index",
  "active_account": 0,
  "accounts": [
    { "username": "<oj login>", "password": "<oj password>" }
  ],
  "active_ai": 0,
  "ai_profiles": [
    {
      "api_key": "<DeepSeek API key>",
      "api_url": "https://api.deepseek.com",
      "model": "deepseek-v4-flash"
    }
  ],
  "pushplus_enabled": false,
  "pushplus_token": ""
}
```

- `app/config_page.py` reads `oj_config.json` on launch; the **account dropdown** lists `accounts[*].username` and the **AI dropdown** lists `ai_profiles[*].model`. `+` buttons append a blank entry; editing the username/model fields renames the dropdown item in-place. `active_account` / `active_ai` remember the currently selected index across launches.
- `ConfigPage._normalize_cfg()` transparently folds the legacy flat schema (top-level `username` / `api_key` / `model` / ...) into the nested form, so older imports still work.
- `RunPage` calls `page_config.get_active_config()`, which returns a flat dict for the currently selected account + AI profile. `OJWorker` consumes that flat dict and is schema-agnostic.
- Missing file → `_ensure_default_state()` seeds the UI with one blank account + one blank AI profile.
- `test.py` ignores `oj_config.json`; it reads credentials from module-level constants and `DEEPSEEK_API_KEY` env var.
- `oj_config.json` is bundled in the PyInstaller build (see `OJ_Helper.spec`).

## Build & Run Commands

### C++ (MinGW)
```bash
g++ -g file.cpp -o file.exe
./file.exe
```

### Python
```bash
python main.py                 # Main GUI (recommended entry point)
python test.py                 # CLI version
python fetch_classid.py        # Discover classID for an exam
python calc_mv.py              # Portfolio calculator
```

### Dependencies
```bash
pip install selenium openai requests pandas akshare beautifulsoup4 pyperclip PyQt5
```

Browser automation requires Microsoft Edge; WebDriver is bundled in `chrome/`.

## .gitignore
```
oj_config.json          # Personal config (API keys, passwords)
oj_solutions.json       # Local AC solution cache
dist/ build/ *.spec     # PyInstaller build artifacts
*.exe *.obj *.o         # Compiled C++ binaries
__pycache__/ *.pyc      # Python cache
```

## VS Code Tasks
`.vscode/tasks.json` provides a C++ build task:
- **Label:** `C/C++: g++.exe 生成活动文件`
- **Command:** `g++ -g ${file} -o ${fileDirname}\${fileBasenameNoExtension}.exe`

## Model Differences
| Script | Model | Config source |
|--------|-------|---------------|
| `main.py` (`app/oj_worker.py`) | user-configurable (default `deepseek-v4-flash`) | `oj_config.json` (`ai_profiles[active_ai].model`) |
| `test.py` | `deepseek-reasoner` (hardcoded) | env var `DEEPSEEK_API_KEY` |

AI system prompt (`app/oj_worker.py`): *"你是一个C++算法竞赛专家。请直接输出可编译的完整C++代码(使用MinGW标准)，不要包含markdown标记..."* — followed by an **【输出格式硬性要求】** block that mandates byte-exact agreement with the problem's sample output (trailing newline preservation, exact spacing/punctuation, no extra prefix text, identical blank lines between multi-cases).
test.py version is similar but includes more formatting instructions.
