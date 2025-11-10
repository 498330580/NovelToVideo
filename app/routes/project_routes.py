"""项目相关路由"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from app.services.project_service import ProjectService
from app.services.task_scheduler import TaskScheduler
from app.utils.logger import get_logger

logger = get_logger(__name__)

project_bp = Blueprint('project', __name__, url_prefix='/project')


@project_bp.route('/')
def index():
    """项目列表页面"""
    try:
        projects = ProjectService.get_all_projects()
        return render_template('project_list.html', projects=projects)
    except Exception as e:
        logger.error(f'获取项目列表失败: {str(e)}', exc_info=True)
        flash(f'获取项目列表失败: {str(e)}', 'error')
        return render_template('project_list.html', projects=[])


@project_bp.route('/create', methods=['GET', 'POST'])
def create():
    """创建项目"""
    if request.method == 'GET':
        return render_template('project_create.html')
    
    try:
        # 获取表单数据
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        text_content = request.form.get('text_content', '').strip()
        
        # 获取配置参数
        config = {
            'voice': request.form.get('voice', 'zh-CN-XiaoxiaoNeural'),
            'rate': request.form.get('rate', '+0%'),
            'pitch': request.form.get('pitch', '+0Hz'),
            'volume': request.form.get('volume', '+0%'),
            'resolution': tuple(map(int, request.form.get('resolution', '1920,1080').split(','))),
            'fps': int(request.form.get('fps', 30)),
            'bitrate': request.form.get('bitrate', '2000k'),
            'format': request.form.get('format', 'mp4'),
            'segment_duration': int(request.form.get('segment_duration', 600)),
            'segment_mode': request.form.get('segment_mode', 'word_count'),
            'max_words': int(request.form.get('max_words', 10000))
        }
        
        # 验证必填字段
        if not name:
            return jsonify({'success': False, 'error': '项目名称不能为空'}), 400
        
        if not text_content:
            return jsonify({'success': False, 'error': '文本内容不能为空'}), 400
        
        # 创建项目
        project_id, error = ProjectService.create_project(name, description, text_content, config)
        
        if error:
            return jsonify({'success': False, 'error': error}), 400
        
        # 提交语音合成任务
        TaskScheduler.submit_tts_task(project_id)
        
        return jsonify({
            'success': True,
            'project_id': project_id,
            'message': '项目创建成功,正在处理中...'
        })
        
    except Exception as e:
        logger.error(f'创建项目失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': f'创建项目失败: {str(e)}'}), 500


@project_bp.route('/<int:project_id>')
def detail(project_id):
    """项目详情页面"""
    try:
        project = ProjectService.get_project(project_id)
        if not project:
            flash('项目不存在', 'error')
            return redirect(url_for('project.index'))
        
        stats = ProjectService.get_project_statistics(project_id)
        
        return render_template('project_detail.html', project=project, stats=stats)
        
    except Exception as e:
        logger.error(f'获取项目详情失败: {str(e)}', exc_info=True)
        flash(f'获取项目详情失败: {str(e)}', 'error')
        return redirect(url_for('project.index'))


@project_bp.route('/<int:project_id>/delete', methods=['POST'])
def delete(project_id):
    """删除项目"""
    try:
        success, error = ProjectService.delete_project(project_id)
        
        if error:
            return jsonify({'success': False, 'error': error}), 400
        
        return jsonify({'success': True, 'message': '项目删除成功'})
        
    except Exception as e:
        logger.error(f'删除项目失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': f'删除项目失败: {str(e)}'}), 500


@project_bp.route('/<int:project_id>/stats')
def stats(project_id):
    """获取项目统计信息"""
    try:
        stats = ProjectService.get_project_statistics(project_id)
        
        if stats is None:
            return jsonify({'success': False, 'error': '项目不存在'}), 404
        
        return jsonify({'success': True, 'data': stats})
        
    except Exception as e:
        logger.error(f'获取项目统计失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': f'获取统计信息失败: {str(e)}'}), 500
