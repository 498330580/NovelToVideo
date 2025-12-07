#!/usr/bin/env python3
"""
数据库迁移脚本：将 projects 表中的 output_path 从全路径转换为相对路径
运行命令：python scripts/migrate_output_paths.py
"""
import os
import sys
import sqlite3
from pathlib import Path


# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 不导入 app 模块，直接使用本地函数

# 定义 OUTPUT_DIR
OUTPUT_DIR = os.path.join(project_root, 'output')
DATABASE_PATH = os.path.join(project_root, 'data', 'novel_to_video.db')


def convert_to_relative_path(absolute_path):
    """
    将绝对路径转换为相对路径
    相对于 output 目录
    
    Args:
        absolute_path: 绝对路径
        
    Returns:
        相对路径（仅目录名）
    """
    if not absolute_path:
        return None
    
    # 只保存目录名（最后一部分）
    return os.path.basename(absolute_path)


def migrate_output_paths():
    """
    将数据库中的所有输出路径从绝对路径转换为相对路径
    """
    print("=" * 60)
    print("开始迁移输出路径...")
    print("=" * 60)
    
    try:
        # 获取数据库连接
        db_path = DATABASE_PATH
        if not os.path.exists(db_path):
            print(f"❌ 数据库文件不存在: {db_path}")
            return False
        
        print(f"\n📄 数据库路径: {db_path}")
        print(f"📁 输出目录: {OUTPUT_DIR}")
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 获取所有有输出路径的记录
        cursor.execute('''
            SELECT id, name, output_path FROM projects 
            WHERE output_path IS NOT NULL AND output_path != ''
        ''')
        rows = cursor.fetchall()
        
        print(f"\n📊 找到 {len(rows)} 条有输出路径的记录")
        
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
            project_id = row['id']
            project_name = row['name']
            old_path = row['output_path']
            
            # 检查是否已经是相对路径（不包含目录分隔符或磁盘符）
            if not os.path.isabs(old_path) and ':' not in old_path:
                print(f"  ⏭️  项目 {project_id} ({project_name}): 已经是相对路径，跳过")
                skipped += 1
                continue
            
            try:
                # 转换为相对路径
                relative_path = convert_to_relative_path(old_path)
                
                # 更新数据库
                cursor.execute(
                    'UPDATE projects SET output_path = ? WHERE id = ?',
                    (relative_path, project_id)
                )
                
                print(f"  ✅ 项目 {project_id} ({project_name}):")
                print(f"     旧: {old_path}")
                print(f"     新: {relative_path}")
                
                converted += 1
                
            except Exception as e:
                print(f"  ❌ 项目 {project_id} ({project_name}): 转换失败 - {str(e)}")
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
    success = migrate_output_paths()
    sys.exit(0 if success else 1)
