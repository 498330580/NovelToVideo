"""项目相关路由"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from app.services.project_service import ProjectService
from app.services.task_scheduler import TaskScheduler
from app.models.project import Project
from app.models.text_segment import TextSegment
from app.utils.logger import get_logger
from app.utils.file_handler import FileHandler
from config import DefaultConfig
import os

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
        # 支持 JSON 和表单两种提交方式
        # 优先解析 JSON，若非 JSON 则回退到表单
        if request.is_json:
            data = request.get_json(silent=True) or {}
            name = str(data.get('name', '')).strip()
            description = str(data.get('description', '')).strip()
            text_content = str(data.get('text_content', '')).strip()
            # 解析配置（兼容字符串/列表/数值）
            resolution_val = data.get('resolution', '1920,1080')
            if isinstance(resolution_val, (list, tuple)) and len(resolution_val) == 2:
                resolution = (int(resolution_val[0]), int(resolution_val[1]))
            else:
                resolution = tuple(map(int, str(resolution_val).split(',')))
            fps = int(data.get('fps', 30))
            bitrate = str(data.get('bitrate', '2000k'))
            fmt = str(data.get('format', 'mp4'))
            segment_duration = int(data.get('segment_duration', 600))
            segment_mode = str(data.get('segment_mode', 'word_count'))
            max_words = int(data.get('max_words', 10000))
            voice = str(data.get('voice', 'zh-CN-XiaoxiaoNeural'))
            rate = str(data.get('rate', '+0%'))
            pitch = str(data.get('pitch', '+0Hz'))
            volume = str(data.get('volume', '+0%'))
        else:
            # 获取表单数据
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            text_content = request.form.get('text_content', '').strip()
            resolution = tuple(map(int, request.form.get('resolution', '1920,1080').split(',')))
            fps = int(request.form.get('fps', 30))
            bitrate = request.form.get('bitrate', '2000k')
            fmt = request.form.get('format', 'mp4')
            segment_duration = int(request.form.get('segment_duration', 600))
            segment_mode = request.form.get('segment_mode', 'word_count')
            max_words = int(request.form.get('max_words', 10000))
            voice = request.form.get('voice', 'zh-CN-XiaoxiaoNeural')
            rate = request.form.get('rate', '+0%')
            pitch = request.form.get('pitch', '+0Hz')
            volume = request.form.get('volume', '+0%')
        
        # 处理背景图片上传
        background_option = request.form.get('background_option', 'default')
        custom_background_path = None
        
        if background_option == 'custom' and 'background_image' in request.files:
            background_file = request.files['background_image']
            if background_file and background_file.filename:
                # 保存自定义背景图片
                safe_filename = FileHandler.safe_filename(background_file.filename)
                custom_background_path = os.path.join(DefaultConfig.TEMP_IMAGE_DIR, 'custom_backgrounds', safe_filename)
                FileHandler.ensure_dir(os.path.dirname(custom_background_path))
                background_file.save(custom_background_path)
        
        # 获取配置参数
        config = {
            'voice': voice,
            'rate': rate,
            'pitch': pitch,
            'volume': volume,
            'resolution': resolution,
            'fps': fps,
            'bitrate': bitrate,
            'format': fmt,
            'segment_duration': segment_duration,
            'segment_mode': segment_mode,
            'max_words': max_words,
            'background_option': background_option,
            'custom_background_path': custom_background_path
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
        
        # 不再自动提交任务，而是返回成功信息
        return jsonify({
            'success': True,
            'project_id': project_id,
            'message': '项目创建成功，请点击开始处理按钮启动任务'
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


@project_bp.route('/<int:project_id>/retry/tts', methods=['POST'])
def retry_tts(project_id):
    """重试语音合成任务
    
    - 将项目内失败的段落重置为待处理
    - 提交新的语音合成任务到调度器
    """
    try:
        project = ProjectService.get_project(project_id)
        if not project:
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        # 重置失败段落为待处理
        TextSegment.reset_audio_status_by_project(
            project_id,
            TextSegment.AUDIO_STATUS_FAILED,
            TextSegment.AUDIO_STATUS_PENDING
        )

        # 提交语音合成任务
        TaskScheduler.submit_tts_task(project_id)

        return jsonify({'success': True, 'message': '已提交重试语音合成任务'})
    except Exception as e:
        logger.error(f'重试语音合成失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': f'重试失败: {str(e)}'}), 500


@project_bp.route('/<int:project_id>/generate/video', methods=['POST'])
def generate_video(project_id):
    """提交视频生成任务"""
    try:
        project = ProjectService.get_project(project_id)
        if not project:
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        TaskScheduler.submit_video_task(project_id)
        return jsonify({'success': True, 'message': '已提交视频生成任务'})
    except Exception as e:
        logger.error(f'提交视频生成任务失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': f'提交失败: {str(e)}'}), 500


@project_bp.route('/<int:project_id>/start', methods=['POST'])
def start_processing(project_id):
    """开始处理项目任务
    
    - 提交语音合成任务到调度器
    """
    try:
        project = ProjectService.get_project(project_id)
        if not project:
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        # 检查项目状态
        if project.status != 'pending':
            return jsonify({'success': False, 'error': '项目状态不是待处理，无法开始处理'}), 400

        # 提交语音合成任务
        TaskScheduler.submit_tts_task(project_id)
        
        # 更新项目状态为处理中
        Project.update_status(project_id, Project.STATUS_PROCESSING)

        return jsonify({'success': True, 'message': '已提交语音合成任务'})
    except Exception as e:
        logger.error(f'开始处理任务失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': f'开始处理任务失败: {str(e)}'}), 500


@project_bp.route('/<int:project_id>/resegment', methods=['POST'])
def resegment(project_id):
    """重新分段文本并重置项目为待处理
    
    - 读取现有段落重构原始文本
    - 根据传入配置重新分段并写入数据库
    - 项目重置为待处理，可继续进行语音合成
    """
    try:
        project = ProjectService.get_project(project_id)
        if not project:
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        # 解析参数（JSON或表单），覆盖项目默认配置
        def _to_int(val, default):
            """安全转换为 int，None 或非法字符串时返回默认值"""
            try:
                return int(val)
            except (TypeError, ValueError):
                try:
                    return int(default)
                except Exception:
                    return 0
        if request.is_json:
            data = request.get_json(silent=True) or {}
            segment_mode = str(data.get('segment_mode', project.config.get('segment_mode', 'word_count') if isinstance(project.config, dict) else 'word_count'))
            default_max = project.config.get('max_words', 10000) if isinstance(project.config, dict) else 10000
            max_words = _to_int(data.get('max_words', default_max), default_max)
        else:
            default_mode = project.config.get('segment_mode', 'word_count') if isinstance(project.config, dict) else 'word_count'
            segment_mode = request.form.get('segment_mode', default_mode) or default_mode
            default_max = project.config.get('max_words', 10000) if isinstance(project.config, dict) else 10000
            max_words = _to_int(request.form.get('max_words', default_max), default_max)

        # 执行重新分段
        success, error = ProjectService.resegment_project(project_id, segment_mode, max_words)
        if not success:
            return jsonify({'success': False, 'error': error or '重新分段失败'}), 400

        return jsonify({'success': True, 'message': '重新分段完成，已重置为待处理'})
    except Exception as e:
        logger.error(f'重新分段失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': f'重新分段失败: {str(e)}'}), 500


@project_bp.route('/<int:project_id>/video/queue')
def view_video_queue(project_id):
    """查看视频合成队列"""
    try:
        project = ProjectService.get_project(project_id)
        if not project:
            flash('项目不存在', 'error')
            return redirect(url_for('project.index'))
        
        # 获取项目的所有视频合成队列
        from app.models.video_synthesis_queue import VideoSynthesisQueue
        queues = VideoSynthesisQueue.get_by_project(project_id)
        
        # 计算统计信息
        total_queues = len(queues)
        completed_count = len([q for q in queues if q.status == VideoSynthesisQueue.STATUS_COMPLETED])
        pending_count = len([q for q in queues if q.status == VideoSynthesisQueue.STATUS_PENDING])
        synthesizing_count = len([q for q in queues if q.status == VideoSynthesisQueue.STATUS_SYNTHESIZING])
        total_duration = sum(q.total_duration for q in queues)
        
        # 计算每个队列的已完成片段数和总片段数
        from app.models.temp_video_segment import TempVideoSegment
        queues_with_progress = []
        for queue in queues:
            completed_segments = len([s for s in queue.temp_segment_ids if TempVideoSegment.get_by_id(s) and TempVideoSegment.get_by_id(s).status == TempVideoSegment.STATUS_SYNTHESIZED])
            queues_with_progress.append({
                'queue': queue,
                'completed_segments': completed_segments,
                'total_segments': len(queue.temp_segment_ids)
            })
        
        return render_template(
            'video_queue.html',
            project=project,
            queues=queues_with_progress,
            total_queues=total_queues,
            completed_count=completed_count,
            pending_count=pending_count,
            synthesizing_count=synthesizing_count,
            total_duration=total_duration
        )
    except Exception as e:
        logger.error(f'查看视频队列失败: {str(e)}', exc_info=True)
        flash(f'查看视频队列失败: {str(e)}', 'error')
        return redirect(url_for('project.detail', project_id=project_id))
