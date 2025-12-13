"""开发环境配置"""
from .default import DefaultConfig


class DevelopmentConfig(DefaultConfig):
    """开发环境配置类"""
    
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    
    # 开发环境可以使用更少的资源限制
    MAX_CONCURRENT_PROJECTS = 2
