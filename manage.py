#!/usr/bin/env python
"""Django の管理コマンドを実行するエントリーポイント。"""
import os
import sys


def main() -> None:
    """管理タスクを実行する。"""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django をインポートできません。インストールされているか確認してください。"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
