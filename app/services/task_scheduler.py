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
        TaskScheduler._reset_stale_processing_projects()
        
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
                logger.info(f'语音合成任务完成: 项目ID={project_id}')
                # 自动提交视频生成任务
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
        """重置系统重启后遗留的处理中项目和运行中任务"""
        try:
            from app.models.project import Project
            from app.models.task import Task
            from app.models.text_segment import TextSegment
            from app.services.project_service import ProjectService
            
            # 获取所有状态为processing的项目
            # 在线程内推送应用上下文，避免数据库访问报错
            if TaskScheduler._app is not None:
                with TaskScheduler._app.app_context():
                    projects = Project.get_all()
                    for project in projects:
                        if project.status == Project.STATUS_PROCESSING:
                            # 将状态重置为pending，以便可以重新开始处理
                            Project.update_status(project.id, Project.STATUS_PENDING)
                            logger.info(f'重置项目状态: ID={project.id}, Name={project.name} 从 processing 到 pending')
                    
                    # 获取所有状态为running的任务并重置为failed
                    tasks = Task.get_running_tasks()
                    for task in tasks:
                        Task.update_status(task.id, Task.STATUS_FAILED, '系统重启导致任务中断')
                        logger.info(f'重置任务状态: ID={task.id}, Type={task.task_type} 从 running 到 failed')
                        
                    # 重新检查所有项目的状态，确保与任务状态和段落状态一致
                    projects = Project.get_all()
                    for project in projects:
                        # 获取项目统计信息
                        stats = ProjectService.get_project_statistics(project.id)
                        if stats:
                            # 检查任务状态来确定项目状态
                            running_tasks = [t for t in stats["tasks"] if t["status"] == "running"]
                            completed_tasks = [t for t in stats["tasks"] if t["status"] == "completed"]
                            failed_tasks = [t for t in stats["tasks"] if t["status"] == "failed"]
                            
                            # 获取段落状态
                            segments = TextSegment.get_by_project(project.id)
                            completed_segments = sum(1 for s in segments if s.audio_status == TextSegment.AUDIO_STATUS_COMPLETED)
                            pending_segments = sum(1 for s in segments if s.audio_status == TextSegment.AUDIO_STATUS_PENDING)
                            failed_segments = sum(1 for s in segments if s.audio_status == TextSegment.AUDIO_STATUS_FAILED)
                            
                            # 如果有运行中的任务，项目状态应该是processing
                            if running_tasks and project.status != Project.STATUS_PROCESSING:
                                Project.update_status(project.id, Project.STATUS_PROCESSING)
                                logger.info(f'更新项目状态: ID={project.id}, Name={project.name} 到 processing (有运行中任务)')
                            # 如果所有段落已完成且没有待处理段落，项目状态应该是completed
                            elif (completed_segments == len(segments) and 
                                  len(segments) > 0 and 
                                  project.status != Project.STATUS_COMPLETED):
                                Project.update_status(project.id, Project.STATUS_COMPLETED)
                                logger.info(f'更新项目状态: ID={project.id}, Name={project.name} 到 completed (所有段落已完成)')
                            # 如果有失败段落且没有已完成段落，项目状态应该是failed
                            elif (failed_segments > 0 and 
                                  completed_segments == 0 and 
                                  project.status not in [Project.STATUS_FAILED, Project.STATUS_COMPLETED]):
                                Project.update_status(project.id, Project.STATUS_FAILED)
                                logger.info(f'更新项目状态: ID={project.id}, Name={project.name} 到 failed (有失败段落)')
            else:
                projects = Project.get_all()
                for project in projects:
                    if project.status == Project.STATUS_PROCESSING:
                        # 将状态重置为pending，以便可以重新开始处理
                        Project.update_status(project.id, Project.STATUS_PENDING)
                        logger.info(f'重置项目状态: ID={project.id}, Name={project.name} 从 processing 到 pending')
                
                # 获取所有状态为running的任务并重置为failed
                tasks = Task.get_running_tasks()
                for task in tasks:
                    Task.update_status(task.id, Task.STATUS_FAILED, '系统重启导致任务中断')
                    logger.info(f'重置任务状态: ID={task.id}, Type={task.task_type} 从 running 到 failed')
        except Exception as e:
            logger.error(f'重置处理中项目状态失败: {str(e)}', exc_info=True)
