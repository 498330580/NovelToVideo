"""
数据库迁移管理模块
在应用启动时自动执行所有待处理的迁移，确保数据库结构始终保持最新
"""
import os
import sqlite3
from pathlib import Path
from config import DefaultConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)


def get_db_connection():
    """获取数据库连接"""
    db_path = DefaultConfig.DATABASE_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _migration_001_add_audio_duration():
    """
    迁移001：为 text_segments 表添加 audio_duration 字段
    用于存储每个音频段落的时长（秒），以加快视频合成速度
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(text_segments)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'audio_duration' in columns:
            logger.info("迁移001: audio_duration 字段已存在，跳过")
            conn.close()
            return True
        
        logger.info("迁移001: 开始为 text_segments 表添加 audio_duration 字段...")
        
        # 添加新字段
        cursor.execute("ALTER TABLE text_segments ADD COLUMN audio_duration REAL")
        logger.info("迁移001: 成功添加 audio_duration 字段")
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_text_segments_audio_duration 
            ON text_segments(audio_duration)
        """)
        logger.info("迁移001: 成功创建索引")
        
        conn.commit()
        conn.close()
        
        logger.info("迁移001: 完成！后续视频合成会从数据库读取音频时长")
        return True
        
    except Exception as e:
        logger.error(f"迁移001失败: {str(e)}", exc_info=True)
        return False


def _migration_002_audio_paths_to_relative():
    """
    迁移002：将 text_segments 表中的 audio_path 从绝对路径转换为相对路径
    确保音频路径可移植性
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取所有有音频路径的记录
        cursor.execute('''
            SELECT id, audio_path FROM text_segments 
            WHERE audio_path IS NOT NULL AND audio_path != ''
        ''')
        rows = cursor.fetchall()
        
        if not rows:
            logger.info("迁移002: 没有需要转换的音频路径记录")
            conn.close()
            return True
        
        logger.info(f"迁移002: 开始转换 {len(rows)} 条音频路径为相对路径...")
        
        converted = 0
        skipped = 0
        errors = 0
        
        for row in rows:
            segment_id = row['id']
            old_path = row['audio_path']
            
            try:
                # 检查是否已经是相对路径（不包含目录分隔符或磁盘符）
                if not os.path.isabs(old_path) and ':' not in old_path:
                    skipped += 1
                    continue
                
                # 转换为相对路径（仅保存文件名）
                relative_path = os.path.basename(old_path)
                
                # 更新数据库
                cursor.execute(
                    'UPDATE text_segments SET audio_path = ? WHERE id = ?',
                    (relative_path, segment_id)
                )
                
                converted += 1
                
            except Exception as e:
                logger.warning(f"迁移002: 段落 {segment_id} 转换失败 - {str(e)}")
                errors += 1
        
        conn.commit()
        conn.close()
        
        logger.info(f"迁移002: 完成！成功转换 {converted} 条记录, 跳过 {skipped} 条, 错误 {errors} 条")
        return errors == 0
        
    except Exception as e:
        logger.error(f"迁移002失败: {str(e)}", exc_info=True)
        return False


def _migration_003_output_paths_to_relative():
    """
    迁移003：将 projects 表中的 output_path 从绝对路径转换为相对路径
    确保输出路径可移植性
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取所有有输出路径的记录
        cursor.execute('''
            SELECT id, name, output_path FROM projects 
            WHERE output_path IS NOT NULL AND output_path != ''
        ''')
        rows = cursor.fetchall()
        
        if not rows:
            logger.info("迁移003: 没有需要转换的输出路径记录")
            conn.close()
            return True
        
        logger.info(f"迁移003: 开始转换 {len(rows)} 条输出路径为相对路径...")
        
        converted = 0
        skipped = 0
        errors = 0
        
        for row in rows:
            project_id = row['id']
            project_name = row['name']
            old_path = row['output_path']
            
            try:
                # 检查是否已经是相对路径（不包含绝对路径标记）
                if not os.path.isabs(old_path) and ':' not in old_path:
                    skipped += 1
                    continue
                
                # 转换为相对路径（仅保存目录名）
                relative_path = os.path.basename(old_path)
                
                # 更新数据库
                cursor.execute(
                    'UPDATE projects SET output_path = ? WHERE id = ?',
                    (relative_path, project_id)
                )
                
                converted += 1
                
            except Exception as e:
                logger.warning(f"迁移003: 项目 {project_id} ({project_name}) 转换失败 - {str(e)}")
                errors += 1
        
        conn.commit()
        conn.close()
        
        logger.info(f"迁移003: 完成！成功转换 {converted} 条记录, 跳过 {skipped} 条, 错误 {errors} 条")
        return errors == 0
        
    except Exception as e:
        logger.error(f"迁移003失败: {str(e)}", exc_info=True)
        return False


