"""任务模型"""
from datetime import datetime
from app.utils.database import execute_query


class Task:
    """任务数据模型"""
    
    # 任务类型常量
    TYPE_TEXT_IMPORT = 'text_import'
    TYPE_AUDIO_SYNTHESIS = 'audio_synthesis'
    TYPE_VIDEO_GENERATION = 'video_generation'
    TYPE_VIDEO_MERGE = 'video_merge'
    
    # 任务状态常量
    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CANCELLED = 'cancelled'
    
    def __init__(self, id=None, project_id=None, task_type=None, status=STATUS_PENDING,
                 progress=0.0, error_message=None, started_at=None, completed_at=None,
                 created_at=None):
        self.id = id
        self.project_id = project_id
        self.task_type = task_type
        self.status = status
        self.progress = progress
        self.error_message = error_message
        self.started_at = started_at
        self.completed_at = completed_at
        self.created_at = created_at
    
    @classmethod
    def create(cls, project_id, task_type):
        """
        创建任务
        
        Args:
            project_id: 项目ID
            task_type: 任务类型
            
        Returns:
            任务ID
        """
        query = '''
            INSERT INTO tasks (project_id, task_type, status)
            VALUES (?, ?, ?)
        '''
        
        task_id = execute_query(
            query,
            (project_id, task_type, cls.STATUS_PENDING),
            fetch=False
        )
        
        return task_id
    
    @classmethod
    def get_by_id(cls, task_id):
        """
        根据ID获取任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            Task对象或None
        """
        query = 'SELECT * FROM tasks WHERE id = ?'
        rows = execute_query(query, (task_id,))
        
        if rows:
            return cls._from_row(rows[0])
        return None
    
    @classmethod
    def get_by_project(cls, project_id):
        """
        获取项目的所有任务
        
        Args:
            project_id: 项目ID
            
        Returns:
            Task对象列表
        """
        query = '''
            SELECT * FROM tasks 
            WHERE project_id = ? 
            ORDER BY created_at DESC
        '''
        rows = execute_query(query, (project_id,))
        
        return [cls._from_row(row) for row in rows]
    
    @classmethod
    def update_status(cls, task_id, status, error_message=None):
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
            error_message: 错误信息
        """
        if status == cls.STATUS_RUNNING:
            query = '''
                UPDATE tasks 
                SET status = ?, started_at = CURRENT_TIMESTAMP
                WHERE id = ?
            '''
            execute_query(query, (status, task_id), fetch=False)
        elif status in [cls.STATUS_COMPLETED, cls.STATUS_FAILED, cls.STATUS_CANCELLED]:
            if error_message:
                query = '''
                    UPDATE tasks 
                    SET status = ?, completed_at = CURRENT_TIMESTAMP, error_message = ?
                    WHERE id = ?
                '''
                execute_query(query, (status, error_message, task_id), fetch=False)
            else:
                query = '''
                    UPDATE tasks 
                    SET status = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                '''
                execute_query(query, (status, task_id), fetch=False)
        else:
            query = 'UPDATE tasks SET status = ? WHERE id = ?'
            execute_query(query, (status, task_id), fetch=False)
    
    @classmethod
    def update_progress(cls, task_id, progress):
        """
        更新任务进度
        
        Args:
            task_id: 任务ID
            progress: 进度(0-100)
        """
        query = 'UPDATE tasks SET progress = ? WHERE id = ?'
        execute_query(query, (progress, task_id), fetch=False)
    
    @classmethod
    def get_running_tasks(cls):
        """
        获取所有运行中的任务
        
        Returns:
            Task对象列表
        """
        query = 'SELECT * FROM tasks WHERE status = ? ORDER BY started_at'
        rows = execute_query(query, (cls.STATUS_RUNNING,))
        
        return [cls._from_row(row) for row in rows]
    
    @classmethod
    def _from_row(cls, row):
        """
        从数据库行创建对象
        
        Args:
            row: 数据库行
            
        Returns:
            Task对象
        """
        return cls(
            id=row['id'],
            project_id=row['project_id'],
            task_type=row['task_type'],
            status=row['status'],
            progress=row['progress'],
            error_message=row['error_message'],
            started_at=row['started_at'],
            completed_at=row['completed_at'],
            created_at=row['created_at']
        )
    
    def to_dict(self):
        """
        转换为字典
        
        Returns:
            任务信息字典
        """
        return {
            'id': self.id,
            'project_id': self.project_id,
            'task_type': self.task_type,
            'status': self.status,
            'progress': self.progress,
            'error_message': self.error_message,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'created_at': self.created_at
        }
