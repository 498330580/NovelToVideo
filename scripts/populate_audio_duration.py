#!/usr/bin/env python3
"""
数据库迁移脚本：为已存在的音频段落填充 audio_duration 字段数据
用于修复 1.0.0 版本升级后缺少 audio_duration 数据的问题

此脚本会：
1. 查找所有 audio_duration 为 NULL 的段落
2. 从对应的音频文件获取时长
3. 将时长写入数据库

运行命令：python scripts/populate_audio_duration.py
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.utils.migrations import get_db_connection
from config import DefaultConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)

try:
    from moviepy.editor import AudioFileClip
except ImportError:
    logger.error("需要安装 moviepy 库: pip install moviepy")
    sys.exit(1)


def get_audio_duration(audio_path):
    """
    获取音频文件的时长（秒）
    
    Args:
        audio_path: 音频文件的绝对路径
        
    Returns:
        时长（秒），获取失败返回 None
    """
    try:
        if not os.path.exists(audio_path):
            logger.warning(f"音频文件不存在: {audio_path}")
            return None
        
        # 获取音频时长
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        audio.close()
        
        return duration
    except Exception as e:
        logger.warning(f"获取音频时长失败 ({audio_path}): {str(e)}")
        return None


def populate_audio_duration():
    """
    填充 audio_duration 字段数据
    
    Returns:
        是否成功
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取所有 audio_duration 为 NULL 且有 audio_path 的段落
        cursor.execute('''
            SELECT id, project_id, audio_path 
            FROM text_segments 
            WHERE audio_duration IS NULL AND audio_path IS NOT NULL AND audio_path != ''
            ORDER BY id
        ''')
        rows = cursor.fetchall()
        
        if not rows:
            logger.info("没有需要填充的 audio_duration 记录")
            conn.close()
            return True
        
        logger.info(f"开始填充 audio_duration 字段，共 {len(rows)} 条记录")
        
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for row in rows:
            segment_id = row['id']
            project_id = row['project_id']
            relative_audio_path = row['audio_path']
            
            try:
                # 构建绝对路径
                abs_audio_path = os.path.join(
                    DefaultConfig.TEMP_AUDIO_DIR,
                    str(project_id),
                    relative_audio_path
                )
                
                # 获取音频时长
                duration = get_audio_duration(abs_audio_path)
                
                if duration is None:
                    logger.warning(f"段落 {segment_id}: 无法获取音频时长，跳过")
                    skip_count += 1
                    continue
                
                # 更新数据库
                cursor.execute(
                    'UPDATE text_segments SET audio_duration = ? WHERE id = ?',
                    (duration, segment_id)
                )
                
                logger.debug(f"段落 {segment_id}: 已设置时长 {duration:.2f}s")
                success_count += 1
                
            except Exception as e:
                logger.error(f"段落 {segment_id}: 处理失败 - {str(e)}")
                error_count += 1
        
        conn.commit()
        conn.close()
        
        logger.info(f"填充完成！成功: {success_count}, 跳过: {skip_count}, 错误: {error_count}")
        
        return error_count == 0
        
    except Exception as e:
        logger.error(f"填充 audio_duration 失败: {str(e)}", exc_info=True)
        return False


if __name__ == '__main__':
    try:
        print("=" * 70)
        print("填充 audio_duration 字段数据")
        print("=" * 70)
        print()
        
        success = populate_audio_duration()
        
        print()
        print("=" * 70)
        if success:
            print("✅ 成功完成！")
            print("现在可以正常生成视频了。")
        else:
            print("❌ 处理中出现错误，请检查日志。")
        print("=" * 70)
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  操作被中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"未预期的错误: {str(e)}", exc_info=True)
        sys.exit(1)
