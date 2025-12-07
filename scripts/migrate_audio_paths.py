#!/usr/bin/env python3
"""
数据库迁移脚本：将 text_segments 表中的 audio_path 从全路径转换为相对路径
运行命令：python scripts/migrate_audio_paths.py
"""
import os
import sys
import sqlite3
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import DefaultConfig
from app.models.text_segment import TextSegment
from app.utils.database import execute_query


def migrate_audio_paths():
    """
    将数据库中的所有音频路径从绝对路径转换为相对路径
    """
    print("=" * 60)
    print("开始迁移音频路径...")
    print("=" * 60)
    
    try:
        # 获取数据库连接
        db_path = DefaultConfig.DATABASE_PATH
        if not os.path.exists(db_path):
            print(f"❌ 数据库文件不存在: {db_path}")
            return False
        
        print(f"\n📄 数据库路径: {db_path}")
        print(f"📁 音频目录: {DefaultConfig.TEMP_AUDIO_DIR}")
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 获取所有有音频路径的记录
        cursor.execute('''
            SELECT id, audio_path FROM text_segments 
            WHERE audio_path IS NOT NULL AND audio_path != ''
        ''')
        rows = cursor.fetchall()
        
        print(f"\n📊 找到 {len(rows)} 条有音频路径的记录")
        
        if len(rows) == 0:
            print("✅ 没有需要迁移的记录")
            conn.close()
            return True
        
        # 统计信息
        converted = 0
        skipped = 0
        errors = 0
        
        print("\n🔄 开始转换路径...\n")
        
        for row in rows:
            segment_id = row['id']
            old_path = row['audio_path']
            
            # 检查是否已经是相对路径（不包含目录分隔符或磁盘符）
            if not os.path.isabs(old_path) and not ':' in old_path:
                print(f"  ⏭️  段落 {segment_id}: 已经是相对路径，跳过")
                skipped += 1
                continue
            
            try:
                # 转换为相对路径
                relative_path = TextSegment.convert_to_relative_path(old_path)
                
                # 更新数据库
                cursor.execute(
                    'UPDATE text_segments SET audio_path = ? WHERE id = ?',
                    (relative_path, segment_id)
                )
                
                print(f"  ✅ 段落 {segment_id}:")
                print(f"     旧: {old_path}")
                print(f"     新: {relative_path}")
                
                converted += 1
                
            except Exception as e:
                print(f"  ❌ 段落 {segment_id}: 转换失败 - {str(e)}")
                errors += 1
        
        # 提交更改
        conn.commit()
        conn.close()
        
        print("\n" + "=" * 60)
        print("迁移完成!")
        print("=" * 60)
        print(f"✅ 成功转换: {converted} 条记录")
        print(f"⏭️  跳过: {skipped} 条记录")
        print(f"❌ 错误: {errors} 条记录")
        
        if errors > 0:
            print(f"\n⚠️  有 {errors} 条记录转换失败，请检查日志")
            return False
        
        print("\n✨ 迁移成功完成!")
        return True
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = migrate_audio_paths()
    sys.exit(0 if success else 1)
