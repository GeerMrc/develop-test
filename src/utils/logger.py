import logging
import os
from datetime import datetime
from src.utils.config import Config

def setup_logger(name, log_file=None):
    """设置日志记录器"""
    config = Config()
    
    # 获取日志目录
    log_dir = config.get('paths.logs', 'data/logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # 如果没有指定日志文件，使用默认格式
    if not log_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        prefix = config.get('logging.file_prefix', 'app')
        log_file = os.path.join(log_dir, f"{prefix}_{timestamp}.log")
    
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(config.get('logging.level', 'DEBUG'))
    
    # 添加文件处理器
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    
    # 添加控制台处理器
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # 设置格式
    formatter = logging.Formatter(
        config.get('logging.format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
        config.get('logging.date_format', '%Y-%m-%d %H:%M:%S')
    )
    
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    # 清除现有的处理器
    logger.handlers.clear()
    
    # 添加处理器
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger 