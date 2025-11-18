"""应用入口文件"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app import create_app
from app.utils.database import init_db
from app.utils.logger import get_logger
from config import DevelopmentConfig, ProductionConfig

logger = get_logger(__name__)


def main():
    """主函数"""
    # 根据环境变量选择配置
    flask_env = os.environ.get('FLASK_ENV', 'development').lower()
    
    if flask_env == 'production':
        config = ProductionConfig
        logger.info('使用生产环境配置')
    else:
        config = DevelopmentConfig
        logger.info('使用开发环境配置')
    
    # 创建Flask应用
    app = create_app(config)
    
    # 初始化数据库
    with app.app_context():
        try:
            init_db()
            logger.info('数据库初始化完成')
        except Exception as e:
            logger.warning(f'数据库初始化跳过(可能已存在): {str(e)}')
    
    # 启动应用
    logger.info('启动Flask应用...')
    logger.info('访问 http://127.0.0.1:5000 打开Web管理面板')
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=config.DEBUG
    )


if __name__ == '__main__':
    main()