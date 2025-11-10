"""任务相关路由"""
from flask import Blueprint, jsonify
from app.models.task import Task
from app.utils.logger import get_logger

logger = get_logger(__name__)

task_bp = Blueprint('task', __name__, url_prefix='/task')


@task_bp.route('/<int:task_id>')
def get_task(task_id):
    """获取任务信息"""
    try:
        task = Task.get_by_id(task_id)
        
        if not task:
            return jsonify({'success': False, 'error': '任务不存在'}), 404
        
        return jsonify({'success': True, 'data': task.to_dict()})
        
    except Exception as e:
        logger.error(f'获取任务信息失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': f'获取任务信息失败: {str(e)}'}), 500


@task_bp.route('/project/<int:project_id>')
def get_project_tasks(project_id):
    """获取项目的所有任务"""
    try:
        tasks = Task.get_by_project(project_id)
        
        return jsonify({
            'success': True,
            'data': [task.to_dict() for task in tasks]
        })
        
    except Exception as e:
        logger.error(f'获取项目任务失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': f'获取项目任务失败: {str(e)}'}), 500


@task_bp.route('/running')
def get_running_tasks():
    """获取所有运行中的任务"""
    try:
        tasks = Task.get_running_tasks()
        
        return jsonify({
            'success': True,
            'data': [task.to_dict() for task in tasks]
        })
        
    except Exception as e:
        logger.error(f'获取运行中任务失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': f'获取运行中任务失败: {str(e)}'}), 500
