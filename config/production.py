"""生产环境配置"""
from .default import DefaultConfig


class ProductionConfig(DefaultConfig):
    """生产环境配置类"""
    
    DEBUG = False
    LOG_LEVEL = 'INFO'
    
    # 生产环境使用更多资源
    MAX_CONCURRENT_PROJECTS = 5
    MAX_THREAD_COUNT = 16