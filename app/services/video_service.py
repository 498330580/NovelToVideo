"""视频生成服务"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips
from app.models.text_segment import TextSegment
from app.models.video_segment import VideoSegment
from app.models.task import Task
from app.models.project import Project
from app.models.temp_video_segment import TempVideoSegment
from app.models.video_synthesis_queue import VideoSynthesisQueue
from app.utils.logger import get_logger
from app.utils.file_handler import FileHandler
from config import DefaultConfig
from app.services.hardware_optimizer import get_optimizer

logger = get_logger(__name__)


class VideoService:
    """视频生成服务类"""
    
    @staticmethod
    def generate_and_save_queue(project_id):
        """
        自动生成视频合成队列并保存到数据库
        
        流程：
        1. 获取所有已完成的音频
        2. 根据 segment_duration 自动分组
        3. 为每组创建 TempVideoSegment 和 VideoSynthesisQueue 记录
        
        Args:
            project_id: 项目ID
            
        Returns:
            成功标志
        """
        try:
            # 获取项目信息
            project = Project.get_by_id(project_id)
            if not project:
                logger.error(f'项目不存在: 项目ID={project_id}')
                return False
            
            config = project.config
            
            # 获取所有已完成的音频
            completed_segments = TextSegment.get_completed_segments(project_id)
            
            if not completed_segments:
                logger.warning(f'没有已完成的音频: 项目ID={project_id}')
                return False
            
            # 收集音频时长信息
            segment_durations = {}
            total_duration = 0
            
            for segment in completed_segments:
                try:
                    # 优先从数据库读取时长
                    if segment.audio_duration is not None and segment.audio_duration > 0:
                        duration = segment.audio_duration
                    else:
                        # 如果数据库没有时长，从音频文件读取
                        audio_path = segment.get_absolute_audio_path()
                        if os.path.exists(audio_path):
                            from moviepy.editor import AudioFileClip
                            audio_clip = AudioFileClip(audio_path)
                            duration = audio_clip.duration
                            audio_clip.close()
                        else:
                            logger.warning(f'音频文件不存在: {audio_path}')
                            duration = 0
                    
                    segment_durations[segment.id] = duration
                    total_duration += duration
                except Exception as e:
                    logger.error(f'读取音频时长失败: segment_id={segment.id}, {str(e)}')
                    segment_durations[segment.id] = 0
            
            logger.info(f'收集到音频时长信息: 项目ID={project_id}, 总时长={total_duration}s, 音频数={len(completed_segments)}')
            
            # 获取配置参数
            segment_duration = config.get('segment_duration', DefaultConfig.DEFAULT_SEGMENT_DURATION)
            output_path = project.get_absolute_output_path()
            safe_name = FileHandler.safe_filename(project.name)
            
            # 分组逻辑：选择时长最接近 segment_duration 的音频组合
            video_index = 1
            selected_segment_ids = set()  # 已选择的音频ID
            queue_count = 0
            
            logger.info(f'开始分组生成队列: segment_duration={segment_duration}s')
            
            while len(selected_segment_ids) < len(completed_segments):
                # 从未选择的音频中选择
                remaining_segments = [s for s in completed_segments if s.id not in selected_segment_ids]
                
                if not remaining_segments:
                    break
                
                # 使用贪心算法选择时长最接近 segment_duration 的组合
                best_group = []
                best_group_duration = 0
                best_diff = float('inf')
                
                # 尝试所有可能的组合（简化版：按顺序贪心选择）
                current_group = []
                current_duration = 0
                
                for segment in remaining_segments:
                    seg_duration = segment_durations.get(segment.id, 0)
                    
                    # 如果加入这个音频后时长更接近目标，就加入
                    if current_duration + seg_duration <= segment_duration:
                        current_group.append(segment)
                        current_duration += seg_duration
                    elif abs((current_duration + seg_duration) - segment_duration) < abs(current_duration - segment_duration):
                        # 即使超过目标也加入，因为更接近目标
                        current_group.append(segment)
                        current_duration += seg_duration
                        break
                    else:
                        # 不加入，准备下一组
                        break
                
                # 如果当前组为空，至少选择一个音频
                if not current_group:
                    current_group = [remaining_segments[0]]
                    current_duration = segment_durations.get(current_group[0].id, 0)
                
                # 创建 TempVideoSegment 记录
                temp_segment_ids = []
                for segment in current_group:
                    try:
                        # 为每个音频创建临时视频片段记录
                        # 注意：这里 temp_video_path 是占位符，实际路径在合成时生成
                        temp_video_path = os.path.join(
                            DefaultConfig.TEMP_VIDEO_DIR,
                            str(project_id),
                            f'segment_{segment.id}.mp4'
                        )
                        temp_segment_id = TempVideoSegment.create(
                            project_id=project_id,
                            text_segment_id=segment.id,
                            temp_video_path=temp_video_path
                        )
                        temp_segment_ids.append(temp_segment_id)
                        selected_segment_ids.add(segment.id)
                    except Exception as e:
                        logger.error(f'创建TempVideoSegment失败: segment_id={segment.id}, {str(e)}')
                
                # 创建 VideoSynthesisQueue 记录
                if temp_segment_ids:
                    try:
                        output_video_path = os.path.join(
                            output_path,
                            f'{safe_name}_{video_index:03d}.{config.get("format", "mp4")}'
                        )
                        queue_id = VideoSynthesisQueue.create(
                            project_id=project_id,
                            video_index=video_index,
                            output_video_path=output_video_path,
                            temp_segment_ids=temp_segment_ids,
                            total_duration=current_duration
                        )
                        logger.info(f'创建队列记录: queue_id={queue_id}, video_index={video_index}, segments={len(temp_segment_ids)}, duration={current_duration:.1f}s')
                        queue_count += 1
                        video_index += 1
                    except Exception as e:
                        logger.error(f'创建VideoSynthesisQueue失败: video_index={video_index}, {str(e)}')
            
            logger.info(f'队列生成完成: 项目ID={project_id}, 总队列数={queue_count}')
            return True
            
        except Exception as e:
            logger.error(f'生成队列失败: 项目ID={project_id}, {str(e)}', exc_info=True)
            return False
    
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
            # 清理临时目录中的孤立文件
            VideoService._cleanup_orphaned_temp_files(temp_video_dir)
            FileHandler.ensure_dir(output_path)
            
            # 调用新的队列驱动方法处理视频合成
            return VideoService._synthesize_from_queue(
                project_id,
                temp_video_dir,
                output_path,
                background_image,
                config,
                task_id
            )
            
        except Exception as e:
            logger.error(f'按时长分组合成视频失败: {str(e)}', exc_info=True)
            return False
    
    @staticmethod
    def _synthesize_from_queue(project_id, temp_video_dir, output_path, background_image, config, task_id):
        """
        使用 VideoSynthesisQueue 队列驱动的视频合成
        
        流程：
        1. 从 VideoSynthesisQueue 表读取待处理的队列
        2. 对每个队列生成临时视频
        3. 合并临时视频为最终视频
        4. 更新状态并清理临时文件
        
        Args:
            project_id: 项目ID
            temp_video_dir: 临时视频目录
            output_path: 输出目录
            background_image: 背景图片路径
            config: 配置字典
            task_id: 任务ID
            
        Returns:
            成功标志
        """
        try:
            logger.info(f'开始使用队列驱动的视频合成: project_id={project_id}')
            
            # 从数据库获取所有待处理的队列记录
            queue_records = VideoSynthesisQueue.get_by_project(project_id)
            
            if not queue_records:
                logger.error(f'没有找到视频合成队列: project_id={project_id}')
                return False
            
            logger.info(f'找到 {len(queue_records)} 个待处理的队列记录')
            
            # 统计进度
            total_queue = len(queue_records)
            completed_queue = 0
            
            # 为了判断是否是一个特别的列表类型，轫换为dict
            segment_map = {}
            all_segments = TextSegment.get_by_project(project_id)
            for seg in all_segments:
                segment_map[seg.id] = seg
            
            # 遍历所有队列记录
            for queue_record in queue_records:
                queue_id = queue_record.id
                video_index = queue_record.video_index
                output_video_path = queue_record.output_video_path
                temp_segment_ids = queue_record.temp_segment_ids  # TempVideoSegment ID列表
                total_duration = queue_record.total_duration
                
                logger.info(f'处理队列: queue_id={queue_id}, video_index={video_index}, temp_segments={len(temp_segment_ids)}')
                
                # 如果队列已完成，跳过
                if queue_record.status == VideoSynthesisQueue.STATUS_COMPLETED:
                    logger.info(f'队列 video_{video_index} 已完成，跳过')
                    completed_queue += 1
                    progress = completed_queue / total_queue * 100
                    Task.update_progress(task_id, progress)
                    continue
                
                # 更新队列状态为合成中
                VideoSynthesisQueue.update_status(queue_id, VideoSynthesisQueue.STATUS_SYNTHESIZING)
                
                try:
                    # 第一步：为每个临时视频片段生成视频
                    temp_video_files = []
                    temp_segment_records = []
                    
                    for temp_segment_id in temp_segment_ids:
                        # 获取 TempVideoSegment 记录
                        temp_seg_record = TempVideoSegment.get_by_id(temp_segment_id)
                        if not temp_seg_record:
                            logger.warning(f'TempVideoSegment 不存在: id={temp_segment_id}')
                            continue
                        
                        text_segment_id = temp_seg_record.text_segment_id
                        segment = segment_map.get(text_segment_id)
                        
                        if not segment:
                            logger.warning(f'TextSegment 不存在: id={text_segment_id}')
                            continue
                        
                        try:
                            temp_video_path = temp_seg_record.temp_video_path
                            
                            # 检查文件是否已存在（断点续传）
                            if os.path.exists(temp_video_path) and os.path.getsize(temp_video_path) > 0:
                                logger.debug(f'临时视频已存在，跳过生成')
                            else:
                                # 生成临时视频
                                audio_abs_path = segment.get_absolute_audio_path()
                                logger.info(f'生成临时视频: temp_segment_id={temp_segment_id}')
                                
                                VideoService._create_and_save_video_segment(
                                    audio_abs_path,
                                    background_image,
                                    temp_video_path,
                                    config
                                )
                            
                            # 更新状态为 synthesized
                            TempVideoSegment.update_status(temp_segment_id, TempVideoSegment.STATUS_SYNTHESIZED)
                            temp_video_files.append(temp_video_path)
                            temp_segment_records.append(temp_seg_record)
                        
                        except Exception as e:
                            logger.error(f'生成临时视频失败: temp_segment_id={temp_segment_id}, error={str(e)}')
                            raise
                    
                    if not temp_video_files:
                        logger.error(f'没有成功生成临时视频')
                        VideoSynthesisQueue.update_status(queue_id, VideoSynthesisQueue.STATUS_PENDING)
                        continue
                    
                    # 第二步：合并临时视频
                    logger.info(f'合并 {len(temp_video_files)} 个视频: video_index={video_index}')
                    
                    # 检查输出文件是否已存在
                    if os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 0:
                        try:
                            os.remove(output_video_path)
                            logger.info(f'删除已存在的输出视频')
                        except Exception as e:
                            logger.warning(f'删除失败: {str(e)}')
                    
                    # 需要或改造_merge_and_save_videos或使用FFmpeg
                    # 暂时使用旧方法
                    VideoService._merge_and_save_videos(
                        temp_video_files,
                        output_video_path,
                        config,
                        temp_video_dir
                    )
                    
                    # 第三步：更新数据库
                    relative_video_path = os.path.relpath(output_video_path, output_path)
                    segment_id = VideoSegment.create(
                        project_id,
                        video_index - 1,
                        total_duration,
                        relative_video_path
                    )
                    VideoSegment.update_status(segment_id, VideoSegment.STATUS_COMPLETED)
                    
                    logger.info(f'视频 video_{video_index} 算法完成')
                    
                    # 第四步：更新是否是 merged 並删除临时文件
                    for temp_segment_record in temp_segment_records:
                        # 更新为 merged
                        TempVideoSegment.update_status(temp_segment_record.id, TempVideoSegment.STATUS_MERGED)
                        
                        # 删除临时视频文件
                        try:
                            if os.path.exists(temp_segment_record.temp_video_path):
                                os.remove(temp_segment_record.temp_video_path)
                                logger.debug(f'删除临时文件: {temp_segment_record.temp_video_path}')
                        except Exception as e:
                            logger.warning(f'删除临时文件失败: {str(e)}')
                    
                    # 第五步：更新队列状态
                    VideoSynthesisQueue.update_status(queue_id, VideoSynthesisQueue.STATUS_COMPLETED)
                    logger.info(f'队列 video_{video_index} 处理完成')
                    
                except Exception as e:
                    logger.error(f'处理队列失败: queue_id={queue_id}, error={str(e)}')
                    # 恢复队列状态为待处理
                    VideoSynthesisQueue.update_status(queue_id, VideoSynthesisQueue.STATUS_PENDING)
                    continue
                
                finally:
                    completed_queue += 1
                    progress = completed_queue / total_queue * 100
                    Task.update_progress(task_id, progress)
            
            logger.info(f'所有队列处理完成')
            return True
            
        except Exception as e:
            logger.error(f'队列驱动的视频合成失败: {str(e)}', exc_info=True)
            return False
    
    @staticmethod
    def _cleanup_orphaned_temp_files(temp_video_dir):
        """
        清理临时目录中的孤立文件
        
        异常中断时，临时目录可能残留：
        - 未完成的视频片段（segment_*.mp4）
        - 音频临时文件（*.m4a）
        这些文件会被清理，重新启动时重新生成
        
        Args:
            temp_video_dir: 临时视频目录
        """
        if not os.path.exists(temp_video_dir):
            return
        
        try:
            cleaned_count = 0
            for filename in os.listdir(temp_video_dir):
                file_path = os.path.join(temp_video_dir, filename)
                # 清理所有临时文件（segment_*.mp4 和 *.m4a）
                if filename.startswith('segment_') or filename.endswith('.m4a'):
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                            cleaned_count += 1
                    except Exception as e:
                        logger.warning(f'清理临时文件失败: {filename}, 错误: {str(e)}')
            
            if cleaned_count > 0:
                logger.info(f'清理了 {cleaned_count} 个孤立的临时文件（异常中断的残留）')
        except Exception as e:
            logger.warning(f'清理临时目录失败: {str(e)}')
    
    @staticmethod
    def _validate_output_file_integrity(output_file):
        """
        验证输出视频文件的完整性
        
        检查项：
        1. 文件是否存在
        2. 文件大小是否大于0
        3. 文件是否是有效的视频（验证時長）
        
        Args:
            output_file: 视频文件路径
            
        Returns:
            True 如果文件有效，False 否则
        """
        if not os.path.exists(output_file):
            return False
        
        if os.path.getsize(output_file) == 0:
            logger.warning(f'输出文件大小为0: {output_file}')
            return False
        
        # 验证视频時長是否有效（通过尝试打开）
        try:
            from moviepy.editor import VideoFileClip
            clip = VideoFileClip(output_file)
            duration = clip.duration
            clip.close()
            if duration <= 0:
                logger.warning(f'输出视频時長不有效: {output_file}, duration={duration}')
                return False
            return True
        except Exception as e:
            logger.warning(f'输出视频文件验证失败（可能不完整）: {output_file}, 错误: {str(e)}')
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
        
        使用 FFmpeg -c copy 直接拼接视频（无需重新编码）
        
        Args:
            temp_video_files: 临时视频文件列表
            output_file: 输出文件路径
            config: 配置字典
            temp_video_dir: 临时视频目录
        """
        import subprocess
        
        if not temp_video_files:
            raise Exception('没有临时视频文件')
        
        try:
            # 如果只有一个文件，直接复制
            if len(temp_video_files) == 1:
                logger.info(f'只有一个视频文件，直接复制')
                output_dir = os.path.dirname(output_file)
                FileHandler.ensure_dir(output_dir)
                import shutil
                shutil.copy(temp_video_files[0], output_file)
                logger.info(f'文件复制完成: {output_file}')
                return
            
            # 使用 FFmpeg -c copy 直接拼接
            logger.info(f'开始使用 FFmpeg -c copy 拼接 {len(temp_video_files)} 个视频')
            
            # 创建文件列表（FFmpeg concat demuxer 需要）
            concat_file = os.path.join(temp_video_dir, 'concat_list.txt')
            with open(concat_file, 'w', encoding='utf-8') as f:
                for video_file in temp_video_files:
                    # FFmpeg concat demuxer 需要使用单引号引用文件路径
                    f.write(f"file '{os.path.abspath(video_file)}'\\n")
            
            logger.info(f'创建了 concat 文件: {concat_file}')
            
            # 执行 FFmpeg 命令
            output_dir = os.path.dirname(output_file)
            FileHandler.ensure_dir(output_dir)
            
            # 构造 FFmpeg 命令：使用 -c copy 不重新编码
            ffmpeg_cmd = [
                'ffmpeg',
                '-f', 'concat',              # 使用 concat demuxer
                '-safe', '0',                # 允许绝对路径
                '-i', concat_file,           # 输入文件列表
                '-c', 'copy',                # 直接复制，不重新编码
                '-y',                        # 覆盖输出文件
                output_file
            ]
            
            logger.info(f'FFmpeg 命令: {" ".join(ffmpeg_cmd)}')
            
            # 执行命令
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 最长 1 小时
            )
            
            if result.returncode != 0:
                error_msg = result.stderr
                logger.error(f'FFmpeg 拼接失败: {error_msg}')
                raise Exception(f'FFmpeg 传递器错误: {error_msg}')
            
            logger.info(f'视频拼接成功: {output_file}')
            
            # 清理 concat 文件
            try:
                os.remove(concat_file)
                logger.debug(f'清理 concat 文件')
            except Exception as e:
                logger.warning(f'清理 concat 文件失败: {str(e)}')
        
        except subprocess.TimeoutExpired:
            logger.error(f'FFmpeg 拼接超时')
            raise Exception('FFmpeg 拼接超时')
        except Exception as e:
            logger.error(f'视频拼接失败: {str(e)}')
            raise

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
    
