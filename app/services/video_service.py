"""视频生成服务"""
import os
import numpy as np
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
        
        新流程（内存优化）：
        1. 逐个生成视频片段并保存到临时目录
        2. 从临时目录读取并合并视频
        3. 按时长分片并移动到输出目录
        
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
            
            # 第一阶段：逐个生成视频片段并保存到临时目录（避免内存溢出）
            logger.info('第一阶段：逐个生成视频片段到临时目录')
            temp_segment_files = []
            
            for idx, segment in enumerate(segments):
                try:
                    # 生成临时视频文件路径
                    temp_video_file = os.path.join(temp_video_dir, f'segment_{segment.id}.mp4')
                    
                    # 创建并保存单个视频片段
                    audio_abs_path = segment.get_absolute_audio_path()
                    VideoService._create_and_save_video_segment(
                        audio_abs_path,
                        background_image,
                        temp_video_file,
                        config
                    )
                    
                    temp_segment_files.append(temp_video_file)
                    
                    # 更新进度（第一阶段占50%）
                    progress = (idx + 1) / len(segments) * 50
                    Task.update_progress(task_id, progress)
                    
                    if (idx + 1) % 100 == 0:
                        logger.info(f'已生成 {idx + 1}/{len(segments)} 个视频片段')
                    
                except Exception as e:
                    logger.error(f'创建视频片段失败: segment_id={segment.id}, error={str(e)}')
                    raise
            
            logger.info(f'所有视频片段已生成到临时目录: {temp_video_dir}')
            
            # 第二阶段：从临时目录读取、合并并分片到输出目录
            VideoService._merge_temp_videos_and_split(
                project_id,
                temp_segment_files,
                config,
                temp_video_dir,
                project.get_absolute_output_path(),
                project.name,
                task_id
            )
            
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
    def _create_and_save_video_segment(audio_path, image_path, output_path, config):
        """
        创建单个视频片段并立即保存到文件（内存优化版本）
        
        优点：
        - 创建后立即保存到文件，不在内存中留存clip对象
        - 避免同时在内存中保留大量视频片段
        - 使用PIL直接读取图片，比imageio更高效
        
        Args:
            audio_path: 音频文件路径
            image_path: 图片文件路径
            output_path: 输出视频文件路径
            config: 配置字典
        """
        import numpy as np
        from moviepy.editor import ImageClip, AudioFileClip
        
        fps = config.get('fps', DefaultConfig.DEFAULT_FPS)
        bitrate = config.get('bitrate', DefaultConfig.DEFAULT_BITRATE)
        
        # 初始化资源变量
        audio_clip = None
        image_clip = None
        video_clip = None
        pil_image = None
        
        try:
            # 加载音频
            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration
            
            # 使用PIL直接读取图片
            pil_image = Image.open(image_path)
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # 转换为numpy数组
            image_array = np.array(pil_image)
            
            # 创建ImageClip
            image_clip = ImageClip(image_array, duration=duration)
            image_clip = image_clip.set_fps(fps)
            
            # 设置音频
            video_clip = image_clip.set_audio(audio_clip)
            
            # 立即保存到文件
            video_clip.write_videofile(
                output_path,
                fps=fps,
                codec='libx264',
                bitrate=bitrate,
                audio_codec='aac',
                temp_audiofile=output_path.replace('.mp4', '_temp.m4a'),
                remove_temp=True,
                logger=None
            )
            
        except MemoryError as e:
            logger.error(f'创建视频片段时内存不足: audio_path={audio_path}, error={str(e)}')
            raise
        except Exception as e:
            logger.error(f'创建视频片段失败: audio_path={audio_path}, error={str(e)}')
            raise
        finally:
            # 确保释放所有资源
            try:
                if video_clip:
                    video_clip.close()
            except:
                pass
            try:
                if audio_clip:
                    audio_clip.close()
            except:
                pass
            try:
                if image_clip:
                    image_clip.close()
            except:
                pass
            try:
                if pil_image:
                    pil_image.close()
            except:
                pass
    
    @staticmethod
    def _create_video_clip(audio_path, image_path, config):
        """
        创建视频片段（内存优化版本）
        
        使用 PIL 直接读取图片数据，避免 ImageClip 的重复加载导致的内存溢出
        
        Args:
            audio_path: 音频文件路径
            image_path: 图片文件路径
            config: 配置字典
            
        Returns:
            视频片段对象
        """
        import numpy as np
        from moviepy.editor import ImageClip, AudioFileClip
        
        fps = config.get('fps', DefaultConfig.DEFAULT_FPS)
        
        # 初始化资源变量
        audio_clip = None
        pil_image = None
        
        try:
            # 加载音频
            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration
            
            # 使用 PIL 直接读取图片，避免 ImageClip 的内存问题
            # PIL 的内存管理比 imageio 更高效
            pil_image = Image.open(image_path)
            # 转换为 RGB 格式（如果需要）
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # 转换为 numpy 数组
            image_array = np.array(pil_image)
            
            # 从 numpy 数组创建 ImageClip（这样可以避免 imageio 的内存溢出问题）
            image_clip = ImageClip(image_array, duration=duration)
            image_clip = image_clip.set_fps(fps)
            
            # 设置音频
            video_clip = image_clip.set_audio(audio_clip)
            
            return video_clip
            
        except MemoryError as e:
            logger.error(f'创建视频片段时内存不足: audio_path={audio_path}, error={str(e)}')
            raise
        except Exception as e:
            logger.error(f'创建视频片段失败: audio_path={audio_path}, error={str(e)}')
            raise
        finally:
            # 确保释放资源
            try:
                if audio_clip:
                    audio_clip.close()
            except:
                pass
            try:
                if pil_image:
                    pil_image.close()
            except:
                pass
    
    @staticmethod
    def _merge_temp_videos_and_split(project_id, temp_segment_files, config, temp_video_dir,
                                      output_path, project_name, task_id):
        """
        从临时目录读取视频片段、合并并分片（内存优化版本）
        
        处理流程：
        1. 从临时目录读取各个视频片段
        2. 合并为完整视频并保存到临时目录
        3. 从临时文件读取并按时长分片
        4. 分片视频移动到输出目录
        5. 删除临时文件
        
        Args:
            project_id: 项目ID
            temp_segment_files: 临时视频片段文件列表
            config: 配置字典
            temp_video_dir: 临时视频目录
            output_path: 输出路径
            project_name: 项目名称
            task_id: 任务ID
        """
        import shutil
        from moviepy.editor import VideoFileClip, concatenate_videoclips
        
        segment_duration = config.get('segment_duration', DefaultConfig.DEFAULT_SEGMENT_DURATION)
        video_format = config.get('format', DefaultConfig.DEFAULT_FORMAT)
        bitrate = config.get('bitrate', DefaultConfig.DEFAULT_BITRATE)
        fps = config.get('fps', DefaultConfig.DEFAULT_FPS)
        
        logger.info(f'开始合并 {len(temp_segment_files)} 个临时视频片段...')
        
        # 初始化资源变量
        video_clips = []
        full_video = None
        full_video_from_file = None
        
        try:
            # 1. 从临时文件读取视频片段
            for temp_file in temp_segment_files:
                if os.path.exists(temp_file):
                    clip = VideoFileClip(temp_file)
                    video_clips.append(clip)
                else:
                    logger.warning(f'临时视频文件不存在: {temp_file}')
            
            if not video_clips:
                raise Exception('没有可用的视频片段')
            
            # 2. 合并所有视频片段
            logger.info('合并视频片段...')
            full_video = concatenate_videoclips(video_clips)
            total_duration = full_video.duration
            
            # 计算需要分成多少片
            num_segments = int(total_duration / segment_duration) + 1
            logger.info(f'视频总时长: {total_duration}秒, 分片数: {num_segments}')
            
            # 3. 保存完整视频到临时文件
            temp_full_video_path = os.path.join(temp_video_dir, 'full_video.mp4')
            logger.info(f'保存完整视频到临时位置: {temp_full_video_path}')
            
            full_video.write_videofile(
                temp_full_video_path,
                fps=fps,
                codec='libx264',
                bitrate=bitrate,
                audio_codec='aac',
                temp_audiofile=os.path.join(temp_video_dir, 'temp_audio_merge.m4a'),
                remove_temp=True,
                logger=None
            )
            
            # 4. 释放内存中的完整视频对象
            if full_video:
                full_video.close()
            for clip in video_clips:
                try:
                    clip.close()
                except:
                    pass
            video_clips = []
            
            logger.info('完整视频已保存，开始分片处理...')
            
            # 5. 从临时文件读取完整视频进行分片
            full_video_from_file = VideoFileClip(temp_full_video_path)
            
            # 确保输出目录存在
            FileHandler.ensure_dir(output_path)
            
            # 分片导出
            safe_name = FileHandler.safe_filename(project_name)
            
            for i in range(num_segments):
                start_time = i * segment_duration
                end_time = min((i + 1) * segment_duration, total_duration)
                
                if start_time >= total_duration:
                    break
                
                # 输出文件路径
                output_filename = f'{safe_name}_{i+1}.{video_format}'
                output_file = os.path.join(output_path, output_filename)
                
                # 检查数据库中是否已记录该片段
                existing_segment = VideoSegment.get_by_project_and_index(project_id, i)
                
                # 如果文件已存在且大小大于0，则删除后重新生成
                if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                    logger.info(f'视频片段已存在，删除后重新生成: {output_filename}')
                    try:
                        os.remove(output_file)
                    except Exception as e:
                        logger.warning(f'删除旧视频片段失败: {output_filename}, 错误: {str(e)}')
                
                # 截取片段
                segment_clip = None
                try:
                    segment_clip = full_video_from_file.subclip(start_time, end_time)
                    
                    # 导出视频
                    logger.info(f'开始导出视频片段 ({i+1}/{num_segments}): {output_filename}')
                    segment_clip.write_videofile(
                        output_file,
                        fps=fps,
                        codec='libx264',
                        bitrate=bitrate,
                        audio_codec='aac',
                        temp_audiofile=os.path.join(temp_video_dir, f'temp_audio_{i}.m4a'),
                        remove_temp=True,
                        logger=None
                    )
                finally:
                    # 确保释放片段资源
                    if segment_clip:
                        try:
                            segment_clip.close()
                        except:
                            pass
                
                # 检查数据库中是否已记录该片段
                existing_segment = VideoSegment.get_by_project_and_index(project_id, i)
                
                if not existing_segment:
                    # 保存到数据库（使用相对路径）
                    relative_video_path = os.path.join(safe_name, output_filename)
                    segment_id = VideoSegment.create(
                        project_id,
                        i,
                        end_time - start_time,
                        relative_video_path
                    )
                    VideoSegment.update_status(segment_id, VideoSegment.STATUS_COMPLETED)
                else:
                    VideoSegment.update_status(existing_segment.id, VideoSegment.STATUS_COMPLETED)
                
                # 更新进度（第二阶段50%）
                progress = 50 + (i + 1) / num_segments * 50
                Task.update_progress(task_id, progress)
                
                logger.info(f'视频片段导出成功: {output_filename}')
            
            # 6. 关闭临时视频文件
            if full_video_from_file:
                full_video_from_file.close()
            
            # 7. 删除临时文件
            logger.info('开始清理临时文件...')
            try:
                # 删除完整视频临时文件
                if os.path.exists(temp_full_video_path):
                    os.remove(temp_full_video_path)
                    logger.info('删除临时完整视频文件')
                
                # 删除所有视频片段临时文件
                deleted_count = 0
                for temp_file in temp_segment_files:
                    if os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                            deleted_count += 1
                        except Exception as e:
                            logger.warning(f'删除临时视频片段失败: {temp_file}, 错误: {str(e)}')
                logger.info(f'删除 {deleted_count}/{len(temp_segment_files)} 个视频片段临时文件')
                
            except Exception as e:
                logger.warning(f'清理临时文件失败: {str(e)}')
            
            logger.info('所有视频片段导出完成')
            
        except Exception as e:
            logger.error(f'合并和分片视频时发生错误: {str(e)}', exc_info=True)
            raise
        finally:
            # 确保释放所有资源
            try:
                if full_video:
                    full_video.close()
            except:
                pass
            try:
                if full_video_from_file:
                    full_video_from_file.close()
            except:
                pass
            for clip in video_clips:
                try:
                    clip.close()
                except:
                    pass