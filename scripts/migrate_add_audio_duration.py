#!/usr/bin/env python3
"""
数据库迁移脚本：为 text_segments 表添加 audio_duration 字段
用于存储每个音频段落的时长（秒），以加快视频合成速度

⚠️ 注意：此脚本已过时，应用现已实现自动迁移机制

在应用启动时会自动检测并执行所有待处理的迁移，
用户升级应用后无需手动运行此脚本。

仅当以下情况时才需要手动执行此脚本：
  1. 自动迁移失败，需要手动重新执行
  2. 在没有启动Flask应用的情况下手动执行迁移

运行命令：python scripts/migrate_add_audio_duration.py
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.utils.migrations import run_migrations


if __name__ == '__main__':
    try:
        print("=" * 70)
        print("数据库迁移 - 手动执行模式")
        print("=" * 70)
        print()
        print("⚠️  注意：应用已实现自动迁移机制，通常无需手动执行此脚本")
        print("升级应用后，在启动时会自动检测并执行所有待处理的迁移。")
        print()
        print("仅当以下情况时才需要手动执行此脚本：")
        print("  1. 自动迁移失败，需要手动重新执行")
        print("  2. 在没有启动Flask应用的情况下手动执行迁移")
        print()
        
        success = run_migrations()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  迁移被中断")
        sys.exit(1)
