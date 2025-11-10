"""配置相关路由"""
from flask import Blueprint, render_template, request, jsonify
from config import DefaultConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)

config_bp = Blueprint('config', __name__, url_prefix='/config')


@config_bp.route('/')
def index():
    """配置页面"""
    return render_template('config.html')


@config_bp.route('/default')
def get_default_config():
    """获取默认配置"""
    try:
        config = {
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
        
        return jsonify({'success': True, 'data': config})
        
    except Exception as e:
        logger.error(f'获取默认配置失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': f'获取默认配置失败: {str(e)}'}), 500


@config_bp.route('/voices')
def get_voices():
    """获取可用的语音列表"""
    try:
        # 常用的中文语音列表
        voices = [
            {'value': 'zh-CN-XiaoxiaoNeural', 'label': '晓晓 (女声)'},
            {'value': 'zh-CN-YunxiNeural', 'label': '云希 (男声)'},
            {'value': 'zh-CN-YunyangNeural', 'label': '云扬 (男声)'},
            {'value': 'zh-CN-XiaoyiNeural', 'label': '晓伊 (女声)'},
            {'value': 'zh-CN-YunjianNeural', 'label': '云健 (男声)'},
            {'value': 'zh-CN-XiaochenNeural', 'label': '晓辰 (女声)'},
            {'value': 'zh-CN-XiaohanNeural', 'label': '晓涵 (女声)'},
            {'value': 'zh-CN-XiaomengNeural', 'label': '晓梦 (女声)'},
            {'value': 'zh-CN-XiaomoNeural', 'label': '晓墨 (女声)'},
            {'value': 'zh-CN-XiaoqiuNeural', 'label': '晓秋 (女声)'},
            {'value': 'zh-CN-XiaoruiNeural', 'label': '晓睿 (女声)'},
            {'value': 'zh-CN-XiaoshuangNeural', 'label': '晓双 (女声)'},
            {'value': 'zh-CN-XiaoxuanNeural', 'label': '晓萱 (女声)'},
            {'value': 'zh-CN-XiaoyanNeural', 'label': '晓颜 (女声)'},
            {'value': 'zh-CN-XiaoyouNeural', 'label': '晓悠 (女声)'},
            {'value': 'zh-CN-XiaozhenNeural', 'label': '晓甄 (女声)'},
            {'value': 'zh-CN-YunfengNeural', 'label': '云枫 (男声)'},
            {'value': 'zh-CN-YunhaoNeural', 'label': '云皓 (男声)'},
            {'value': 'zh-CN-YunxiaNeural', 'label': '云夏 (男声)'},
            {'value': 'zh-CN-YunyeNeural', 'label': '云野 (男声)'},
            {'value': 'zh-CN-YunzeNeural', 'label': '云泽 (男声)'},
        ]
        
        return jsonify({'success': True, 'data': voices})
        
    except Exception as e:
        logger.error(f'获取语音列表失败: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': f'获取语音列表失败: {str(e)}'}), 500
