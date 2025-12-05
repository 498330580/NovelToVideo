"""日志工具模块"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(name='novel_to_video', log_level='INFO'):
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        log_level: 日志级别
        
    Returns:
        配置好的日志记录器
    """
    from config import DefaultConfig
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level))
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 确保日志目录存在
    log_dir = Path(DefaultConfig.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    
    # 文件处理器 - 轮转日志
    file_handler = RotatingFileHandler(
        log_dir / 'app.log',
        maxBytes=DefaultConfig.LOG_MAX_BYTES,
        backupCount=DefaultConfig.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 错误日志单独文件
    error_handler = RotatingFileHandler(
        log_dir / 'error.log',
        maxBytes=DefaultConfig.LOG_MAX_BYTES,
        backupCount=DefaultConfig.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    return logger


def get_logger(name='novel_to_video'):
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        日志记录器
    """
    logger = logging.getLogger(name)
    
    # 如果logger还没有被配置,则配置它
    if not logger.handlers:
        from config import DefaultConfig
        setup_logger(name, DefaultConfig.LOG_LEVEL)
    
    return logger
