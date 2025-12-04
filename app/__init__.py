"""Flask应用初始化"""
from flask import Flask, render_template
from config import DevelopmentConfig
from app.utils.database import close_db, init_db
from app.utils.logger import setup_logger, get_logger
from app.services.task_scheduler import TaskScheduler

__version__ = '1.0.0'

logger = get_logger(__name__)


def create_app(config=None):
    """
    创建Flask应用
    
    Args:
        config: 配置对象
        
    Returns:
        Flask应用实例
    """
    app = Flask(__name__)
    
    # 加载配置
    if config is None:
        app.config.from_object(DevelopmentConfig)
    else:
        app.config.from_object(config)
    
    # 设置日志
    setup_logger(log_level=app.config.get('LOG_LEVEL', 'INFO'))
    
    # 注册数据库关闭函数
    app.teardown_appcontext(close_db)
    
    # 注册路由
    register_blueprints(app)
    
    # 注册主页路由
    @app.route('/')
    def index():
        from app.services.project_service import ProjectService
        try:
            projects = ProjectService.get_all_projects()
            total_projects = len(projects)
            completed_projects = sum(1 for p in projects if p.status == 'completed')
            processing_projects = sum(1 for p in projects if p.status in ['processing', 'pending'])
            failed_projects = sum(1 for p in projects if p.status == 'failed')
            
            stats = {
                'total_projects': total_projects,
                'completed_projects': completed_projects,
                'processing_projects': processing_projects,
                'failed_projects': failed_projects,
                'recent_projects': projects[:5] if projects else []
            }
        except Exception as e:
            logger.error(f'获取首页统计信息失败: {str(e)}')
            stats = {
                'total_projects': 0,
                'completed_projects': 0,
                'processing_projects': 0,
                'failed_projects': 0,
                'recent_projects': []
            }
        
        return render_template('dashboard.html', stats=stats)
    
    # 错误处理
    @app.errorhandler(404)
    def not_found(error):
        return render_template('base.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('base.html'), 500
    
    # 启动任务调度器（传入应用实例，便于线程内使用应用上下文）
    with app.app_context():
        TaskScheduler.start(app)
    
    return app


def register_blueprints(app):
    """
    注册蓝图
    
    Args:
        app: Flask应用实例
    """
    from app.routes.project_routes import project_bp
    from app.routes.task_routes import task_bp
    from app.routes.config_routes import config_bp
    
    app.register_blueprint(project_bp)
    app.register_blueprint(task_bp)
    app.register_blueprint(config_bp)
