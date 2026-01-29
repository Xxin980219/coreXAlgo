import cv2
import numpy as np
import os
import random
from enum import Enum
from pathlib import Path
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List, Dict, Any
from ..utils.basic import set_logging
from ..utils.constants import IMAGE_TYPE_FORMAT


# 旋转类型枚举
class RotationType(Enum):
    """
    旋转类型枚举
    """
    CLOCKWISE_90 = '90'  # 顺时针90度
    COUNTERCLOCKWISE_90 = '270'  # 逆时针90度
    ROTATE_180 = '180'  # 180度旋转


class YOLODataPreprocessor:
    """
    YOLO数据预处理类
    
    专门用于处理YOLO格式数据集的数据预处理工具，主要功能包括：
    1. YOLO数据集旋转（支持顺时针90度、逆时针90度、180度旋转）
    2. 自动更新对应的YOLO标签坐标
    3. 批量处理多个数据集
    4. 支持多线程并行处理，提高效率
    5. 可选的原文件备份功能
    6. 内存优化，支持处理大图片
    """
    
    def __init__(self, verbose: bool = True):
        """
        初始化YOLO数据预处理器
        
        Args:
            verbose: 是否启用详细日志
        """
        # 初始化日志记录器
        self.logger = set_logging(name="YOLODataPreprocessor", verbose=verbose)
    
    def _rotate_image_and_labels(self, image_path: Path, txt_path: Path, rotation_type: str, backup_dir: Optional[Path] = None) -> bool:
        """
        旋转图片和对应的YOLO标签文件

        Args:
            image_path: 图片文件路径
            txt_path: 标签文件路径
            rotation_type: 旋转类型 ('90'顺时针90度, '270'逆时针90度, '180'180度)
            backup_dir: 备份目录，如果提供则备份原文件

        Returns:
            bool: 旋转是否成功
        """
        # 读取图片 - 内存优化：对于大图片，使用降采样减少内存使用
        try:
            # 尝试使用降采样读取图片，减少内存使用
            img = cv2.imread(str(image_path), cv2.IMREAD_REDUCED_COLOR_8)
            if img is None:
                # 如果降采样失败，使用普通读取
                img = cv2.imread(str(image_path))
                if img is None:
                    self.logger.error(f"无法读取图片: {image_path}")
                    return False
        except Exception as e:
            self.logger.error(f"读取图片失败: {e}")
            return False

        h, w = img.shape[:2]

        # 备份原文件
        if backup_dir:
            backup_dir = Path(backup_dir)
            backup_dir.mkdir(parents=True, exist_ok=True)

            # 备份图片
            img_backup_path = backup_dir / image_path.name
            shutil.copy2(image_path, img_backup_path)

            # 备份标签文件
            if txt_path.exists():
                txt_backup_path = backup_dir / txt_path.name
                shutil.copy2(txt_path, txt_backup_path)

        # 执行图片旋转
        if rotation_type == RotationType.CLOCKWISE_90.value:  # 顺时针90度
            rotated_img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        elif rotation_type == RotationType.COUNTERCLOCKWISE_90.value:  # 逆时针90度
            rotated_img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif rotation_type == RotationType.ROTATE_180.value:  # 180度旋转
            rotated_img = cv2.rotate(img, cv2.ROTATE_180)
        else:
            self.logger.error(f"无效的旋转类型: {rotation_type}")
            return False

        # 保存旋转后的图片（覆盖原文件）
        cv2.imwrite(str(image_path), rotated_img)
        self.logger.info(f"✓ 已旋转图片: {image_path.name} -> {rotation_type}度")

        # 处理标签文件
        if txt_path.exists():
            self._rotate_yolo_labels_file(txt_path, rotation_type)
            self.logger.info(f"✓ 已更新标签: {txt_path.name}")
        else:
            self.logger.warning(f"⚠ 未找到标签文件: {txt_path.name}")

        return True

    def _rotate_yolo_labels_file(self, txt_path: Path, rotation_type: str = '90') -> None:
        """
        旋转YOLO格式的标签文件并覆盖原文件
        YOLO格式: class_id x_center y_center width height
        坐标是归一化的 (0-1)
        
        Args:
            txt_path: 标签文件路径
            rotation_type: 旋转类型 ('90'顺时针90度, '270'逆时针90度, '180'180度)
        """
        new_lines = []

        try:
            with open(txt_path, 'r') as f:
                lines = f.readlines()

            for line in lines:
                parts = line.strip().split()
                if len(parts) != 5:
                    new_lines.append(line.strip())  # 保留不符合格式的行
                    continue

                try:
                    class_id = int(parts[0])
                    x_center = float(parts[1])
                    y_center = float(parts[2])
                    width = float(parts[3])
                    height = float(parts[4])

                    # 应用旋转变换
                    if rotation_type == RotationType.CLOCKWISE_90.value:  # 顺时针90度
                        # 坐标变换: (x, y) -> (1-y, x)
                        new_x_center = 1.0 - y_center
                        new_y_center = x_center
                        new_width = height
                        new_height = width
                    elif rotation_type == RotationType.COUNTERCLOCKWISE_90.value:  # 逆时针90度
                        # 坐标变换: (x, y) -> (y, 1-x)
                        new_x_center = y_center
                        new_y_center = 1.0 - x_center
                        new_width = height
                        new_height = width
                    elif rotation_type == RotationType.ROTATE_180.value:  # 180度
                        new_x_center = 1.0 - x_center
                        new_y_center = 1.0 - y_center
                        new_width = width
                        new_height = height
                    else:
                        new_x_center, new_y_center, new_width, new_height = x_center, y_center, width, height

                    # 确保坐标在[0,1]范围内
                    new_x_center = max(0.0, min(1.0, new_x_center))
                    new_y_center = max(0.0, min(1.0, new_y_center))
                    new_width = max(0.0, min(1.0, new_width))
                    new_height = max(0.0, min(1.0, new_height))

                    new_line = f"{class_id} {new_x_center:.6f} {new_y_center:.6f} {new_width:.6f} {new_height:.6f}"
                    new_lines.append(new_line)

                except ValueError as e:
                    self.logger.warning(f"警告: 解析标签行时出错 '{line.strip()}' -> {e}")
                    new_lines.append(line.strip())  # 保留原行

            # 写回文件（覆盖）
            with open(txt_path, 'w') as f:
                for line in new_lines:
                    f.write(line + '\n')
                
        except Exception as e:
            self.logger.error(f"处理标签文件时出错 {txt_path}: {e}")
    
    def rotate_yolo_dataset(self, image_folder: str, label_folder: str, seed: Optional[int] = 42, rotation_type: str = RotationType.CLOCKWISE_90.value, ratio: float = 0.5, backup: bool = True, max_workers: int = 4) -> None:
        """
        YOLO数据集旋转功能
        
        Args:
            image_folder: 图片文件夹地址
            label_folder: 标签文件夹地址
            seed: 随机种子，用于可重复的结果, 默认42
            rotation_type: 旋转类型，可使用RotationType枚举常量的value属性
                          - RotationType.CLOCKWISE_90.value: 顺时针90度
                          - RotationType.COUNTERCLOCKWISE_90.value: 逆时针90度
                          - RotationType.ROTATE_180.value: 180度旋转
                          默认: RotationType.CLOCKWISE_90.value
            ratio: 随机旋转比例 (0-1)，默认0.5
            backup: 是否备份原文件
            max_workers: 最大线程数，默认4
        """
        # 验证旋转类型
        valid_rotation_types = [rt.value for rt in RotationType]
        if rotation_type not in valid_rotation_types:
            self.logger.error(f"无效的旋转类型: {rotation_type}")
            self.logger.error(f"有效的旋转类型: {valid_rotation_types}")
            return
        # 设置随机种子
        if seed is not None:
            random.seed(seed)
            self.logger.info(f"使用随机种子: {seed}")

        # 验证文件夹存在
        try:
            image_folder = Path(image_folder)
            label_folder = Path(label_folder)
            
            if not image_folder.exists():
                self.logger.error(f"错误: 图片文件夹不存在: {image_folder}")
                return
            
            if not label_folder.exists():
                self.logger.error(f"错误: 标签文件夹不存在: {label_folder}")
                return
        except Exception as e:
            self.logger.error(f"验证文件夹失败: {e}")
            return

        # 创建备份目录
        backup_dir = None
        if backup:
            try:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                backup_dir = image_folder / f"backup_{timestamp}"
                self.logger.info(f"备份目录: {backup_dir}")
            except Exception as e:
                self.logger.error(f"创建备份目录失败: {e}")
                backup_dir = None

        image_files = []

        try:
            for file_path in image_folder.iterdir():
                if file_path.is_file() and file_path.suffix in IMAGE_TYPE_FORMAT:
                    image_files.append(file_path)
        except Exception as e:
            self.logger.error(f"读取文件夹失败: {e}")
            return

        if not image_files:
            self.logger.error(f"错误: 在图片文件夹中没有找到图片文件: {image_folder}")
            self.logger.error(f"支持的格式: {', '.join(IMAGE_TYPE_FORMAT)}")
            return

        self.logger.info(f"找到 {len(image_files)} 个图片文件")

        # 计算需要旋转的文件数量
        total_files = len(image_files)
        rotate_count = int(total_files * ratio)

        if rotate_count == 0:
            self.logger.info(f"根据比例 {ratio}，没有文件需要旋转")
            return

        # 随机选择要旋转的文件
        files_to_rotate = random.sample(image_files, rotate_count)

        self.logger.info(f"开始处理 {rotate_count} 个文件...")
        self.logger.info("-" * 50)

        # 旋转文件
        rotated_count = 0
        
        # 使用多线程处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for i, image_path in enumerate(files_to_rotate, 1):
                # 确定对应的标签文件
                txt_path = label_folder / f"{image_path.stem}.txt"
                
                self.logger.info(f"[{i}/{rotate_count}] 处理: {image_path.name} ({rotation_type}度)")
                
                # 提交任务到线程池
                futures.append(executor.submit(
                    self._rotate_image_and_labels,
                    image_path,
                    txt_path,
                    rotation_type,
                    backup_dir
                ))
            
            # 等待所有任务完成并收集结果
            for future in futures:
                if future.result():
                    rotated_count += 1

        # 打印统计信息
        self.logger.info("\n" + "=" * 60)
        self.logger.info("🎉 旋转处理完成!")
        self.logger.info("=" * 60)
        self.logger.info(f"📁 图片文件夹: {image_folder}")
        self.logger.info(f"📁 标签文件夹: {label_folder}")
        self.logger.info(f"📊 总文件数: {total_files}")
        self.logger.info(f"🎯 旋转比例: {ratio * 100:.1f}%")
        self.logger.info(f"🔄 旋转类型: {rotation_type}度")
        self.logger.info(f"✅ 目标旋转文件数: {rotate_count}")
        self.logger.info(f"✅ 成功旋转文件数: {rotated_count}")

        if backup and backup_dir:
            self.logger.info(f"💾 原文件已备份到: {backup_dir}")
        self.logger.info("=" * 60)

    def batch_process(self, process_configs: List[Dict[str, Any]]) -> None:
        """
        批量处理多个数据集
        
        Args:
            process_configs: 配置列表，每个配置包含处理一个数据集所需的参数
                            每个配置应包含以下键：
                            - image_folder: 图片文件夹地址
                            - label_folder: 标签文件夹地址
                            - seed: 随机种子（可选）
                            - rotation_type: 旋转类型（可选），推荐使用RotationType枚举常量的value属性
                            - ratio: 随机旋转比例（可选）
                            - backup: 是否备份原文件（可选）
                            - max_workers: 最大线程数（可选）
        
        Example:
            >>> # 创建YOLO数据预处理器实例
            >>> preprocessor = YOLODataPreprocessor()
            >>>
            >>> # 定义多个数据集配置（使用枚举常量）
            >>> configs = [
            ...     {
            ...         "image_folder": "./dataset1/images",
            ...         "label_folder": "./dataset1/labels",
            ...         "rotation_type": RotationType.CLOCKWISE_90.value,  # 顺时针90度
            ...         "ratio": 0.5,
            ...         "max_workers": 4
            ...     },
            ...     {
            ...         "image_folder": "./dataset2/images",
            ...         "label_folder": "./dataset2/labels",
            ...         "rotation_type": RotationType.ROTATE_180.value,  # 180度旋转
            ...         "ratio": 0.3,
            ...         "backup": True
            ...     },
            ...     {
            ...         "image_folder": "./dataset3/images",
            ...         "label_folder": "./dataset3/labels",
            ...         "rotation_type": RotationType.COUNTERCLOCKWISE_90.value,  # 逆时针90度
            ...         "ratio": 0.8,
            ...         "seed": 123
            ...     }
            ... ]
            >>> 
            >>> # 执行批量处理
            >>> preprocessor.batch_process(configs)
            >>> # 输出: 依次处理每个数据集并显示处理结果
        """
        self.logger.info("=" * 60)
        self.logger.info("开始批量处理")
        self.logger.info("=" * 60)
        
        total_configs = len(process_configs)
        for i, config in enumerate(process_configs, 1):
            self.logger.info(f"\n[{i}/{total_configs}] 处理数据集:")
            self.logger.info(f"图片文件夹: {config.get('image_folder')}")
            self.logger.info(f"标签文件夹: {config.get('label_folder')}")
            self.logger.info(f"旋转类型: {config.get('rotation_type', '90')}度")
            self.logger.info(f"旋转比例: {config.get('ratio', 0.5)}")
            
            try:
                # 调用旋转方法处理数据集
                self.rotate_yolo_dataset(**config)
                self.logger.info(f"✅ 数据集处理完成")
            except Exception as e:
                self.logger.error(f"❌ 数据集处理失败: {e}")
        
        self.logger.info("\n" + "=" * 60)
        self.logger.info("批量处理完成")
        self.logger.info("=" * 60)