def _get_migration_version():
    """
    获取数据库当前的迁移版本
    
    Returns:
        当前迁移版本号（整数），如果未初始化则返回 0
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查迁移版本表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='db_migrations'
        """)
        
        if not cursor.fetchone():
            # 表不存在，说明还没有执行过任何迁移
            conn.close()
            return 0
        
        # 获取最高版本号
        cursor.execute("SELECT MAX(version) FROM db_migrations WHERE status = 'completed'")
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result[0] else 0
        
    except Exception as e:
        logger.warning(f"获取迁移版本失败: {str(e)}")
        return 0


def _record_migration(version, name, success):
    """
    记录迁移执行情况
    
    Args:
        version: 迁移版本号
        name: 迁移名称
        success: 是否成功
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 创建迁移记录表（如果不存在）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS db_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER NOT NULL UNIQUE,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 记录迁移
        status = 'completed' if success else 'failed'
        cursor.execute("""
            INSERT OR REPLACE INTO db_migrations (version, name, status)
            VALUES (?, ?, ?)
        """, (version, name, status))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.warning(f"记录迁移信息失败: {str(e)}")


def run_migrations():
    """
    自动执行所有待处理的迁移
    在应用启动时调用此函数
    """
    try:
        db_path = DefaultConfig.DATABASE_PATH
        
        # 检查数据库是否存在
        if not os.path.exists(db_path):
            logger.info("数据库不存在或尚未初始化，跳过迁移")
            return True
        
        logger.info("=" * 70)
        logger.info("开始检查并执行数据库迁移...")
        logger.info("=" * 70)
        
        current_version = _get_migration_version()
        logger.info(f"当前数据库迁移版本: {current_version}")
        
        # 定义所有可用的迁移（版本号 -> (迁移函数, 迁移名称)）
        migrations = {
            1: (_migration_001_add_audio_duration, "为 text_segments 表添加 audio_duration 字段"),
            2: (_migration_002_audio_paths_to_relative, "将 text_segments 表中的 audio_path 转换为相对路径"),
            3: (_migration_003_output_paths_to_relative, "将 projects 表中的 output_path 转换为相对路径"),
        }
        
        # 按版本顺序执行迁移
        all_success = True
        for version in sorted(migrations.keys()):
            if version > current_version:
                migration_func, migration_name = migrations[version]
                logger.info(f"\n执行迁移 #{version}: {migration_name}")
                
                try:
                    success = migration_func()
                    _record_migration(version, migration_name, success)
                    
                    if success:
                        logger.info(f"✅ 迁移 #{version} 成功")
                    else:
                        logger.error(f"❌ 迁移 #{version} 失败")
                        all_success = False
                        
                except Exception as e:
                    logger.error(f"❌ 迁移 #{version} 异常: {str(e)}", exc_info=True)
                    _record_migration(version, migration_name, False)
                    all_success = False
        
        if current_version >= max(migrations.keys()):
            logger.info("\n✅ 数据库已是最新版本，无需迁移")
        
        logger.info("=" * 70)
        if all_success:
            logger.info("✨ 所有迁移执行完成")
        else:
            logger.warning("⚠️  某些迁移执行失败，请检查日志")
        logger.info("=" * 70)
        
        return all_success
        
    except Exception as e:
        logger.error(f"执行迁移失败: {str(e)}", exc_info=True)
        return False
