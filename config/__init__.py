"""配置包初始化文件"""
from .default import DefaultConfig
from .development import DevelopmentConfig
from .production import ProductionConfig

__all__ = ['DefaultConfig', 'DevelopmentConfig', 'ProductionConfig']