#!/usr/bin/env python3
"""
数据库迁移脚本：为 text_segments 表添加 audio_duration 字段
用于存储每个音频段落的时长（秒），以加快视频合成速度

运行命令：python scripts/migrate_add_audio_duration.py
"""
import os
import sys
import sqlite3
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import DefaultConfig
from moviepy.editor import AudioFileClip


def migrate_add_audio_duration():
    """
    为 text_segments 表添加 audio_duration 字段，
    并从现有音频文件读取时长信息填充该字段
    """
    print("=" * 70)
    print("数据库迁移：为 text_segments 表添加 audio_duration 字段")
    print("=" * 70)
    
    try:
        db_path = DefaultConfig.DATABASE_PATH
        if not os.path.exists(db_path):
            print(f"❌ 数据库文件不存在: {db_path}")
            return False
        
        print(f"\n📄 数据库路径: {db_path}")
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(text_segments)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'audio_duration' in columns:
            print("\n✅ audio_duration 字段已存在，跳过迁移")
            conn.close()
            return True
        
        print("\n🔄 开始添加 audio_duration 字段...\n")
        
        # 添加新字段
        cursor.execute("ALTER TABLE text_segments ADD COLUMN audio_duration REAL")
        print("✅ 成功添加 audio_duration 字段")
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_text_segments_audio_duration ON text_segments(audio_duration)")
        print("✅ 成功创建索引")
        
        # 从现有音频文件读取时长信息
        print("\n🔄 正在从音频文件读取时长信息...\n")
        
        cursor.execute('''
            SELECT id, project_id, audio_path FROM text_segments 
            WHERE audio_path IS NOT NULL AND audio_path != ''
            ORDER BY id
        ''')
        rows = cursor.fetchall()
        
        print(f"📊 找到 {len(rows)} 条有音频路径的记录\n")
        
        if len(rows) == 0:
            print("✅ 没有需要更新的记录")
            conn.commit()
            conn.close()
            return True
        
        # 统计信息
        updated = 0
        errors = 0
        
        for idx, row in enumerate(rows):
            segment_id = row['id']
            project_id = row['project_id']
            audio_filename = row['audio_path']
            
            try:
                # 构建音频文件的绝对路径
                audio_abs_path = os.path.join(
                    DefaultConfig.TEMP_AUDIO_DIR,
                    str(project_id),
                    audio_filename
                )
                
                if not os.path.exists(audio_abs_path):
                    print(f"  ⚠️  段落 {segment_id}: 音频文件不存在 - {audio_abs_path}")
                    continue
                
                # 读取音频时长
                audio_clip = AudioFileClip(audio_abs_path)
                duration = audio_clip.duration
                audio_clip.close()
                
                # 更新数据库
                cursor.execute(
                    'UPDATE text_segments SET audio_duration = ? WHERE id = ?',
                    (duration, segment_id)
                )
                
                print(f"  ✅ 段落 {segment_id}: {duration:.2f}秒")
                updated += 1
                
                # 每10条记录输出进度
                if (idx + 1) % 10 == 0:
                    print(f"     ... 已处理 {idx + 1}/{len(rows)} 条记录")
                
            except Exception as e:
                print(f"  ❌ 段落 {segment_id}: 失败 - {str(e)}")
                errors += 1
        
        # 提交更改
        conn.commit()
        conn.close()
        
        print("\n" + "=" * 70)
        print("迁移完成!")
        print("=" * 70)
        print(f"✅ 成功更新: {updated} 条记录")
        print(f"❌ 失败: {errors} 条记录")
        
        if updated > 0:
            print(f"\n✨ 迁移成功! 现在视频合成会更快（直接从数据库读取时长）")
        
        return errors == 0
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    # 激活虚拟环境中的依赖
    try:
        success = migrate_add_audio_duration()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  迁移被中断")
        sys.exit(1)
