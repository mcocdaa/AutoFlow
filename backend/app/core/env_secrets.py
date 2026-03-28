import os
from pathlib import Path


def apply_file_env() -> None:
    allowlist = {
        "DB_PASSWORD_FILE",
        "SECRET_KEY_FILE",
        "MYSQL_ROOT_PASSWORD_FILE",
    }
    for key, file_path in list(os.environ.items()):
        if key not in allowlist or not file_path:
            continue
        target_key = key[:-5]
        if os.environ.get(target_key):
            raise RuntimeError(
                f"检测到同时设置了 {target_key} 与 {key}，请只保留一种配置方式"
            )
        p = Path(file_path)
        if not p.exists():
            raise RuntimeError(f"{key} 指向的文件不存在: {file_path}")
        secret = p.read_text(encoding="utf-8").strip()
        if not secret:
            raise RuntimeError(f"{key} 指向的文件内容为空: {file_path}")
        os.environ[target_key] = secret
