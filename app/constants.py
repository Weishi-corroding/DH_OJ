# -*- coding: utf-8 -*-
"""全局常量：颜色、字体、布局尺寸、文件路径、反查重头文件池。"""

import os
import sys

# ============================================================
# 颜色 / 字体 / 布局
# ============================================================
FONT_FAMILY = "Microsoft YaHei UI"
ICON_COLOR = "#1A1A1A"
ACCENT_BLUE = "#005FB8"
ACCENT_BLUE_HOVER = "#004C93"
TITLE_BG = "#F3F3F3"
WINDOW_BG = "#FAFAFA"
SIDEBAR_BG = "#F3F3F3"
BORDER_COLOR = "#E5E5E5"
TEXT_PRIMARY = "#1A1A1A"
TEXT_SECONDARY = "#666666"
TEXT_PLACEHOLDER = "#999999"
INPUT_BG = "#FFFFFF"
INPUT_BORDER = "#D1D1D1"
INPUT_BORDER_FOCUS = "#005FB8"
BTN_HOVER_BG = "#E5E5E5"
BTN_PRIMARY_BG = "#005FB8"
BTN_PRIMARY_HOVER = "#004C93"
SUCCESS_GREEN = "#0FA958"
ERROR_RED = "#E81123"
WARNING_ORANGE = "#FF8C00"
LOG_BG = "#1E1E1E"
SIDEBAR_WIDTH = 200
TITLEBAR_HEIGHT = 36
WINDOW_RADIUS = 8
SHADOW_MARGIN = 10


# ============================================================
# 文件路径
# ============================================================
# 打包为 exe 时配置/缓存文件放在 exe 同目录（用户可编辑）；开发态下放在仓库根目录。
# 注意：本文件位于 app/，所以要在脚本模式下向上一级到项目根。
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_FILE = os.path.join(BASE_DIR, "oj_config.json")
# 本地题解缓存：AC 成功后把通过的代码按题目 id 存入，下次作为参考题解复用
SOLUTIONS_FILE = os.path.join(BASE_DIR, "oj_solutions.json")


# ============================================================
# 反查重头文件池
# ============================================================
# 本地题解直接提交时，在代码前部拼一段乱序 #include，让两份相同答案在
# 词频/前缀指纹上产生足够差异。50 个均为标准库头文件，MinGW 下都可编译通过；
# 顺序在每次提交时打乱。
DECOY_HEADERS = [
    "iostream", "iomanip", "fstream", "sstream", "string", "cstring",
    "cstdio", "cstdlib", "cmath", "cctype", "climits", "cfloat",
    "ctime", "cassert", "vector", "list", "deque", "queue", "stack",
    "map", "set", "unordered_map", "unordered_set", "bitset", "array",
    "tuple", "utility", "algorithm", "numeric", "functional", "iterator",
    "memory", "limits", "type_traits", "complex", "valarray", "random",
    "chrono", "ratio", "regex", "locale", "codecvt", "exception",
    "stdexcept", "system_error", "new", "typeinfo", "scoped_allocator",
    "initializer_list", "atomic"
]
