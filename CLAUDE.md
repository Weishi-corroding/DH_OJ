# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Personal academic/coding project with four distinct areas:

### 1. DHU OJ (Online Judge) Automation (Primary)
Automates solving C++ problems on [oj.dhu.edu.cn](http://oj.dhu.edu.cn) using AI-generated code via Selenium + Edge.

**Two automation scripts:**

- **`test.py`** — Full-featured CLI version. Uses a **hybrid approach**: Selenium for browser interaction + **subprocess `curl` to the OJ REST API** (`/api/problems/getProblemByIdAndExamIdAndClassId`) with auth token from `localStorage` and `JSESSIONID` from cookies. This provides structured problem data (title, description, input/output requirements, samples) rather than raw DOM text. Uses `deepseek-reasoner` (the reasoning model). Hardcoded credentials/API key still live at the top of the file (not yet refactored to config file).

- **`OJ_GUI.py`** — PyQt5 desktop GUI (Windows 11 styled). The only actively maintained entry point. Features: custom frameless window with shadows/drag, sidebar navigation (Config/Run/Logs), Win11-style form controls, threaded OJ execution via `QThread` worker, live logging with color-coded levels, JSON config persistence (`oj_config.json`, gitignored), and proper resource cleanup. Reads all credentials from `oj_config.json` at startup; if the file is missing, the Config page starts empty.

**Test / helper scripts:**
- **`aitest.py`** — Standalone DeepSeek API connectivity tester. Hardcoded `deepseek-chat` model.
- **`test_ai_config.py`** — Verifies AI call by reading `oj_config.json` and sending a probe request. Quick smoke test after editing the config.
- **`test_oj_flow.py`** — Step-by-step Selenium walkthrough of just the **login → join exam → start → handle draw modal** path, with verbose debug logging on every modal/select element. Used to debug the n-select flow in isolation.
- **`fetch_classid.py`** — Helper to discover `classID` values for a given `examId` by calling the OJ REST API directly.
- **`cookies.json`** — Stored JSESSIONID for the OJ platform.

**Packaging:**
- **`OJ_Helper.spec`** — PyInstaller spec for building `OJ_GUI.py` into a single `dist/OJ_Helper.exe`. Bundles `oj_config.json` as data so the exe is relocatable; build artifacts go to `dist/` and `build/` (both gitignored).

**Auth flow (shared pattern):**
1. Selenium Edge browser navigates to `oj.dhu.edu.cn`
2. Fills login form (credentials hardcoded or from config)
3. Extracts `DHU_OJ_ACCESS_TOKEN_USER` from `localStorage` (JSON-wrapped JWT)
4. Reads `JSESSIONID` from cookies
5. Uses both in REST API calls or continues browser-based interaction

**AI code generation flow:**
1. Handle category/draw-problem modal (two-step n-select — see below) → 2. Fetch problem (API or DOM) → 3. Send to DeepSeek → 4. Paste into CodeMirror editor (Ctrl+A, Ctrl+V or `innerText` JS injection) → 5. Select MinGW → 6. Submit → 7. Check for AC (look for "我要抽题" button in success modal or "已通关" text; 30s timeout on the AC modal) → 8. On failure, scrape error details from "运行结果" tab → 9. Send back to AI for repair → 10. Repeat

**Model differences:**
| Script | Model | Config source |
|--------|-------|---------------|
| `OJ_GUI.py` | user-configurable (default in `oj_config.json`: `deepseek-v4-flash`) | `oj_config.json` |
| `test.py` | `deepseek-reasoner` (hardcoded) | env var `DEEPSEEK_API_KEY` |
| `aitest.py` | `deepseek-chat` (hardcoded) | env var `DEEPSEEK_API_KEY` |

### 2. C++ Solutions & Data Structures

**OJ problem solutions (academic):**
- `OJ_StudentArraySort.cpp` — Student class with bubble sort by total score (getter pattern)
- `OJ_CalculateFinalandSort(Friend Function).cpp` — Weighted grade calculation (20/25/55), friend function sort operator
- `OJ_EnterpriseIncomeTax.cpp` — Polymorphic tax: `company` base class → `Service` (5%) / `Manufacture` (17%) with virtual `calcTax()`
- `Oj.cpp` — Simple digit counting in strings

**Data structure implementations:**
- `test.cpp` — Full template-based sequential list (`SqList<T>`) with insert, delete, locate, invert, prior/next element, intersection of two sorted lists. Supports `int`, `double`, `char`, `string`. This is the most substantial C++ file.

**LeetCode:**
- `leetcode49.cpp` — Work-in-progress: Group Anagrams (currently just prints ASCII values of characters)

### 3. Stock / Financial Tools
- `Ashare.py` — Stock price fetcher from Tencent/Sina APIs (from github.com/mpquant/Ashare)
- `calc_mv.py` — Portfolio market value calculator. Reads `20251212.csv` (columns: `code`, `hold_vol`), fetches real-time A-share prices via `akshare.stock_zh_a_spot()`, calculates `market_value = hold_vol * price`
- `scraper.py` — Index scraper template using BeautifulSoup
- Data files: `20251212.csv`, `0202.xlsx`, `0822.xls`

### 4. Python Practice Assignments
- `P1.py` — Power/exponent calculation (`n**20`, count digits)
- `P2.py` — Leap year detection
- `P3.py` — ID card date-of-birth extraction
- `P4.py` — Tiered water bill calculation
- `新建 文本文档.txt` — Combined script with BMI, cone volume, etc.

## Architecture: OJ Automation

```
Browser (Edge via Selenium WebDriver)
├── Login → localStorage["DHU_OJ_ACCESS_TOKEN_USER"]
├── Navigate to exam → /#/user/exam-list → "参加" → "开始做题"
├── Handle category modal (draw problem)
├── CodeMirror editor (.cm-content) ← AI-generated C++
├── Compiler selector → MinGW
├── Submit → "提交代码" → confirm dialog → plagiarism warning
└── Result loop: check AC → error scrape → AI repair → resubmit

AI (DeepSeek via OpenAI-compatible API)
└── System: "你是一个C++算法竞赛专家。直接输出可编译的完整C++代码。"
    ├── User: <problem description>
    └── Or: <existing code + error message> (repair mode)
```

## Build & Run Commands

### C++ (MinGW)
```bash
# Compile
g++ -g file.cpp -o file.exe

# Run (accepts stdin)
./file.exe
```

### Python
```bash
# OJ automation (CLI)
python test.py

# OJ automation (GUI)
python OJ_GUI.py

# Test AI connection
python aitest.py

# Smoke test the config + AI call
python test_ai_config.py

# Debug the OJ login/draw-modal flow in isolation
python test_oj_flow.py

# Fetch classID for an exam
python fetch_classid.py

# Portfolio calculator
python calc_mv.py

# Run individual practice scripts
python P1.py
```

### Dependencies
```bash
pip install selenium openai requests pandas akshare beautifulsoup4 pyperclip PyQt5
```

Browser automation requires Microsoft Edge; WebDriver is bundled in `chrome/`.

## Configuration

All secrets (OJ password, DeepSeek API key) live in **`oj_config.json`** in the repo root. The file is **gitignored** — copy the schema below to bootstrap it, or fill it in via the GUI's Config page (which writes the file on save).

Schema:
```json
{
  "oj_url":   "https://oj.dhu.edu.cn/#/user/index",
  "username": "<oj login>",
  "password": "<oj password>",
  "api_key":  "<DeepSeek API key>",
  "api_url":  "https://api.deepseek.com",
  "model":    "deepseek-v4-flash"
}
```

- `OJ_GUI.py` reads this file on launch (path resolves to the exe's directory when frozen, otherwise the script's directory). Missing file → Config page starts empty, no crash.
- `test.py` and `aitest.py` ignore `oj_config.json` and read credentials/API key from module-level constants / `DEEPSEEK_API_KEY` env var. Refactor target if you want unified config.
- `oj_config.json` is referenced in `OJ_Helper.spec` so it ships alongside the PyInstaller build.

## Key Implementation Details

- **CodeMirror interaction:** The editor is a `.cm-content` contenteditable element. Code is injected via `driver.execute_script("arguments[0].innerText = ...")` followed by a space + backspace to trigger the input event. `test.py` also uses `pyperclip` + `Ctrl+V` as an alternative.
- **Result checking:** AC detection looks for the "我要抽题" button in a success modal or "已通关" text, with a 30s timeout on the AC modal in `OJ_GUI.py`. No AC → switches to the "运行结果" tab and scrapes error details from a textarea.
- **Draw-problem modal (two-step n-select):** The draw modal (`n-card.n-modal` or `n-dialog`) can contain **multiple** `n-select` dropdowns in series. For each visible `.n-select .n-base-selection`: (1) click the selection to open the portal, then (2) on the target `.n-base-select-option`, try `ActionChains.move_to_element().pause().click()` first; on failure fall back to dispatching a `mousedown` MouseEvent (Naive UI doesn't always honor `click` on options). If the portal options aren't found, fall back to a class-based XPath search for `n-base-select-option--show-checkmark`. After every select resolves, click "我要抽题" and verify the modal closes. See `_handle_draw_modal` in `OJ_GUI.py:1196` and the verbose reference flow in `test_oj_flow.py:63`.
- **Threading:** `OJ_GUI.py` runs the OJ automation in a `QThread` to keep the UI responsive, with a `_stop_flag` for clean cancellation.
- **No test framework** is used; scripts run directly with `python file.py`.
- **C++ targets MinGW compiler** compatibility (no MSVC-specific features).

## VS Code Tasks

`.vscode/tasks.json` provides a C++ build task:
- **Label:** `C/C++: g++.exe 生成活动文件`
- **Command:** `C:\Program Files\mingw64\bin\g++.exe -g ${file} -o ${fileDirname}\${fileBasenameNoExtension}.exe`
