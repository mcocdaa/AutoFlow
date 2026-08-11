# @file /backend/tests/conftest.py
# @brief pytest 共享配置:仓库根加入 sys.path,使 plugins.* 可被测试与 loader 导入
# @create 2026-08-10

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
