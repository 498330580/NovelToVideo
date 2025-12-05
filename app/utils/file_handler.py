"""文件处理工具模块"""
import os
import shutil
from pathlib import Path
from app.utils.logger import get_logger
import chardet

logger = get_logger(__name__)


class FileHandler:
    """文件处理工具类"""
    
    @staticmethod
    def ensure_dir(directory):
        """
        确保目录存在
        
        Args:
            directory: 目录路径
        """
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def delete_file(file_path):
        """
        删除文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否成功删除
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f'已删除文件: {file_path}')
                return True
            return False
        except Exception as e:
            logger.error(f'删除文件失败 {file_path}: {str(e)}')
            return False
    
    @staticmethod
    def delete_directory(directory):
        """
        删除目录及其内容
        
        Args:
            directory: 目录路径
            
        Returns:
            是否成功删除
        """
        try:
            if os.path.exists(directory):
                shutil.rmtree(directory)
                logger.info(f'已删除目录: {directory}')
                return True
            return False
        except Exception as e:
            logger.error(f'删除目录失败 {directory}: {str(e)}')
            return False
    
    @staticmethod
    def get_file_size(file_path):
        """
        获取文件大小
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件大小(字节)
        """
        try:
            return os.path.getsize(file_path)
        except Exception as e:
            logger.error(f'获取文件大小失败 {file_path}: {str(e)}')
            return 0
    
    @staticmethod
    def get_directory_size(directory):
        """
        获取目录大小
        
        Args:
            directory: 目录路径
            
        Returns:
            目录总大小(字节)
        """
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
        except Exception as e:
            logger.error(f'获取目录大小失败 {directory}: {str(e)}')
        
        return total_size
    
    @staticmethod
    def clean_temp_files(directory, max_age_hours=24):
        """
        清理临时文件
        
        Args:
            directory: 目录路径
            max_age_hours: 文件最大保留时间(小时)
        """
        import time
        
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    if os.path.exists(file_path):
                        file_age = current_time - os.path.getmtime(file_path)
                        if file_age > max_age_seconds:
                            FileHandler.delete_file(file_path)
                            logger.info(f'已清理过期临时文件: {file_path}')
        except Exception as e:
            logger.error(f'清理临时文件失败 {directory}: {str(e)}')
    
    @staticmethod
    def safe_filename(filename):
        """
        生成安全的文件名
        
        Args:
            filename: 原始文件名
            
        Returns:
            安全的文件名
        """
        import re
        
        # 移除或替换不安全的字符
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # 限制长度
        if len(safe_name) > 200:
            name, ext = os.path.splitext(safe_name)
            safe_name = name[:200-len(ext)] + ext
        
        return safe_name
    
    @staticmethod
    def copy_file(src, dst):
        """
        复制文件
        
        Args:
            src: 源文件路径
            dst: 目标文件路径
            
        Returns:
            是否成功复制
        """
        try:
            FileHandler.ensure_dir(os.path.dirname(dst))
            shutil.copy2(src, dst)
            logger.info(f'已复制文件: {src} -> {dst}')
            return True
        except Exception as e:
            logger.error(f'复制文件失败 {src} -> {dst}: {str(e)}')
            return False
    
    @staticmethod
    def detect_file_encoding(file_path):
        """
        检测文件编码
        
        Args:
            file_path: 文件路径
            
        Returns:
            (编码名称, 置信度)
        """
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
            
            # 使用chardet检测编码
            result = chardet.detect(raw_data)
            encoding = result.get('encoding', 'utf-8')
            confidence = result.get('confidence', 0)
            
            # 如果检测到None或置信度很低，尝试常见编码
            if not encoding or confidence < 0.5:
                encoding = 'utf-8'
            
            logger.info(f'文件编码检测: {file_path} -> {encoding} (置信度: {confidence})')
            return encoding, confidence
            
        except Exception as e:
            logger.error(f'编码检测失败 {file_path}: {str(e)}')
            return 'utf-8', 0
    
    @staticmethod
    def read_text_file(file_path):
        """
        读取文本文件，自动检测编码
        
        Args:
            file_path: 文件路径
            
        Returns:
            (文件内容, 使用的编码) 或 (None, None)
        """
        # 常见中文编码列表
        encodings = ['utf-8', 'gbk', 'gb2312', 'big5', 'utf-16', 'utf-8-sig']
        
        # 首先尝试使用chardet检测
        detected_encoding, confidence = FileHandler.detect_file_encoding(file_path)
        if detected_encoding and confidence > 0.7:
            encodings.insert(0, detected_encoding)
        
        # 尝试各种编码读取
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                    content = f.read()
                
                # 验证是否成功读取（检查是否有内容且包含有效字符）
                if content and len(content.strip()) > 0:
                    logger.info(f'成功使用编码 {encoding} 读取文件: {file_path}')
                    return content, encoding
            except (UnicodeDecodeError, LookupError, IOError) as e:
                logger.debug(f'尝试编码 {encoding} 失败: {str(e)}')
                continue
        
        logger.error(f'无法使用任何编码读取文件: {file_path}')
        return None, None
