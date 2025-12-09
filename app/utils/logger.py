"""日志工具模块"""
import logging
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path

# 日志锁，确保线程安全
_logger_lock = threading.Lock()

# 全局日志处理器缓存
_global_handlers = None


def _get_or_create_global_handlers():
    """
    获取或创建全局日志处理器
    确保所有日志记录器共享相同的处理器
    """
    global _global_handlers
    
    if _global_handlers is not None:
        return _global_handlers
    
    from config import DefaultConfig
    
    # 确保日志目录存在
    log_dir = Path(DefaultConfig.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    
    handlers = []
    
    # 文件处理器 - 轮转日志
    file_handler = RotatingFileHandler(
        log_dir / 'app.log',
        maxBytes=DefaultConfig.LOG_MAX_BYTES,
        backupCount=DefaultConfig.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    file_handler.flush = lambda: file_handler.stream.flush()  # 确保可以刷新
    handlers.append(file_handler)
    
    # 控制台处理器 - 直接输出到stdout
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    console_handler.flush = lambda: sys.stdout.flush()  # 显式刷新stdout
    handlers.append(console_handler)
    
    # 错误日志单独文件
    error_handler = RotatingFileHandler(
        log_dir / 'error.log',
        maxBytes=DefaultConfig.LOG_MAX_BYTES,
        backupCount=DefaultConfig.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    error_handler.flush = lambda: error_handler.stream.flush()
    handlers.append(error_handler)
    
    _global_handlers = handlers
    return _global_handlers


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
    
    # 获取全局处理器并添加到此logger
    handlers = _get_or_create_global_handlers()
    for handler in handlers:
        logger.addHandler(handler)
    
    # 禁用传播到父logger，避免重复输出
    logger.propagate = False
    
    return logger


def get_logger(name='novel_to_video'):
    """
    获取日志记录器
    线程安全的
    
    Args:
        name: 日志记录器名称
        
    Returns:
        日志记录器
    """
    from config import DefaultConfig
    
    with _logger_lock:
        logger = logging.getLogger(name)
        
        # 如果logger还没有被配置,则配置它
        if not logger.handlers:
            setup_logger(name, DefaultConfig.LOG_LEVEL)
        else:
            # 确保处理器有刷新机制
            for handler in logger.handlers:
                if not hasattr(handler, 'flush'):
                    if isinstance(handler, logging.StreamHandler):
                        handler.flush = lambda: sys.stdout.flush()
                    elif isinstance(handler, RotatingFileHandler):
                        handler.flush = lambda: handler.stream.flush()
        
        return logger
