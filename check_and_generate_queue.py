#!/usr/bin/env python
"""检查项目状态并生成队列数据"""

import sys
sys.path.insert(0, '.')

from app import create_app
from app.models.text_segment import TextSegment
from app.models.video_synthesis_queue import VideoSynthesisQueue
from app.models.temp_video_segment import TempVideoSegment
from app.models.project import Project
from app.services.video_service import VideoService

# 创建应用上下文
app = create_app()
with app.app_context():
    # 获取项目信息
    project = Project.get_by_id(1)
    if not project:
        print("❌ 项目不存在")
        sys.exit(1)
    
    print(f"✓ 项目: {project.name} (ID={project.id})")
    print(f"  状态: {project.status}")
    print(f"  配置: {project.config}")
    
    # 获取已完成的音频
    completed_segments = TextSegment.get_completed_segments(1)
    print(f"\n✓ 已完成的音频: {len(completed_segments)} 个")
    
    for seg in completed_segments[:5]:  # 仅显示前5个
        print(f"  - ID={seg.id}, 时长={seg.audio_duration}s")
    
    if len(completed_segments) > 5:
        print(f"  ... 等等 {len(completed_segments) - 5} 个")
    
    # 检查是否已有队列
    existing_queues = VideoSynthesisQueue.get_by_project(1)
    print(f"\n现有队列: {len(existing_queues)} 个")
    if existing_queues:
        for q in existing_queues:
            print(f"  - Queue ID={q.id}, video_index={q.video_index}, status={q.status}")
    
    # 检查是否已有临时视频片段
    existing_temps = TempVideoSegment.get_by_project(1)
    print(f"现有临时视频片段: {len(existing_temps)} 个")
    
    # 生成队列
    print("\n" + "="*60)
    print("开始生成队列数据...")
    print("="*60)
    
    success = VideoService.generate_and_save_queue(1)
    
    if success:
        print("\n✓ 队列生成成功！")
        
        # 显示生成的队列
        queues = VideoSynthesisQueue.get_by_project(1)
        print(f"\n生成的队列: {len(queues)} 个")
        for q in queues:
            print(f"  Queue ID={q.id}")
            print(f"    - video_index={q.video_index}")
            print(f"    - output_video_path={q.output_video_path}")
            print(f"    - temp_segment_ids={q.temp_segment_ids}")
            print(f"    - total_duration={q.total_duration}s")
            print(f"    - status={q.status}")
        
        # 显示生成的临时视频片段
        temps = TempVideoSegment.get_by_project(1)
        print(f"\n生成的临时视频片段: {len(temps)} 个")
        for t in temps[:10]:
            print(f"  Temp ID={t.id}, text_segment_id={t.text_segment_id}, status={t.status}")
        
        if len(temps) > 10:
            print(f"  ... 等等 {len(temps) - 10} 个")
    else:
        print("\n❌ 队列生成失败")
        sys.exit(1)

    print("\n" + "="*60)
    print("✓ 所有操作完成！")
    print("="*60)
