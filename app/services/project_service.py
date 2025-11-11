"""项目管理服务"""
import os
import json
from app.models.project import Project
from app.models.text_segment import TextSegment
from app.models.task import Task
from app.utils.logger import get_logger
from app.utils.file_handler import FileHandler
from config import DefaultConfig

logger = get_logger(__name__)


class ProjectService:
    """项目管理服务类"""
    
    @staticmethod
    def create_project(name, description, text_content, config=None):
        """
        创建新项目
        
        Args:
            name: 项目名称
            description: 项目描述
            text_content: 小说文本内容
            config: 配置字典
            
        Returns:
            (项目ID, 错误信息)
        """
        try:
            # 检查项目名称是否已存在
            existing = Project.get_by_name(name)
            if existing:
                return None, f'项目名称 "{name}" 已存在'
            
            # 验证文本长度
            text_length = len(text_content)
            if text_length > DefaultConfig.MAX_PROJECT_TEXT_SIZE:
                return None, f'文本内容过大({text_length}字),超过最大限制({DefaultConfig.MAX_PROJECT_TEXT_SIZE}字)'
            
            # 使用默认配置
            if config is None:
                config = ProjectService._get_default_config()
            
            # 创建输出目录
            safe_name = FileHandler.safe_filename(name)
            output_path = os.path.join(DefaultConfig.OUTPUT_DIR, safe_name)
            FileHandler.ensure_dir(output_path)
            
            # 创建项目
            project_id = Project.create(name, description, output_path, config)
            
            logger.info(f'项目创建成功: {name} (ID: {project_id})')
            
            # 创建文本导入任务
            task_id = Task.create(project_id, Task.TYPE_TEXT_IMPORT)
            
            # 开始处理文本
            from app.services.text_processor import TextProcessor
            TextProcessor.process_text(project_id, text_content, config, task_id)
            
            return project_id, None
            
        except Exception as e:
            logger.error(f'创建项目失败: {str(e)}', exc_info=True)
            return None, f'创建项目失败: {str(e)}'
    
    @staticmethod
    def get_project(project_id):
        """
        获取项目信息
        
        Args:
            project_id: 项目ID
            
        Returns:
            项目对象或None
        """
        return Project.get_by_id(project_id)
    
    @staticmethod
    def get_all_projects():
        """
        获取所有项目
        
        Returns:
            项目列表
        """
        return Project.get_all()
    
    @staticmethod
    def delete_project(project_id):
        """
        删除项目
        
        Args:
            project_id: 项目ID
            
        Returns:
            (成功标志, 错误信息)
        """
        try:
            project = Project.get_by_id(project_id)
            if not project:
                return False, '项目不存在'
            
            # 删除输出文件
            if project.output_path and os.path.exists(project.output_path):
                FileHandler.delete_directory(project.output_path)
            
            # 删除临时文件
            temp_audio_path = os.path.join(DefaultConfig.TEMP_AUDIO_DIR, str(project_id))
            if os.path.exists(temp_audio_path):
                FileHandler.delete_directory(temp_audio_path)
            
            temp_image_path = os.path.join(DefaultConfig.TEMP_IMAGE_DIR, str(project_id))
            if os.path.exists(temp_image_path):
                FileHandler.delete_directory(temp_image_path)
            
            temp_video_path = os.path.join(DefaultConfig.TEMP_VIDEO_DIR, str(project_id))
            if os.path.exists(temp_video_path):
                FileHandler.delete_directory(temp_video_path)
            
            # 删除数据库记录(会级联删除相关的段落、视频片段和任务)
            Project.delete(project_id)
            
            logger.info(f'项目删除成功: {project.name} (ID: {project_id})')
            
            return True, None
            
        except Exception as e:
            logger.error(f'删除项目失败: {str(e)}', exc_info=True)
            return False, f'删除项目失败: {str(e)}'
    
    @staticmethod
    def get_project_statistics(project_id):
        """
        获取项目统计信息
        
        Args:
            project_id: 项目ID
            
        Returns:
            统计信息字典
        """
        try:
            project = Project.get_by_id(project_id)
            if not project:
                return None
            
            segments = TextSegment.get_by_project(project_id)
            tasks = Task.get_by_project(project_id)
            
            total_segments = len(segments)
            completed_segments = sum(1 for s in segments if s.audio_status == TextSegment.AUDIO_STATUS_COMPLETED)
            total_words = sum((s.word_count or 0) for s in segments)
            
            return {
                'total_segments': total_segments,
                'completed_segments': completed_segments,
                'pending_segments': total_segments - completed_segments,
                'total_words': total_words,
                'tasks': [t.to_dict() for t in tasks]
            }
            
        except Exception as e:
            logger.error(f'获取项目统计信息失败: {str(e)}', exc_info=True)
            return None

    @staticmethod
    def _get_default_config():
        """
        获取默认配置
        
        Returns:
            默认配置字典
        """
        return {
            'voice': DefaultConfig.DEFAULT_VOICE,
            'rate': DefaultConfig.DEFAULT_RATE,
            'pitch': DefaultConfig.DEFAULT_PITCH,
            'volume': DefaultConfig.DEFAULT_VOLUME,
            'resolution': DefaultConfig.DEFAULT_RESOLUTION,
            'fps': DefaultConfig.DEFAULT_FPS,
            'bitrate': DefaultConfig.DEFAULT_BITRATE,
            'format': DefaultConfig.DEFAULT_FORMAT,
            'segment_duration': DefaultConfig.DEFAULT_SEGMENT_DURATION,
            'segment_mode': DefaultConfig.DEFAULT_SEGMENT_MODE,
            'max_words': DefaultConfig.DEFAULT_MAX_WORDS
        }

    @staticmethod
    def resegment_project(project_id, segment_mode=None, max_words=None):
        """
        重新分段项目文本
        
        - 以现有段落内容重建原始文本
        - 删除旧段落并按新配置重新分段
        - 项目重置为待处理状态
        
        Args:
            project_id: 项目ID
            segment_mode: 分段模式（chapter/word_count）
            max_words: 单段最大字数
        
        Returns:
            (成功标志, 错误信息)
        """
        try:
            project = Project.get_by_id(project_id)
            if not project:
                return False, '项目不存在'

            # 获取现有段落，如果没有段落则无法重构文本
            segments = TextSegment.get_by_project(project_id)
            if not segments:
                return False, '项目暂无文本段落，无法重新分段'

            # 重建原始文本（按换行连接，保持自然段落分隔）
            # 过滤掉空内容，避免 join 报错
            text_content = '\n'.join([s.content for s in segments if s.content])

            # 删除旧段落
            TextSegment.delete_by_project(project_id)

            # 构造新配置（以项目配置为基础）
            config = project.config if isinstance(project.config, dict) else {}
            if segment_mode:
                config['segment_mode'] = segment_mode
            if max_words:
                config['max_words'] = max_words

            # 创建文本导入任务并重新分段
            task_id = Task.create(project_id, Task.TYPE_TEXT_IMPORT)

            from app.services.text_processor import TextProcessor
            ok, err = TextProcessor.process_text(project_id, text_content, config, task_id)
            if not ok:
                return False, err or '文本重新分段失败'

            return True, None
        except Exception as e:
            logger.error(f'重新分段失败: {str(e)}', exc_info=True)
            return False, f'重新分段失败: {str(e)}'
