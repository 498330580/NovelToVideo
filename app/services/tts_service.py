"""语音合成服务"""
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.models.text_segment import TextSegment
from app.models.task import Task
from app.models.project import Project
from app.utils.logger import get_logger
from app.utils.file_handler import FileHandler
from config import DefaultConfig

logger = get_logger(__name__)


class TTSService:
    """语音合成服务类"""
    
    # 线程池
    _executor = ThreadPoolExecutor(max_workers=DefaultConfig.MAX_THREAD_COUNT)
    
    @staticmethod
    def synthesize_project(project_id):
        """
        合成项目的所有语音
        
        Args:
            project_id: 项目ID
            
        Returns:
            (成功标志, 错误信息)
        """
        task_id = None
        try:
            # 创建任务
            task_id = Task.create(project_id, Task.TYPE_AUDIO_SYNTHESIS)
            Task.update_status(task_id, Task.STATUS_RUNNING)
            
            # 更新项目状态
            Project.update_status(project_id, Project.STATUS_PROCESSING)
            
            # 获取项目配置（容错：项目/配置可能为 None）
            project = Project.get_by_id(project_id)
            if not project:
                error_msg = '项目不存在，无法进行语音合成'
                Task.update_status(task_id, Task.STATUS_FAILED, error_msg)
                Project.update_status(project_id, Project.STATUS_FAILED)
                return False, error_msg
            config = project.config if isinstance(project.config, dict) else {}
            
            # 获取待处理的段落
            segments = TextSegment.get_pending_segments(project_id)
            total_segments = len(segments)
            
            if total_segments == 0:
                logger.info(f'没有待合成的段落: 项目ID={project_id}')
                # 无段落可处理，任务直接完成，并将项目状态更新为已完成，避免页面长时间处于“处理中”
                Task.update_status(task_id, Task.STATUS_COMPLETED)
                Project.update_status(project_id, Project.STATUS_COMPLETED)
                return True, None
            
            logger.info(f'开始语音合成: 项目ID={project_id}, 段落数={total_segments}')
            
            # 确保临时目录存在
            temp_audio_dir = os.path.join(DefaultConfig.TEMP_AUDIO_DIR, str(project_id))
            FileHandler.ensure_dir(temp_audio_dir)
            
            # 多线程处理
            completed_count = 0
            failed_count = 0
            
            for segment in segments:
                try:
                    TTSService._synthesize_segment(segment, config, temp_audio_dir)
                    completed_count += 1
                except Exception as e:
                    logger.error(f'段落语音合成失败: segment_id={segment.id}, error={str(e)}')
                    failed_count += 1
                
                # 更新进度
                progress = (completed_count + failed_count) / total_segments * 100
                Task.update_progress(task_id, progress)
            
            # 完成任务
            if failed_count == 0:
                Task.update_status(task_id, Task.STATUS_COMPLETED)
                logger.info(f'语音合成完成: 项目ID={project_id}')
                return True, None
            else:
                error_msg = f'部分段落合成失败: 成功{completed_count}, 失败{failed_count}'
                Task.update_status(task_id, Task.STATUS_FAILED, error_msg)
                # 更新项目状态为失败
                Project.update_status(project_id, Project.STATUS_FAILED)
                return False, error_msg
                
        except Exception as e:
            logger.error(f'语音合成失败: {str(e)}', exc_info=True)
            if task_id:
                Task.update_status(task_id, Task.STATUS_FAILED, str(e))
            # 更新项目状态为失败
            Project.update_status(project_id, Project.STATUS_FAILED)
            return False, str(e)
    
    @staticmethod
    def _synthesize_segment(segment, config, temp_audio_dir):
        """
        合成单个段落的语音
        
        Args:
            segment: 文本段落对象
            config: 配置字典
            temp_audio_dir: 临时音频目录
        """
        # 更新状态为合成中
        TextSegment.update_audio_status(segment.id, TextSegment.AUDIO_STATUS_SYNTHESIZING)
        
        # 音频文件路径
        audio_filename = f'segment_{segment.id}.mp3'
        audio_path = os.path.join(temp_audio_dir, audio_filename)
        
        # 获取语音参数
        voice = config.get('voice', DefaultConfig.DEFAULT_VOICE)
        rate = config.get('rate', DefaultConfig.DEFAULT_RATE)
        pitch = config.get('pitch', DefaultConfig.DEFAULT_PITCH)
        volume = config.get('volume', DefaultConfig.DEFAULT_VOLUME)
        
        # 文本内容防御性处理：空文本直接标记失败，避免 TTS 抛错
        safe_text = (segment.content or '').strip()
        if not safe_text:
            TextSegment.update_audio_status(segment.id, TextSegment.AUDIO_STATUS_FAILED)
            raise Exception('文本内容为空，无法合成语音')

        # 调用 Edge TTS 合成语音
        retry_count = 0
        max_retries = DefaultConfig.TTS_RETRY_COUNT
        
        while retry_count < max_retries:
            try:
                # 使用异步方式调用 edge-tts
                asyncio.run(TTSService._async_synthesize(
                    safe_text,
                    voice,
                    rate,
                    pitch,
                    volume,
                    audio_path
                ))
                
                # 验证文件是否生成
                if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                    # 更新状态为已完成
                    TextSegment.update_audio_status(
                        segment.id,
                        TextSegment.AUDIO_STATUS_COMPLETED,
                        audio_path
                    )
                    logger.info(f'段落语音合成成功: segment_id={segment.id}')
                    return
                else:
                    raise Exception('音频文件生成失败')
                    
            except Exception as e:
                retry_count += 1
                logger.warning(f'语音合成失败 (尝试 {retry_count}/{max_retries}): {str(e)}')
                
                if retry_count >= max_retries:
                    # 更新状态为失败
                    TextSegment.update_audio_status(segment.id, TextSegment.AUDIO_STATUS_FAILED)
                    raise Exception(f'语音合成失败,已重试{max_retries}次: {str(e)}')
    
    @staticmethod
    async def _async_synthesize(text, voice, rate, pitch, volume, output_path):
        """
        异步合成语音
        
        Args:
            text: 文本内容
            voice: 语音角色
            rate: 语速
            pitch: 音调
            volume: 音量
            output_path: 输出路径
        """
        try:
            import edge_tts
            
            communicate = edge_tts.Communicate(
                text,
                voice,
                rate=rate,
                pitch=pitch,
                volume=volume
            )
            
            await communicate.save(output_path)
            
        except Exception as e:
            logger.error(f'Edge TTS 调用失败: {str(e)}', exc_info=True)
            raise
