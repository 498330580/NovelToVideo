"""视频生成服务"""
import os
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips
from app.models.text_segment import TextSegment
from app.models.video_segment import VideoSegment
from app.models.task import Task
from app.models.project import Project
from app.utils.logger import get_logger
from app.utils.file_handler import FileHandler
from config import DefaultConfig

logger = get_logger(__name__)


class VideoService:
    """视频生成服务类"""
    
    @staticmethod
    def generate_project_videos(project_id):
        """
        生成项目的所有视频
        
        Args:
            project_id: 项目ID
            
        Returns:
            (成功标志, 错误信息)
        """
        task_id = None
        project = None
        try:
            # 创建任务
            task_id = Task.create(project_id, Task.TYPE_VIDEO_GENERATION)
            Task.update_status(task_id, Task.STATUS_RUNNING)
            
            # 获取项目信息
            project = Project.get_by_id(project_id)
            if not project:
                error_msg = '项目不存在'
                Task.update_status(task_id, Task.STATUS_FAILED, error_msg)
                return False, error_msg
                
            config = project.config
            
            # 获取所有音频段落
            all_segments = TextSegment.get_by_project(project_id)
            completed_segments = TextSegment.get_completed_segments(project_id)
            
            # 检查音频合成进度是否达到100%
            if len(all_segments) == 0:
                error_msg = '没有音频段落'
                Task.update_status(task_id, Task.STATUS_FAILED, error_msg)
                return False, error_msg
            
            # 计算音频完成进度
            audio_progress = len(completed_segments) / len(all_segments) * 100
            
            # 只有当音频合成进度达到100%时才允许开始视频合成
            if audio_progress < 100:
                error_msg = f'音频合成进度未达到100% ({audio_progress:.1f}%)，无法开始视频合成'
                Task.update_status(task_id, Task.STATUS_FAILED, error_msg)
                return False, error_msg
            
            segments = completed_segments
            if not segments:
                error_msg = '没有已完成的音频段落'
                Task.update_status(task_id, Task.STATUS_FAILED, error_msg)
                return False, error_msg
            
            logger.info(f'开始视频生成: 项目ID={project_id}, 段落数={len(segments)}')
            
            # 确保临时目录存在
            temp_image_dir = os.path.join(DefaultConfig.TEMP_IMAGE_DIR, str(project_id))
            temp_video_dir = os.path.join(DefaultConfig.TEMP_VIDEO_DIR, str(project_id))
            FileHandler.ensure_dir(temp_image_dir)
            FileHandler.ensure_dir(temp_video_dir)
            
            # 生成背景图片
            background_image = VideoService._generate_background_image(
                project.name,
                config,
                temp_image_dir
            )
            
            # 生成视频片段
            video_clips = []
            for idx, segment in enumerate(segments):
                try:
                    clip = VideoService._create_video_clip(
                        segment.audio_path,
                        background_image,
                        config
                    )
                    video_clips.append(clip)
                    
                    # 更新进度
                    progress = (idx + 1) / len(segments) * 50  # 前50%进度
                    Task.update_progress(task_id, progress)
                    
                except Exception as e:
                    logger.error(f'创建视频片段失败: segment_id={segment.id}, error={str(e)}')
                    raise
            
            # 合并视频并按时长分片
            VideoService._merge_and_split_videos(
                project_id,
                video_clips,
                config,
                temp_video_dir,
                project.output_path,
                project.name,
                task_id
            )
            
            # 关闭所有视频片段
            for clip in video_clips:
                clip.close()
            
            Task.update_status(task_id, Task.STATUS_COMPLETED)
            Project.update_status(project_id, Project.STATUS_COMPLETED)
            
            logger.info(f'视频生成完成: 项目ID={project_id}')
            return True, None
            
        except Exception as e:
            logger.error(f'视频生成失败: {str(e)}', exc_info=True)
            if task_id:
                Task.update_status(task_id, Task.STATUS_FAILED, str(e))
            if project:
                Project.update_status(project_id, Project.STATUS_FAILED)
            return False, str(e)
    
    @staticmethod
    def _generate_background_image(project_name, config, temp_image_dir):
        """
        生成背景图片
        
        Args:
            project_name: 项目名称
            config: 配置字典
            temp_image_dir: 临时图片目录
            
        Returns:
            背景图片路径
        """
        # 检查是否使用自定义背景图片
        background_option = config.get('background_option', 'default')
        custom_background_path = config.get('custom_background_path')
        
        if background_option == 'custom' and custom_background_path and os.path.exists(custom_background_path):
            # 使用自定义背景图片
            logger.info(f'使用自定义背景图片: {custom_background_path}')
            
            # 获取目标分辨率
            resolution = config.get('resolution', DefaultConfig.DEFAULT_RESOLUTION)
            width, height = resolution
            
            # 调整自定义图片大小以匹配目标分辨率
            try:
                from PIL import Image
                custom_image = Image.open(custom_background_path)
                # 调整图片大小以适应目标分辨率（保持宽高比）
                custom_image = custom_image.resize((width, height), Image.Resampling.LANCZOS)
                
                # 保存调整后的图片到临时目录
                adjusted_image_path = os.path.join(temp_image_dir, 'custom_background.png')
                custom_image.save(adjusted_image_path)
                custom_image.close()
                
                logger.info(f'自定义背景图片调整完成: {adjusted_image_path}')
                return adjusted_image_path
            except Exception as e:
                logger.error(f'处理自定义背景图片失败: {e}')
                # 如果处理失败，继续使用默认背景生成
        
        # 使用默认背景生成（原有的逻辑）
        resolution = config.get('resolution', DefaultConfig.DEFAULT_RESOLUTION)
        width, height = resolution
        
        # 创建黑色背景
        image = Image.new('RGB', (width, height), color=0)
        draw = ImageDraw.Draw(image)
        
        # 使用默认字体
        font_size = int(height * 0.08)  # 字体大小为高度的8%
        try:
            # 尝试使用系统中文字体
            font = ImageFont.truetype("msyh.ttc", font_size)  # 微软雅黑
        except:
            try:
                font = ImageFont.truetype("simhei.ttf", font_size)  # 黑体
            except:
                font = ImageFont.load_default()
        
        # 计算文字位置(居中)
        text = project_name
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (width - text_width) / 2
        y = (height - text_height) / 2
        
        # 绘制白色文字
        draw.text((x, y), text, fill=(255, 255, 255), font=font)
        
        # 保存图片
        image_path = os.path.join(temp_image_dir, 'background.png')
        image.save(image_path)
        
        logger.info(f'背景图片生成成功: {image_path}')
        return image_path
    
    @staticmethod
    def _create_video_clip(audio_path, image_path, config):
        """
        创建视频片段
        
        Args:
            audio_path: 音频文件路径
            image_path: 图片文件路径
            config: 配置字典
            
        Returns:
            视频片段对象
        """
        fps = config.get('fps', DefaultConfig.DEFAULT_FPS)
        
        # 加载音频
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        
        # 创建图片视频
        image_clip = ImageClip(image_path, duration=duration)
        image_clip = image_clip.set_fps(fps)
        
        # 设置音频
        video_clip = image_clip.set_audio(audio_clip)
        
        return video_clip
    
    @staticmethod
    def _merge_and_split_videos(project_id, video_clips, config, temp_video_dir,
                                 output_path, project_name, task_id):
        """
        合并并分片视频
        
        Args:
            project_id: 项目ID
            video_clips: 视频片段列表
            config: 配置字典
            temp_video_dir: 临时视频目录
            output_path: 输出路径
            project_name: 项目名称
            task_id: 任务ID
        """
        segment_duration = config.get('segment_duration', DefaultConfig.DEFAULT_SEGMENT_DURATION)
        video_format = config.get('format', DefaultConfig.DEFAULT_FORMAT)
        bitrate = config.get('bitrate', DefaultConfig.DEFAULT_BITRATE)
        fps = config.get('fps', DefaultConfig.DEFAULT_FPS)
        
        # 合并所有视频片段
        logger.info('开始合并视频片段...')
        full_video = concatenate_videoclips(video_clips)
        total_duration = full_video.duration
        
        # 计算需要分成多少片
        num_segments = int(total_duration / segment_duration) + 1
        
        logger.info(f'视频总时长: {total_duration}秒, 分片数: {num_segments}')
        
        # 确保输出目录存在
        FileHandler.ensure_dir(output_path)
        
        # 分片导出
        safe_name = FileHandler.safe_filename(project_name)
        
        for i in range(num_segments):
            start_time = i * segment_duration
            end_time = min((i + 1) * segment_duration, total_duration)
            
            if start_time >= total_duration:
                break
            
            # 检查视频片段是否已存在
            output_filename = f'{safe_name}_{i+1}.{video_format}'
            output_file = os.path.join(output_path, output_filename)
            
            # 检查数据库中是否已记录该片段
            existing_segment = VideoSegment.get_by_project_and_index(project_id, i)
            
            # 如果文件已存在且大小大于0，则跳过
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                logger.info(f'视频片段已存在，跳过: {output_filename}')
                
                if not existing_segment:
                    # 保存到数据库
                    segment_id = VideoSegment.create(
                        project_id,
                        i,
                        end_time - start_time,
                        output_file
                    )
                    # 确保新创建的记录状态为completed
                    VideoSegment.update_status(segment_id, VideoSegment.STATUS_COMPLETED)
                else:
                    # 更新现有记录的状态为completed
                    VideoSegment.update_status(existing_segment.id, VideoSegment.STATUS_COMPLETED)
                
                # 更新进度
                progress = 50 + (i + 1) / num_segments * 50  # 后50%进度
                Task.update_progress(task_id, progress)
                
                continue
            
            # 如果文件不存在或大小为0，但数据库中有记录，需要更新数据库状态
            if existing_segment and (not os.path.exists(output_file) or os.path.getsize(output_file) == 0):
                # 将数据库中的记录状态更新为pending，表示需要重新处理
                VideoSegment.update_status(existing_segment.id, VideoSegment.STATUS_PENDING)
                logger.info(f'视频文件不存在，更新数据库状态为待处理: 索引 {i}')
            
            # 截取片段
            segment_clip = full_video.subclip(start_time, end_time)
            
            # 导出视频
            segment_clip.write_videofile(
                output_file,
                fps=fps,
                codec='libx264',
                bitrate=bitrate,
                audio_codec='aac',
                temp_audiofile=os.path.join(temp_video_dir, f'temp_audio_{i}.m4a'),
                remove_temp=True,
                logger=None  # 禁用moviepy的日志输出
            )
            
            # 检查数据库中是否已记录该片段
            existing_segment = VideoSegment.get_by_project_and_index(project_id, i)
            
            if not existing_segment:
                # 保存到数据库
                segment_id = VideoSegment.create(
                    project_id,
                    i,
                    end_time - start_time,
                    output_file
                )
                # 确保新创建的记录状态为completed
                VideoSegment.update_status(segment_id, VideoSegment.STATUS_COMPLETED)
            else:
                # 更新现有记录的状态为completed
                VideoSegment.update_status(existing_segment.id, VideoSegment.STATUS_COMPLETED)
            
            segment_clip.close()
            
            # 更新进度
            progress = 50 + (i + 1) / num_segments * 50  # 后50%进度
            Task.update_progress(task_id, progress)
            
            logger.info(f'视频片段导出成功: {output_filename}')
        
        # 关闭完整视频
        full_video.close()
        
        logger.info('所有视频片段导出完成')