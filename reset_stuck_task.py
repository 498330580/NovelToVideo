#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""重置卡死的语音合成任务"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models.task import Task
from app.models.text_segment import TextSegment
from app.models.project import Project
from config import DevelopmentConfig

def reset_stuck_task(task_id):
    """重置卡死的任务"""
    app = create_app(DevelopmentConfig)
    
    with app.app_context():
        print(f"检查任务ID: {task_id}")
        
        # 获取任务信息
        task = Task.get_by_id(task_id)
        if not task:
            print(f"任务 {task_id} 不存在")
            return
            
        print(f"任务信息:")
        print(f"  任务类型: {task.task_type}")
        print(f"  任务状态: {task.status}")
        print(f"  任务进度: {task.progress}%")
        print(f"  错误信息: {task.error_message}")
        print(f"  创建时间: {task.created_at}")
        print(f"  开始时间: {task.started_at}")
        print(f"  完成时间: {task.completed_at}")
        
        # 获取项目信息
        project = Project.get_by_id(task.project_id)
        if not project:
            print(f"\n无法获取项目信息 (项目ID: {task.project_id})")
            return
            
        # 检查该项目中卡在synthesizing状态的文本段落
        segments = TextSegment.get_by_project(task.project_id)
        stuck_segments = [s for s in segments if s.audio_status == TextSegment.AUDIO_STATUS_SYNTHESIZING]
        
        if stuck_segments:
            print(f"\n发现 {len(stuck_segments)} 个卡在synthesizing状态的文本段落:")
            for segment in stuck_segments:
                print(f"  段落ID: {segment.id}, 索引: {segment.segment_index}, 状态: {segment.audio_status}")
                # 将这些段落状态重置为pending，以便可以重新处理
                TextSegment.update_audio_status(segment.id, TextSegment.AUDIO_STATUS_PENDING)
                print(f"  段落 {segment.id} 状态已重置为pending")
            print(f"\n总共重置了 {len(stuck_segments)} 个段落的状态")
        else:
            print("\n未发现卡在synthesizing状态的文本段落")
            
        # 如果任务状态是failed，我们可以尝试重新启动它
        if task.status == Task.STATUS_FAILED:
            print(f"\n任务 {task_id} 处于failed状态，可以尝试重新启动")
            # 这里我们不自动重启任务，而是提示用户可以手动重启

if __name__ == '__main__':
    if len(sys.argv) > 1:
        task_id = int(sys.argv[1])
        reset_stuck_task(task_id)
    else:
        print("请提供任务ID，例如: python reset_stuck_task.py 14")