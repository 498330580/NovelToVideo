"""硬件配置检测和视频合成参数智能优化模块

根据当前运行环境的硬件配置（CPU核心数、内存大小、GPU等）自动优化视频合成参数，
确保在不同配置的电脑上都能快速合成视频，同时避免内存溢出。

特别针对画面不变化的背景图+音频合成场景进行优化。
"""

import os
import platform
import psutil
import logging
from typing import Dict, Any
from app.utils.logger import get_logger

logger = get_logger(__name__)


class HardwareInfo:
    """硬件信息类"""
    
    def __init__(self):
        """检测当前系统的硬件信息"""
        # 系统信息
        self.system = platform.system()  # 'Windows', 'Linux', 'Darwin'
        self.machine = platform.machine()  # 'x86_64', 'arm64' 等
        
        # CPU信息
        self.cpu_count = os.cpu_count() or 4  # CPU逻辑核心数
        self.cpu_count_physical = psutil.cpu_count(logical=False) or (self.cpu_count // 2)  # 物理核心数
        
        # 内存信息
        self.memory_total_gb = psutil.virtual_memory().total / (1024 ** 3)
        self.memory_available_gb = psutil.virtual_memory().available / (1024 ** 3)
        
        # GPU信息
        self.has_cuda = self._check_cuda()
        self.has_opencl = self._check_opencl()
        
        self._log_hardware_info()
    
    def _check_cuda(self) -> bool:
        """检查是否支持CUDA (NVIDIA GPU)"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
        except Exception:
            return False
    
    def _check_opencl(self) -> bool:
        """检查是否支持OpenCL"""
        try:
            # 简单检查：在Linux上检查是否存在opencl库
            if self.system == 'Linux':
                result = os.system('ldconfig -p | grep -q libOpenCL') == 0
                return result
            # Windows上通过环境变量检查
            elif self.system == 'Windows':
                return 'OPENCL_VENDOR_PATH' in os.environ
            return False
        except Exception:
            return False
    
    def _log_hardware_info(self):
        """记录硬件信息到日志"""
        logger.info(f"系统信息: {self.system} {self.machine}")
        logger.info(f"CPU: {self.cpu_count} 逻辑核心, {self.cpu_count_physical} 物理核心")
        logger.info(f"内存: {self.memory_total_gb:.2f}GB 总量, {self.memory_available_gb:.2f}GB 可用")
        logger.info(f"GPU: CUDA={self.has_cuda}, OpenCL={self.has_opencl}")
    
    def get_info_dict(self) -> Dict[str, Any]:
        """获取硬件信息字典"""
        return {
            'system': self.system,
            'machine': self.machine,
            'cpu_count': self.cpu_count,
            'cpu_count_physical': self.cpu_count_physical,
            'memory_total_gb': self.memory_total_gb,
            'memory_available_gb': self.memory_available_gb,
            'has_cuda': self.has_cuda,
            'has_opencl': self.has_opencl,
        }


class VideoEncodingOptimizer:
    """视频编码参数优化器
    
    针对画面不变化的背景图+音频合成场景进行优化。
    在这个场景中，由于画面不变化，我们可以采用特殊的优化策略：
    1. 使用高效率编码器（如libx264的ultrafast预设）
    2. 合理分配CPU线程数
    3. 启用硬件加速（如果可用）
    4. 调整缓冲区大小
    """
    
    def __init__(self):
        """初始化优化器"""
        try:
            self.hardware = HardwareInfo()
            logger.info("硬件优化器初始化成功")
        except Exception as e:
            logger.error(f"硬件优化器初始化失败: {str(e)}", exc_info=True)
            # 使用默认硬件配置
            self.hardware = None
        self._optimal_params = None
    
    def get_optimal_params(self, 
                          fps: int = 30,
                          bitrate: str = '2000k',
                          resolution: tuple = (1920, 1080),
                          force_cpu: bool = False) -> Dict[str, Any]:
        """
        获取针对当前硬件的最优视频合成参数
        
        Args:
            fps: 帧率（默认30）
            bitrate: 比特率（默认'2000k'）
            resolution: 分辨率，(宽, 高)（默认(1920, 1080)）
            force_cpu: 强制使用CPU编码（用于调试或兼容性）
            
        Returns:
            优化后的参数字典
        """
        if self._optimal_params is None:
            self._optimal_params = self._calculate_optimal_params(fps, bitrate, resolution, force_cpu)
        
        return self._optimal_params
    
    def _calculate_optimal_params(self, fps: int, bitrate: str, 
                                 resolution: tuple, force_cpu: bool) -> Dict[str, Any]:
        """计算最优参数"""
        
        params = {
            'fps': fps,
            'bitrate': bitrate,
            'resolution': resolution,
            'codec': 'libx264',  # 默认编码器
            'preset': 'ultrafast',  # 编码预设
            'threads': 1,  # 编码线程数
            'use_hardware_accel': False,  # 是否使用硬件加速
            'buffer_size_mb': 100,  # 缓冲区大小（MB）
            'pixel_format': 'yuv420p',  # 像素格式
            'memory_efficient': False,  # 内存高效模式
        }
        
        # 如果硬件检测失败，使用默认参数
        if self.hardware is None:
            logger.warning("硬件检测失败，使用默认参数")
            return params
        
        # 根据硬件配置优化参数
        memory_gb = self.hardware.memory_total_gb
        cpu_cores = self.hardware.cpu_count
        cpu_physical_cores = self.hardware.cpu_count_physical
        
        logger.info(f"开始优化视频合成参数: CPU={cpu_cores}核, 内存={memory_gb:.2f}GB")
        
        # 1. 根据内存大小选择编码策略
        if memory_gb < 4:
            # 小内存设备（<4GB）：激进的内存优化
            params['memory_efficient'] = True
            params['buffer_size_mb'] = 50
            params['preset'] = 'ultrafast'
            params['threads'] = max(1, cpu_physical_cores // 2)
            logger.info(f"小内存模式(<4GB): 使用激进优化, 线程数={params['threads']}")
        
        elif memory_gb < 8:
            # 中等内存（4-8GB）：平衡的内存优化
            params['memory_efficient'] = True
            params['buffer_size_mb'] = 100
            params['preset'] = 'superfast'
            params['threads'] = max(1, cpu_physical_cores // 2)
            logger.info(f"中等内存模式(4-8GB): 使用平衡优化, 线程数={params['threads']}")
        
        elif memory_gb < 16:
            # 较好内存（8-16GB）：轻度内存优化
            params['memory_efficient'] = False
            params['buffer_size_mb'] = 150
            params['preset'] = 'superfast'
            params['threads'] = max(1, cpu_physical_cores - 1)
            logger.info(f"较好内存模式(8-16GB): 使用轻度优化, 线程数={params['threads']}")
        
        else:
            # 充足内存（>16GB）：充分利用硬件
            params['memory_efficient'] = False
            params['buffer_size_mb'] = 200
            params['preset'] = 'faster'
            params['threads'] = cpu_physical_cores
            logger.info(f"充足内存模式(>16GB): 充分利用硬件, 线程数={params['threads']}")
        
        # 2. 根据CPU核心数调整线程数
        # 对于视频编码，通常4个线程效率最高，超过8个线程收益递减
        if cpu_physical_cores <= 2:
            params['threads'] = 1
            params['preset'] = 'ultrafast'
        elif cpu_physical_cores <= 4:
            params['threads'] = 2
            params['preset'] = 'ultrafast'
        elif cpu_physical_cores <= 8:
            params['threads'] = max(2, min(4, cpu_physical_cores - 1))
            params['preset'] = 'superfast'
        else:
            params['threads'] = max(4, min(8, cpu_physical_cores - 2))
            params['preset'] = 'faster'
        
        # 3. 根据分辨率和帧率调整比特率
        width, height = resolution
        pixel_count = width * height
        target_bitrate = self._calculate_optimal_bitrate(pixel_count, fps, memory_gb)
        if target_bitrate:
            params['bitrate'] = target_bitrate
            logger.info(f"根据分辨率和内存调整比特率: {params['bitrate']}")
        
        # 4. 尝试启用硬件加速（如果可用且不强制CPU）
        if not force_cpu:
            if self.hardware.has_cuda and self._can_use_cuda_for_encoding():
                params['use_hardware_accel'] = True
                params['codec'] = 'hevc_nvenc'  # NVIDIA GPU编码器
                params['preset'] = 'fast'  # NVIDIA的预设
                params['threads'] = 0  # GPU编码不需要CPU线程
                logger.info("启用NVIDIA CUDA硬件加速")
            else:
                # 检查是否支持其他GPU加速方案
                amd_available = self._check_amd_encoding()
                if amd_available:
                    # 注意: h264_amf不支持preset参数，为avoid错误我们禁用硬件加速
                    params['use_hardware_accel'] = False
                    logger.info("检测到AMD GPU编码器，但不支持preset参数，降级为CPU编码")
                else:
                    # 检查macOS的硬件加速
                    if self.hardware.system == 'Darwin':
                        videotoolbox_available = self._check_videotoolbox_encoding()
                        if videotoolbox_available:
                            params['use_hardware_accel'] = True
                            params['codec'] = 'h264_videotoolbox'  # macOS硬件加速
                            params['preset'] = 'fast'
                            params['threads'] = 0
                            logger.info("启用macOS VideoToolbox硬件加速")
                        else:
                            params['use_hardware_accel'] = False
                            logger.info("macOS: 未检测到硬件加速，使用CPU软件编码")
                    else:
                        # Linux或其他平台
                        params['use_hardware_accel'] = False
                        logger.info(f"{self.hardware.system}平台: 使用CPU软件编码")
        
        logger.info(f"最终参数配置: codec={params['codec']}, preset={params['preset']}, "
                   f"threads={params['threads']}, buffer={params['buffer_size_mb']}MB, "
                   f"bitrate={params['bitrate']}, memory_efficient={params['memory_efficient']}")
        
        return params
    
    def _calculate_optimal_bitrate(self, pixel_count: int, fps: int, memory_gb: float) -> str:
        """根据分辨率、帧率和内存计算最优比特率
        
        对于静止背景的场景，可以使用较低的比特率
        """
        # 基础比特率计算：像素数 * 帧率 / 1000
        # 但由于是静止背景，可以减少20-40%
        base_bitrate = pixel_count * fps / 1000 * 0.6  # 减少40%用于静止背景
        
        # 根据内存情况调整
        if memory_gb < 4:
            base_bitrate *= 0.8  # 小内存时进一步降低10%
        
        # 转换为标准格式
        bitrate_k = max(500, min(base_bitrate, 5000))  # 限制在500k-5000k之间
        
        return f"{int(bitrate_k)}k"
    
    def _can_use_cuda_for_encoding(self) -> bool:
        """检查是否可以使用CUDA进行视频编码
        
        需要检查ffmpeg是否编译了NVIDIA支持
        """
        try:
            import subprocess
            result = subprocess.run(['ffmpeg', '-encoders'], 
                                  capture_output=True, text=True, timeout=5)
            return 'hevc_nvenc' in result.stdout or 'h264_nvenc' in result.stdout
        except Exception:
            return False
    
    def _check_amd_encoding(self) -> bool:
        """检查是否支持AMD GPU硬件加速编码
        
        检查ffmpeg是否编译了h264_amf编码器支持
        """
        try:
            import subprocess
            result = subprocess.run(['ffmpeg', '-encoders'], 
                                  capture_output=True, text=True, timeout=5)
            return 'h264_amf' in result.stdout or 'hevc_amf' in result.stdout
        except Exception:
            return False
    
    def _check_videotoolbox_encoding(self) -> bool:
        """检查是否支持macOS VideoToolbox硬件加速
        
        检查ffmpeg是否编译了videotoolbox编码器支持
        """
        try:
            import subprocess
            result = subprocess.run(['ffmpeg', '-encoders'], 
                                  capture_output=True, text=True, timeout=5)
            return 'h264_videotoolbox' in result.stdout or 'hevc_videotoolbox' in result.stdout
        except Exception:
            return False
    
    def get_encoding_options(self) -> Dict[str, Any]:
        """获取moviepy write_videofile方法的编码选项"""
        params = self.get_optimal_params()
        
        options = {
            'codec': params['codec'],
            'fps': params['fps'],
            'bitrate': params['bitrate'],
            'threads': params['threads'],
            'preset': params['preset'],
        }
        
        # 如果启用硬件加速，使用GPU编码器的特定参数
        if params['use_hardware_accel']:
            options['preset'] = 'fast'  # NVIDIA NVENC的预设
        
        return options
    
    def get_memory_efficient_config(self) -> Dict[str, Any]:
        """获取内存高效配置"""
        params = self.get_optimal_params()
        
        return {
            'write_logfile': False,  # 不写日志文件以节省I/O
            'verbose': False,
            'logger': None,  # moviepy不输出日志
            'threads': params['threads'],
            'buffer_size': params['buffer_size_mb'],
            'memory_efficient': params['memory_efficient'],
        }


# 全局优化器实例
_optimizer = None


def get_optimizer() -> VideoEncodingOptimizer:
    """获取全局优化器实例（单例模式）"""
    global _optimizer
    if _optimizer is None:
        _optimizer = VideoEncodingOptimizer()
    return _optimizer


def reset_optimizer():
    """重置全局优化器实例（用于测试）"""
    global _optimizer
    _optimizer = None
