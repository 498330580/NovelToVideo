"""默认配置"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.parent


class DefaultConfig:
    """默认配置类"""
    
    # Flask基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = False
    
    # 数据库配置
    DATABASE_PATH = os.path.join(BASE_DIR, 'data', 'novel_to_video.db')
    DATABASE_POOL_SIZE = 10
    
    # 文件路径配置
    OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
    TEMP_DIR = os.path.join(BASE_DIR, 'temp')
    TEMP_AUDIO_DIR = os.path.join(TEMP_DIR, 'audio')
    TEMP_IMAGE_DIR = os.path.join(TEMP_DIR, 'images')
    TEMP_VIDEO_DIR = os.path.join(TEMP_DIR, 'video_segments')
    LOG_DIR = os.path.join(BASE_DIR, 'logs')
    
    # 语音参数默认值
    DEFAULT_VOICE = 'zh-CN-XiaoxiaoNeural'
    DEFAULT_RATE = '+0%'
    DEFAULT_PITCH = '+0Hz'
    DEFAULT_VOLUME = '+0%'
    
    # 视频参数默认值
    DEFAULT_RESOLUTION = (1920, 1080)
    DEFAULT_FPS = 30
    DEFAULT_BITRATE = '2000k'
    DEFAULT_FORMAT = 'mp4'
    DEFAULT_SEGMENT_DURATION = 600  # 秒
    
    # 分段参数默认值
    DEFAULT_SEGMENT_MODE = 'edge_tts'  # 仅支持 edge_tts
    DEFAULT_MAX_WORDS = 10000
    
    # 任务处理配置
    MAX_THREAD_COUNT = 16  # 最大线程数
    MAX_CONCURRENT_PROJECTS = 5  # 最大并发项目数
    TTS_RETRY_COUNT = 3  # TTS失败重试次数
    
    # 资源限制
    MAX_PROJECT_TEXT_SIZE = 5000000  # 单个项目最大字数
    MAX_VIDEO_SEGMENT_DURATION = 3600  # 单个视频片段最大时长(秒)
    MAX_TEMP_FILE_SIZE = 50 * 1024 * 1024 * 1024  # 临时文件最大占用50GB
    
    # 日志配置
    LOG_LEVEL = 'INFO'
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 单个日志文件最大10MB
    LOG_BACKUP_COUNT = 5  # 保留5个备份
    
    # 移除章节识别正则表达式，不再需要章节分段功能