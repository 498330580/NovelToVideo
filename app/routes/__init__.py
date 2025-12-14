"""路由模块初始化"""
from .project_routes import project_bp
from .task_routes import task_bp
from .config_routes import config_bp

__all__ = ['project_bp', 'task_bp', 'config_bp']
