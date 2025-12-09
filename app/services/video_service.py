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
from app.services.hardware_optimizer import get_optimizer

logger = get_logger(__name__)


class VideoService:
    """视频生成服务类"""
    
    @staticmethod
    def generate_project_videos(project_id):
        """
        生成项目的所有视频
        
        新流程（智能分组合成）：
        1. 识别已完成的音频时长
        2. 按用户的 segment_duration 自动分组，选择时长最接近的音频合成
        3. 记录已合成的音频，不参与下一个视频合成
        4. 将临时文件保存在 temp 文件夹，然后移动到 output 文件夹
        
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
            
            # 检查磁盘空间是否足够
            if not VideoService._check_disk_space(segments, temp_video_dir):
                error_msg = '磁盘空间不足，无法生成视频'
                Task.update_status(task_id, Task.STATUS_FAILED, error_msg)
                return False, error_msg
            
            # 生成背景图片
            background_image = VideoService._generate_background_image(
                project.name,
                config,
                temp_image_dir
            )
            
            # 新流程：按 segment_duration 分组合成视频
            logger.info('开始按分组时长合成视频...')
            segment_duration = config.get('segment_duration', DefaultConfig.DEFAULT_SEGMENT_DURATION)
            output_path = project.get_absolute_output_path()
            safe_name = FileHandler.safe_filename(project.name)
            
            # 使用新的分组合成逻辑
            success = VideoService._synthesize_videos_by_duration(
                project_id,
                segments,
                config,
                background_image,
                segment_duration,
                temp_video_dir,
                output_path,
                safe_name,
                task_id
            )
            
            if not success:
                error_msg = '视频合成失败'
                Task.update_status(task_id, Task.STATUS_FAILED, error_msg)
                return False, error_msg
            
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
    def _synthesize_videos_by_duration(project_id, segments, config, background_image,
                                      segment_duration, temp_video_dir, output_path,
                                      safe_name, task_id):
        """
        按 segment_duration 分组合成视频
        
        流程：
        1. 从未合成音频中识别时长
        2. 选择相加时间最接近 segment_duration 的音频
        3. 为这批音频创建一个视频
        4. 记录已合成的音频，不参与后续合成
        5. 重复步骤1-4直到所有音频都被合成
        
        Args:
            project_id: 项目ID
            segments: 已完成的音频段落列表
            config: 配置字典
            background_image: 背景图片路径
            segment_duration: 目标分段时长(秒)
            temp_video_dir: 临时视频目录
            output_path: 输出目录
            safe_name: 安全的文件名
            task_id: 任务ID
            
        Returns:
            成功标志
        """
        import shutil
        from moviepy.editor import VideoFileClip, concatenate_videoclips
        
        fps = config.get('fps', DefaultConfig.DEFAULT_FPS)
        video_format = config.get('format', DefaultConfig.DEFAULT_FORMAT)
        bitrate = config.get('bitrate', DefaultConfig.DEFAULT_BITRATE)
        
        try:
            # 获取所有音频的时长信息
            # 优先从数据库读取，戗不然从音频文件扩描
            segment_durations = {}
            total_duration = 0
            missing_duration_count = 0
            
            logger.info(f'开始收集音频时长信息...')
            
            for segment in segments:
                try:
                    # 优先从数据库读取时长
                    if segment.audio_duration is not None and segment.audio_duration > 0:
                        duration = segment.audio_duration
                        segment_durations[segment.id] = duration
                        total_duration += duration
                    else:
                        # 如果数据库没有时长，从音频文件扩描
                        missing_duration_count += 1
                        audio_path = segment.get_absolute_audio_path()
                        if os.path.exists(audio_path):
                            from moviepy.editor import AudioFileClip
                            audio_clip = AudioFileClip(audio_path)
                            duration = audio_clip.duration
                            audio_clip.close()
                            segment_durations[segment.id] = duration
                            total_duration += duration
                            # 也要求保存到数据库以便下次使用
                            segment.audio_duration = duration
                except Exception as e:
                    logger.warning(f'获取音频时长失败: segment_id={segment.id}, error={str(e)}')
                    # 继续处理其他音频
            
            if missing_duration_count > 0:
                logger.info(f'从数据库成功读取：{len(segment_durations) - missing_duration_count}条记录, 需要扩描文件：{missing_duration_count}条记录')
            else:
                logger.info(f'从数据库成功读取每条记录的时长（不需要扩描音频文件）')
            
            if not segment_durations:
                logger.error('无法获取任何音频的时长信息')
                return False
            
            logger.info(f'总音频时长: {total_duration}s, 目标分段时长: {segment_duration}s')
            
            # 确保输出目录存在
            FileHandler.ensure_dir(output_path)
            
            # 实现断点续传：检查数据库中已完成的视频段落，恢复上次执行的程
            from app.models.video_segment import VideoSegment
            completed_video_segments = VideoSegment.get_by_project(project_id)
            completed_indices = set([seg.segment_index for seg in completed_video_segments 
                                     if seg.status == VideoSegment.STATUS_COMPLETED])
            
            # 检查是否有上次未完成的任务1
            # 仅处理已完成的视频，不处理未完成或失败的视频
            synthesized_segment_ids = set()
            if completed_indices:
                logger.info(f'检测到已有 {len(completed_indices)} 个已完成的视频段落 (video_1 ~ video_{max(completed_indices)})'
                          f'，开始断点续传...')
            
            video_index = max(completed_indices) + 1 if completed_indices else 1
            total_segments = len(segments)
            
            while len(synthesized_segment_ids) < total_segments:
                # 第一步：从未合成音频中选择相加时间最接近 segment_duration 的音频
                selected_segments = VideoService._select_segments_by_target_duration(
                    segments,
                    segment_durations,
                    synthesized_segment_ids,
                    segment_duration
                )
                
                if not selected_segments:
                    logger.warning('无法选择更多的音频段落，可能所有音频都已合成')
                    break
                
                selected_ids = [seg.id for seg in selected_segments]
                selected_duration = sum(segment_durations[seg_id] for seg_id in selected_ids)
                logger.info(f'视频 {video_index}: 选择 {len(selected_segments)} 个音频段落，总时长: {selected_duration:.2f}秒')
                
                # 检查此视频是否已经完成，如果完成则跳过
                output_filename = f'{safe_name}_{video_index}.{video_format}'
                output_file = os.path.join(output_path, output_filename)
                existing_video = VideoSegment.get_by_project_and_index(project_id, video_index - 1)
                
                if existing_video and existing_video.status == VideoSegment.STATUS_COMPLETED:
                    # 视频已完成，检查文件是否存在
                    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                        logger.info(f'视频 {video_index} 已完成（断点续传），正常跳过: {output_filename}')
                        # 标记这些音频为已合成
                        synthesized_segment_ids.update(selected_ids)
                        video_index += 1
                        progress = len(synthesized_segment_ids) / total_segments * 100
                        Task.update_progress(task_id, progress)
                        continue
                    else:
                        logger.warning(f'视频 {video_index} 预期为COMPLETED但视频文件不存在，重新源董: {output_filename}')
                
                # 第二步：为这批音频生成临时视频
                temp_video_files = []
                for idx, segment in enumerate(selected_segments):
                    try:
                        temp_video_file = os.path.join(temp_video_dir, f'segment_{segment.id}_{video_index}.mp4')
                        audio_abs_path = segment.get_absolute_audio_path()
                        VideoService._create_and_save_video_segment(
                            audio_abs_path,
                            background_image,
                            temp_video_file,
                            config
                        )
                        temp_video_files.append(temp_video_file)
                    except Exception as e:
                        logger.error(f'创建视频片段失败: segment_id={segment.id}, error={str(e)}')
                        raise
                
                # 第三步：合并这批视频并保存到输出目录
                try:
                    output_filename = f'{safe_name}_{video_index}.{video_format}'
                    output_file = os.path.join(output_path, output_filename)
                    
                    # 如果文件已存在，删除后重新生成
                    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                        logger.info(f'视频文件已存在，删除后重新生成: {output_filename}')
                        try:
                            os.remove(output_file)
                        except Exception as e:
                            logger.warning(f'删除旧视频文件失败: {output_filename}, 错误: {str(e)}')
                    
                    # 合并视频文件
                    logger.info(f'合并 {len(temp_video_files)} 个视频片段到: {output_filename}')
                    VideoService._merge_and_save_videos(
                        temp_video_files,
                        output_file,
                        config,
                        temp_video_dir
                    )
                    
                    # 记录视频段落到数据库
                    relative_video_path = os.path.join(safe_name, output_filename)
                    segment_id = VideoSegment.create(
                        project_id,
                        video_index - 1,
                        selected_duration,
                        relative_video_path
                    )
                    VideoSegment.update_status(segment_id, VideoSegment.STATUS_COMPLETED)
                    
                    logger.info(f'视频 {video_index} 生成成功: {output_filename}')
                    
                except Exception as e:
                    logger.error(f'合并和保存视频失败: error={str(e)}')
                    raise
                finally:
                    # 删除临时视频文件
                    for temp_file in temp_video_files:
                        try:
                            if os.path.exists(temp_file):
                                os.remove(temp_file)
                        except Exception as e:
                            logger.warning(f'删除临时视频文件失败: {temp_file}, 错误: {str(e)}')
                
                # 第四步：标记这批音频为已合成
                synthesized_segment_ids.update(selected_ids)
                video_index += 1
                
                # 更新进度
                progress = len(synthesized_segment_ids) / total_segments * 100
                Task.update_progress(task_id, progress)
            
            logger.info(f'所有视频生成完成，共生成 {video_index - 1} 个视频')
            return True
            
        except Exception as e:
            logger.error(f'按时长分组合成视频失败: {str(e)}', exc_info=True)
            return False
    
    @staticmethod
    def _select_segments_by_target_duration(segments, segment_durations, synthesized_ids, target_duration):
        """
        从未合成音频中选择相加时间最接近 target_duration 的音频
        
        使用贪心算法：按顺序遍历未合成的音频，选择总时长最接近目标时长的组合
        
        Args:
            segments: 所有音频段落列表
            segment_durations: 音频时长字典 {segment_id: duration}
            synthesized_ids: 已合成的音频ID集合
            target_duration: 目标总时长
            
        Returns:
            选中的 TextSegment 对象列表
        """
        # 获取未合成的音频段落和时长
        pending_segments = [s for s in segments if s.id not in synthesized_ids]
        pending_durations = {s.id: segment_durations[s.id] for s in pending_segments if s.id in segment_durations}
        
        if not pending_segments:
            return []
        
        # 使用贪心算法选择最接近目标时长的音频组合
        selected = []
        current_duration = 0
        
        for segment in pending_segments:
            if segment.id not in pending_durations:
                continue
            
            duration = pending_durations[segment.id]
            # 如果加上这个音频后时长不超过目标时长，则加入
            if current_duration + duration <= target_duration:
                selected.append(segment)
                current_duration += duration
            # 如果已经超过目标时长的一半，停止添加
            elif current_duration > target_duration * 0.5:
                break
        
        # 如果没有选中任何音频，选择第一个未合成的音频
        if not selected and pending_segments:
            selected = [pending_segments[0]]
        
        return selected
    
    @staticmethod
    def _merge_and_save_videos(temp_video_files, output_file, config, temp_video_dir):
        """
        合并多个视频文件并保存到输出位置
        
        Args:
            temp_video_files: 临时视频文件列表
            output_file: 输出文件路径
            config: 配置字典
            temp_video_dir: 临时视频目录
        """
        from moviepy.editor import VideoFileClip, concatenate_videoclips
        
        fps = config.get('fps', DefaultConfig.DEFAULT_FPS)
        bitrate = config.get('bitrate', DefaultConfig.DEFAULT_BITRATE)
        
        # 安全地解析resolution参数
        try:
            resolution = config.get('resolution', DefaultConfig.DEFAULT_RESOLUTION)
            if isinstance(resolution, str):
                resolution = tuple(map(int, resolution.split(',')))
            elif isinstance(resolution, (list, tuple)):
                resolution = tuple(resolution)
            else:
                resolution = DefaultConfig.DEFAULT_RESOLUTION
        except Exception as e:
            logger.warning(f'分辨率参数解析失败: {str(e)}, 使用默认分辨率')
            resolution = DefaultConfig.DEFAULT_RESOLUTION
        
        # 获取硬件优化参数
        try:
            optimizer = get_optimizer()
            optimal_params = optimizer.get_optimal_params(fps=fps, bitrate=bitrate, resolution=resolution)
            logger.info(f'合并视频优化参数: codec={optimal_params["codec"]}, preset={optimal_params["preset"]}, threads={optimal_params["threads"]}')
            # 刷新日志处理器，确保日志立即输出
            for handler in logger.handlers:
                if hasattr(handler, 'flush'):
                    try:
                        handler.flush()
                    except:
                        pass
        except Exception as e:
            logger.error(f'获取硬件优化参数失败: {str(e)}', exc_info=True)
            # 使用默认参数
            optimal_params = {
                'fps': fps,
                'bitrate': bitrate,
                'codec': 'libx264',
                'preset': 'ultrafast',
                'threads': 2
            }
        
        video_clips = []
        try:
            # 加载所有视频文件
            for temp_file in temp_video_files:
                if os.path.exists(temp_file):
                    try:
                        clip = VideoFileClip(temp_file)
                        video_clips.append(clip)
                    except Exception as e:
                        logger.warning(f'加载视频文件失败: {temp_file}, 错误: {str(e)}')
            
            if not video_clips:
                raise Exception('没有可用的视频片段')
            
            # 合并视频
            if len(video_clips) == 1:
                # 如果只有一个视频，直接复制
                merged_video = video_clips[0]
            else:
                merged_video = concatenate_videoclips(video_clips)
            
            # 保存到输出文件
            output_dir = os.path.dirname(output_file)
            FileHandler.ensure_dir(output_dir)
            
            # 准备视频写入选项，强制使用磁盘缓冲
            temp_audio_file = os.path.join(temp_video_dir, f'temp_audio_{os.path.basename(output_file)}.m4a')
            
            merged_video.write_videofile(
                output_file,
                fps=optimal_params['fps'],
                codec=optimal_params['codec'],
                bitrate=optimal_params['bitrate'],
                audio_codec='aac',
                temp_audiofile=temp_audio_file,
                remove_temp=True,
                logger=None,
                threads=optimal_params['threads']
            )
            
        finally:
            # 释放所有视频资源
            for clip in video_clips:
                try:
                    clip.close()
                except:
                    pass
    
    @staticmethod
    def _check_disk_space(segments, temp_dir):
        """
        检查磁盘空间是否足够
        
        Args:
            segments: 音频段落列表
            temp_dir: 临时目录路径
            
        Returns:
            bool: 是否有足够的磁盘空间
        """
        try:
            # 估算所需空间：假设每个音频段落生成的视频大约是音频的3倍大小
            estimated_size = 0
            for segment in segments:
                audio_path = segment.get_absolute_audio_path()
                if os.path.exists(audio_path):
                    audio_size = os.path.getsize(audio_path)
                    estimated_size += audio_size * 3  # 视频大约是音频的3倍
            
            # 检查临时目录可用空间
            stat = os.statvfs(temp_dir) if hasattr(os, 'statvfs') else None
            if stat:
                free_space = stat.f_frsize * stat.f_bavail
                return free_space > estimated_size * 2  # 需要至少2倍的估计空间
            
            # 如果无法检查磁盘空间，则假设有足够空间
            return True
        except Exception as e:
            logger.warning(f'检查磁盘空间时出错: {str(e)}')
            return True  # 出错时继续执行，但记录警告
    
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
        
        # 安全地解析resolution参数
        try:
            resolution = config.get('resolution', DefaultConfig.DEFAULT_RESOLUTION)
            if isinstance(resolution, str):
                resolution = tuple(map(int, resolution.split(',')))
            elif isinstance(resolution, (list, tuple)):
                resolution = tuple(resolution)
            else:
                resolution = DefaultConfig.DEFAULT_RESOLUTION
        except Exception as e:
            logger.warning(f'分辨率参数解析失败: {str(e)}, 使用默认分辨率')
            resolution = DefaultConfig.DEFAULT_RESOLUTION
        
        # 获取硬件优化参数
        try:
            optimizer = get_optimizer()
            optimal_params = optimizer.get_optimal_params(fps=fps, bitrate=bitrate, resolution=resolution)
            logger.debug(f'创建视频片段优化参数: codec={optimal_params["codec"]}, preset={optimal_params["preset"]}, threads={optimal_params["threads"]}')
            # 刷新日志处理器，确保日志立即输出
            for handler in logger.handlers:
                if hasattr(handler, 'flush'):
                    try:
                        handler.flush()
                    except:
                        pass
        except Exception as e:
            logger.error(f'获取硬件优化参数失败: {str(e)}', exc_info=True)
            # 使用默认参数
            optimal_params = {
                'fps': fps,
                'bitrate': bitrate,
                'codec': 'libx264',
                'preset': 'ultrafast',
                'threads': 2
            }
        
        # 初始化资源变量
        audio_clip = None
        image_clip = None
        video_clip = None
        pil_image = None
        
        try:
            # 检查输入文件是否存在
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"音频文件不存在: {audio_path}")
            
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"图片文件不存在: {image_path}")
            
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
            
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            FileHandler.ensure_dir(output_dir)
            
            # 立即保存到文件，强制使用磁盘缓冲
            output_dir = os.path.dirname(output_path)
            output_basename = os.path.basename(output_path)
            temp_audio_file = os.path.join(output_dir, f'{output_basename}_audio_temp.m4a')
            
            video_clip.write_videofile(
                output_path,
                fps=optimal_params['fps'],
                codec=optimal_params['codec'],
                bitrate=optimal_params['bitrate'],
                audio_codec='aac',
                temp_audiofile=temp_audio_file,
                remove_temp=True,
                logger=None,
                threads=optimal_params['threads']
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
            # 检查输入文件是否存在
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"音频文件不存在: {audio_path}")
            
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"图片文件不存在: {image_path}")
            
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
    
