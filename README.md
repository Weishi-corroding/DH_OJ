# 🧪 DH OJ Helper

东华大学 Online Judge 自动化辅助工具。使用 Selenium 自动化浏览器 + AI 大模型，自动完成 OJ 题目的获取、作答、提交全流程。

## 功能特性

- **全自动答题** — 从登录、进入考试、抽题、获取题面，到 AI 生成代码、填入编辑器、提交判题，全流程无人值守
- **本地题解缓存** — AC 通过的代码自动缓存，下次遇到相同题目直接提交（附带乱序头文件防查重）
- **反查重保护** — 缓存答案提交时自动在代码前插入 50 个随机顺序的 C++ 标准库头文件，降低字符级指纹相似度
- **智能重试** — 首次失败自动更换策略重新生成（去除参考题解），二次失败暂停等待人工介入
- **多账号 / 多 AI 配置** — 支持多组 OJ 账号与 AI 接口配置，下拉切换
- **暂停恢复** — 任意时刻可暂停流程，手动处理后一键恢复，自动识别当前 DOM 状态
- **通知推送** — 支持 PushPlus 微信推送 + Windows 系统托盘通知
- **Win11 风格界面** — 无边框圆角窗口、自绘控件，清爽现代

## 项目结构

```
main.py                  # 入口：高 DPI 适配 + QApplication + MainWindow 启动
app/
├── constants.py         # 色板、字体、文件路径、反查重头文件池
├── draw_icons.py        # 标题栏图标绘制
├── widgets.py           # 自绘 Win11 控件（按钮/输入框/下拉框/复选框/标题栏按钮/侧边栏按钮）
├── sidebar.py           # 左侧导航栏
├── config_page.py       # 配置页面（OJ 账号、AI 接口、PushPlus、导入导出）
├── run_page.py          # 运行页面（状态卡、开始/暂停/继续、延迟提交、坚持提交开关）
├── log_page.py          # 日志页面（彩色分级日志输出）
├── oj_worker.py         # OJWorker（QThread）：Selenium 自动化主循环
└── main_window.py       # 无边框主窗口
test.py                  # CLI 版本（备选入口，调试用）
fetch_classid.py         # 查询 examId 对应的 classId 辅助脚本
OJ_Helper.spec           # PyInstaller 打包配置
```

## 快速开始

### 环境要求

- Python 3.10+
- Microsoft Edge 浏览器
- [WebDriver](https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/)（已内置于 `chrome/` 目录）

### 安装依赖

```bash
pip install selenium openai requests pyperclip PyQt5
```

### 配置

1. 运行 `python main.py` 启动 GUI
2. 在「配置」页面填写：
   - **OJ 地址** — 默认为 `https://oj.dhu.edu.cn`
   - **账号** — 你的 OJ 登录用户名/密码
   - **AI 接口** — API Key、接口地址、模型名称
   - **PushPlus Token**（可选）— 启用微信推送通知
3. 点击 **保存配置**

### 运行

1. 切换到「运行」页面
2. 点击 **▶ 开始运行**
3. 程序自动打开浏览器 → 登录 → 进入考试 → 循环做题
4. 可在「日志」页面查看实时输出

## ⚠️ 免责声明

本工具仅供学习研究使用，旨在帮助学习 C++ 算法竞赛知识，提高编程能力。

**禁止**将本工具用于：
- 任何形式的学术作弊、作业抄袭或考试舞弊
- 破坏 OJ 平台正常运行
- 其他违反学校规定或法律法规的行为

使用本工具所产生的后果由使用者自行承担。开发者不对因使用本工具而导致的任何违规记录、学术处罚或其他损失负责。

请合理使用，诚信学习。

## 许可证

MIT
