"""任务调度服务"""
import threading
from queue import Queue
from app.models.task import Task
from app.models.project import Project
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TaskScheduler:
    """任务调度服务类"""
    
    # 任务队列
    _task_queue = Queue()
    
    # 正在运行的任务
    _running_tasks = {}
    
    # 调度器线程
    _scheduler_thread = None
    
    # 运行标志
    _running = False
    
    # Flask应用实例
    _app = None
    
    @staticmethod
    def start(app=None):
        """启动任务调度器
        
        Args:
            app: Flask应用实例，用于在线程中推送应用上下文
        """
        if TaskScheduler._running:
            logger.warning('任务调度器已经在运行')
            return
        
        # 记录应用实例以便在线程中使用应用上下文
        if app is not None:
            TaskScheduler._app = app
        
        # 检查并重置系统重启后遗留的处理中项目
        try:
            TaskScheduler._reset_stale_processing_projects()
        except Exception as e:
            logger.warning(f'重置处理中项目状态时出错(可能是数据库未初始化): {str(e)}')
        
        TaskScheduler._running = True
        TaskScheduler._scheduler_thread = threading.Thread(
            target=TaskScheduler._schedule_loop,
            daemon=True
        )
        TaskScheduler._scheduler_thread.start()
        logger.info('任务调度器启动成功')
    
    @staticmethod
    def stop():
        """停止任务调度器"""
        TaskScheduler._running = False
        if TaskScheduler._scheduler_thread:
            TaskScheduler._scheduler_thread.join(timeout=5)
        logger.info('任务调度器已停止')
    
    @staticmethod
    def submit_tts_task(project_id):
        """
        提交语音合成任务
        
        Args:
            project_id: 项目ID
        """
        TaskScheduler._task_queue.put({
            'type': 'tts',
            'project_id': project_id
        })
        logger.info(f'语音合成任务已提交: 项目ID={project_id}')
    
    @staticmethod
    def submit_video_task(project_id):
        """
        提交视频生成任务
        
        Args:
            project_id: 项目ID
        """
        TaskScheduler._task_queue.put({
            'type': 'video',
            'project_id': project_id
        })
        logger.info(f'视频生成任务已提交: 项目ID={project_id}')
    
    @staticmethod
    def _schedule_loop():
        """任务调度循环"""
        import time
        
        while TaskScheduler._running:
            try:
                # 从队列获取任务(非阻塞)
                if not TaskScheduler._task_queue.empty():
                    task_info = TaskScheduler._task_queue.get(timeout=1)
                    
                    # 执行任务
                    TaskScheduler._execute_task(task_info)
                else:
                    # 没有任务时短暂休眠
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f'任务调度异常: {str(e)}', exc_info=True)
                time.sleep(1)
    
    @staticmethod
    def _execute_task(task_info):
        """
        执行任务
        
        Args:
            task_info: 任务信息字典
        """
        task_type = task_info['type']
        project_id = task_info['project_id']
        
        # 在新线程中执行任务
        if task_type == 'tts':
            thread = threading.Thread(
                target=TaskScheduler._run_tts_task,
                args=(project_id,),
                daemon=True
            )
            thread.start()
            TaskScheduler._running_tasks[project_id] = thread
            
        elif task_type == 'video':
            thread = threading.Thread(
                target=TaskScheduler._run_video_task,
                args=(project_id,),
                daemon=True
            )
            thread.start()
            TaskScheduler._running_tasks[project_id] = thread
    
    @staticmethod
    def _run_tts_task(project_id):
        """
        运行语音合成任务
        
        Args:
            project_id: 项目ID
        """
        try:
            from app.services.tts_service import TTSService
            
            # 在线程内推送应用上下文，避免数据库访问报错
            if TaskScheduler._app is not None:
                with TaskScheduler._app.app_context():
                    logger.info(f'开始执行语音合成任务: 项目ID={project_id}')
                    success, error = TTSService.synthesize_project(project_id)
            else:
                logger.info(f'开始执行语音合成任务: 项目ID={project_id}')
                success, error = TTSService.synthesize_project(project_id)
            
            if success:
                logger.info(f'语音合成任务完成: 项目 ID={project_id}')
                            
                # 第一步: 自动生成视频合成队列
                logger.info(f'开始自动生成视频合成队列: 项目 ID={project_id}')
                try:
                    from app.services.video_service import VideoService
                    queue_success = VideoService.generate_and_save_queue(project_id)
                    if queue_success:
                        logger.info(f'视频合成队列生成成功: 项目 ID={project_id}')
                    else:
                        logger.warning(f'视频合成队列生成失败: 项目 ID={project_id}')
                except Exception as e:
                    logger.error(f'自动生成队列异常: 项目 ID={project_id}, {str(e)}', exc_info=True)
                            
                # 第二步: 自动提交视频生成任务1
                TaskScheduler.submit_video_task(project_id)
            else:
                logger.error(f'语音合成任务失败: 项目ID={project_id}, 错误: {error}')
                
        except Exception as e:
            logger.error(f'语音合成任务异常: 项目ID={project_id}, {str(e)}', exc_info=True)
        finally:
            if project_id in TaskScheduler._running_tasks:
                del TaskScheduler._running_tasks[project_id]
    
    @staticmethod
    def _run_video_task(project_id):
        """
        运行视频生成任务
        
        Args:
            project_id: 项目ID
        """
        try:
            from app.services.video_service import VideoService
            
            # 在线程内推送应用上下文，避免数据库访问报错
            if TaskScheduler._app is not None:
                with TaskScheduler._app.app_context():
                    logger.info(f'开始执行视频生成任务: 项目ID={project_id}')
                    success, error = VideoService.generate_project_videos(project_id)
            else:
                logger.info(f'开始执行视频生成任务: 项目ID={project_id}')
                success, error = VideoService.generate_project_videos(project_id)
            
            if success:
                logger.info(f'视频生成任务完成: 项目ID={project_id}')
            else:
                logger.error(f'视频生成任务失败: 项目ID={project_id}, 错误: {error}')
                
        except Exception as e:
            logger.error(f'视频生成任务异常: 项目ID={project_id}, {str(e)}', exc_info=True)
        finally:
            if project_id in TaskScheduler._running_tasks:
                del TaskScheduler._running_tasks[project_id]
    
    @staticmethod
    def get_running_tasks():
        """
        获取正在运行的任务
        
        Returns:
            运行中的任务项目ID列表
        """
        return list(TaskScheduler._running_tasks.keys())
    
    @staticmethod
    def _reset_stale_processing_projects():
        """
        重置系统重启后遗留的处理中项目
        - 根据项目的实际进度智能重置状态
        - 如果音频已完全合成，设置为FAILED（等待用户重新生成视频）
        - 如果音频未完全合成，重置为PENDING（需要重新合成语音）
        - 将状态为running的任务重置为failed
        """
        try:
            from app.models.project import Project
            from app.models.task import Task
            from app.models.text_segment import TextSegment
            
            # 在线程内推送应用上下文，避免数据库访问报错
            if TaskScheduler._app is not None:
                with TaskScheduler._app.app_context():
                    # 重置处理中的项目状态
                    projects = Project.get_all()
                    reset_count = 0
                    failed_count = 0
                    
                    for project in projects:
                        if project.status == Project.STATUS_PROCESSING:
                            # 检查项目的音频完成情况
                            all_segments = TextSegment.get_by_project(project.id)
                            completed_segments = TextSegment.get_completed_segments(project.id)
                            
                            if all_segments and completed_segments:
                                audio_progress = (len(completed_segments) / len(all_segments)) * 100
                            else:
                                audio_progress = 0 if not all_segments else 100
                            
                            # 根据音频进度决定项目状态
                            if audio_progress >= 100:
                                # 音频已完全合成 → 设置为FAILED，等待用户点击生成视频
                                Project.update_status(project.id, Project.STATUS_FAILED)
                                logger.info(f'项目{project.id}音频已完成，重启后设置为失败状态，等待用户重新生成视频')
                                failed_count += 1
                            else:
                                # 音频未完全合成 → 重置为PENDING，需要重新合成
                                Project.update_status(project.id, Project.STATUS_PENDING)
                                logger.info(f'项目{project.id}音频进度{audio_progress:.1f}%，重启后重置为待处理')
                                reset_count += 1
                    
                    if reset_count > 0:
                        logger.info(f'重置了 {reset_count} 个处理中的项目状态为待处理（需要重新合成语音）')
                    if failed_count > 0:
                        logger.info(f'设置了 {failed_count} 个处理中的项目为失败状态（等待生成视频）')
                    
                    # 重置运行中的任务状态
                    tasks = Task.get_running_tasks()
                    if tasks:
                        for task in tasks:
                            Task.update_status(task.id, Task.STATUS_FAILED, '系统重启导致任务中断')
                        logger.info(f'重置了 {len(tasks)} 个运行中的任务状态为失败')
            else:
                # 无应用上下文时的简化处理
                projects = Project.get_all()
                reset_count = 0
                for project in projects:
                    if project.status == Project.STATUS_PROCESSING:
                        # 检查项目的音频完成情况
                        all_segments = TextSegment.get_by_project(project.id)
                        completed_segments = TextSegment.get_completed_segments(project.id)
                        
                        if all_segments and completed_segments:
                            audio_progress = (len(completed_segments) / len(all_segments)) * 100
                        else:
                            audio_progress = 0 if not all_segments else 100
                        
                        # 根据音频进度决定项目状态
                        if audio_progress >= 100:
                            Project.update_status(project.id, Project.STATUS_FAILED)
                            logger.info(f'项目{project.id}音频已完成，重启后设置为失败状态，等待用户重新生成视频')
                        else:
                            Project.update_status(project.id, Project.STATUS_PENDING)
                            logger.info(f'项目{project.id}音频进度{audio_progress:.1f}%，重启后重置为待处理')
                        reset_count += 1
                
                if reset_count > 0:
                    logger.info(f'重置了 {reset_count} 个处理中的项目状态')
                
                tasks = Task.get_running_tasks()
                for task in tasks:
                    Task.update_status(task.id, Task.STATUS_FAILED, '系统重启导致任务中断')
        except Exception as e:
            logger.error(f'重置处理中项目状态失败: {str(e)}', exc_info=True)