# 主程序入口
if __name__ == "__main__":
    # 示例用法
    logger = set_logging(name="YOLODataPreprocessorExample", verbose=True)
    logger.info("=" * 60)
    logger.info("YOLO数据集旋转工具示例")
    logger.info("=" * 60)
    
    # 创建YOLO数据预处理器实例
    preprocessor = YOLODataPreprocessor()
    
    # 示例参数
    image_folder = "./images"  # 图片文件夹路径
    label_folder = "./labels"  # 标签文件夹路径
    seed = 42  # 随机种子
    rotation_type = RotationType.CLOCKWISE_90.value  # 旋转类型: 使用枚举常量
    ratio = 0.5  # 旋转比例
    backup = False  # 是否备份
    
    logger.info(f"📁 图片文件夹: {image_folder}")
    logger.info(f"📁 标签文件夹: {label_folder}")
    logger.info(f"🎯 旋转比例: {ratio * 100:.1f}%")
    logger.info(f"🔄 旋转类型: {rotation_type}度")
    logger.info(f"💾 备份文件: {'是' if backup else '否'}")
    if seed:
        logger.info(f"🎲 随机种子: {seed}")
    logger.info("=" * 60)
    
    # 开始处理
    start_time = time.time()
    
    preprocessor.rotate_yolo_dataset(
        image_folder=image_folder,
        label_folder=label_folder,
        seed=seed,
        rotation_type=rotation_type,
        ratio=ratio,
        backup=backup
    )
    
    end_time = time.time()
    logger.info(f"\n⏱️ 总耗时: {end_time - start_time:.2f} 秒")