"""项目模型"""
import os
import json
from datetime import datetime
from app.utils.database import execute_query
from config import DefaultConfig


class Project:
    """项目数据模型"""
    
    # 项目状态常量
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CANCELLED = 'cancelled'
    
    def __init__(self, id=None, name=None, description=None, created_at=None,
                 updated_at=None, status=STATUS_PENDING, output_path=None, config_json=None):
        self.id = id
        self.name = name
        self.description = description
        self.created_at = created_at
        self.updated_at = updated_at
        self.status = status
        self.output_path = output_path
        self.config_json = config_json
    
    @property
    def config(self):
        """获取配置字典"""
        if self.config_json:
            return json.loads(self.config_json)
        return {}
    
    @config.setter
    def config(self, value):
        """设置配置字典"""
        self.config_json = json.dumps(value, ensure_ascii=False)
    
    @classmethod
    def create(cls, name, description, output_path, config):
        """
        创建新项目
        
        Args:
            name: 项目名称
            description: 项目描述
            output_path: 输出路径
            config: 配置字典
            
        Returns:
            项目ID
        """
        config_json = json.dumps(config, ensure_ascii=False)
        
        query = '''
            INSERT INTO projects (name, description, output_path, config_json)
            VALUES (?, ?, ?, ?)
        '''
        
        project_id = execute_query(
            query,
            (name, description, output_path, config_json),
            fetch=False
        )
        
        return project_id
    
    @classmethod
    def get_by_id(cls, project_id):
        """
        根据ID获取项目
        
        Args:
            project_id: 项目ID
            
        Returns:
            Project对象或None
        """
        query = 'SELECT * FROM projects WHERE id = ?'
        rows = execute_query(query, (project_id,))
        
        if rows:
            return cls._from_row(rows[0])
        return None
    
    @classmethod
    def get_by_name(cls, name):
        """
        根据名称获取项目
        
        Args:
            name: 项目名称
            
        Returns:
            Project对象或None
        """
        query = 'SELECT * FROM projects WHERE name = ?'
        rows = execute_query(query, (name,))
        
        if rows:
            return cls._from_row(rows[0])
        return None
    
    @classmethod
    def get_all(cls):
        """
        获取所有项目
        
        Returns:
            Project对象列表
        """
        query = 'SELECT * FROM projects ORDER BY created_at DESC'
        rows = execute_query(query)
        
        return [cls._from_row(row) for row in rows]
    
    @classmethod
    def update_status(cls, project_id, status):
        """
        更新项目状态
        
        Args:
            project_id: 项目ID
            status: 新状态
        """
        query = '''
            UPDATE projects 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        '''
        execute_query(query, (status, project_id), fetch=False)
    
    @classmethod
    def delete(cls, project_id):
        """
        删除项目
        
        Args:
            project_id: 项目ID
        """
        query = 'DELETE FROM projects WHERE id = ?'
        execute_query(query, (project_id,), fetch=False)
    
    @staticmethod
    def convert_to_relative_path(absolute_path):
        """
        将绝对路径转换为相对路径
        相对于 output 目录
        
        Args:
            absolute_path: 绝对路径
            
        Returns:
            相对路径（仅目录名）
        """
        if not absolute_path:
            return None
        
        # 只保存目录名（最后一部分）
        return os.path.basename(absolute_path)
    
    @staticmethod
    def convert_to_absolute_path(relative_path):
        """
        将相对路径转换为绝对路径
        重建完整路径：output/{relative_path}
        
        Args:
            relative_path: 相对路径（通常是目录名）
            
        Returns:
            绝对路径
        """
        if not relative_path:
            return None
        
        # 如果已经是绝对路径，直接返回
        if os.path.isabs(relative_path):
            return relative_path
        
        # 拼接到 output 目录
        return os.path.join(DefaultConfig.OUTPUT_DIR, relative_path)
    
    def get_absolute_output_path(self):
        """
        获取绝对输出路径
        
        Returns:
            绝对路径
        """
        if not self.output_path:
            return None
        
        # 如果已经是绝对路径，直接返回
        if os.path.isabs(self.output_path):
            return self.output_path
        
        # 拼接到 output 目录
        return os.path.join(DefaultConfig.OUTPUT_DIR, self.output_path)
    
    @classmethod
    def _from_row(cls, row):
        """
        从数据库行创建对象
        
        Args:
            row: 数据库行
            
        Returns:
            Project对象
        """
        return cls(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            status=row['status'],
            output_path=row['output_path'],
            config_json=row['config_json']
        )
    
    def to_dict(self):
        """
        转换为字典
        
        Returns:
            项目信息字典
        """
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'status': self.status,
            'output_path': self.get_absolute_output_path(),  # 返回绝对路径供前端显示
            'config': self.config
        }
