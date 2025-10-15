import os
import cv2
from tqdm import tqdm

from ..utils import set_logging

__all__ = ['resize_box_to_target', 'sliding_crop_image', 'TaggedImageCrop', 'batch_multithreaded_image_cropping']


def resize_box_to_target(box, target_size, original_size):
    """
    将边界框坐标从原始图像尺寸等比缩放到目标尺寸

    Args:
        box (List[int] | Tuple[int]): 原始图像上的边界框坐标，格式为 [x_min, y_min, x_max, y_max]
        target_size (Tuple[int]): 目标图像的尺寸，格式为 (width, height)
        original_size (Tuple[int]): 原始图像的尺寸，格式为 (width, height)

    Returns:
        List[int]: 缩放后的边界框坐标，格式为 [x_min, y_min, x_max, y_max]，
                   坐标值已四舍五入取整，确保为整数像素坐标

    Example:
        >>> original_box = [100, 50, 200, 150]  # 原始边界框
        >>> target_size = (800, 600)             # 目标图像尺寸
        >>> original_size = (1600, 1200)        # 原始图像尺寸
        >>> new_box = resize_box_to_target(original_box, target_size, original_size)
        >>> print(new_box)  # [50, 25, 100, 75] (等比例缩小一半)
    """
    tar_w, tar_h = target_size
    orig_w, orig_h = original_size

    scale_x = tar_w / orig_w
    scale_y = tar_h / orig_h

    return [
        int(round(box[0] * scale_x)),
        int(round(box[1] * scale_y)),
        int(round(box[2] * scale_x)),
        int(round(box[3] * scale_y))
    ]


def sliding_crop_image(img, crop_size=None, stride=None):
    """
    滑动裁剪图片,返回裁剪的图像块及其位置信息

    Args:
        img: 输入图像，numpy数组格式，形状为 [高度, 宽度, 通道数] 或 [高度, 宽度]
        crop_size: 裁剪窗口大小
        stride: 滑动步长

    Returns:
        list: 包含裁剪图像块及其坐标信息的列表，每个元素为 [crop_img, x, y]
            - crop_img: 裁剪出的图像块，numpy数组
            - x: 该图像块在原图中的左上角x坐标
            - y: 该图像块在原图中的左上角y坐标

     Example:
        >>> import numpy as np
        >>>
        >>> # 示例1: 基本滑动裁剪
        >>> image = np.random.rand(256, 256, 3)  # 创建测试图像
        >>> crops = sliding_crop_image(image, crop_size=64, stride=32)
        >>> print(f"共裁剪出 {len(crops)} 个图像块")
        >>>
        >>> # 访问第一个裁剪块和其坐标
        >>> first_crop, x, y = crops[0]
        >>> print(f"第一个裁剪块位置: x={x}, y={y}, 形状: {first_crop.shape}")
    """
    h, w = img.shape[:2]
    crops = []
    for y in range(0, h - crop_size + 1, stride):
        for x in range(0, w - crop_size + 1, stride):
            crop = img[y:y + crop_size, x:x + crop_size]
            crops.append([crop, x, y])
    return crops


class TaggedImageCrop:
    """
    基于VOC标签格式的图像裁剪处理器

    用于将带有VOC格式标注的图像裁剪成多个小块，同时自动调整标注信息。
    适用于目标检测数据增强、大图像分割处理等场景。

    Attributes:
        retrain_no_detect (bool): 是否保留没有目标的裁剪块
        save_dir (str): 保存目录
        target_size (Tuple[int, int]): 裁剪前图像缩放目标尺寸 (width, height)
        crop_size (int): 裁剪窗口大小（正方形）
        stride (int): 滑动步长
    Example:
        >>> # 初始化裁剪处理器
        >>> processor = TaggedImageCrop(
        >>>     retrain_no_detect=True,          # 保留无目标图像块
        >>>     save_dir="./output_crops",       # 输出目录
        >>>     target_size=(2000, 1500),        # 先缩放到2000x1500
        >>>     crop_size=640,                   # 裁剪为640x640块
        >>>     stride=320                       # 50%重叠率
        >>> )
        >>>
        >>> # 处理单张图像和对应的标注文件
        >>> processor.crop_image_and_labels(
        >>>     "images/defect_001.jpg",
        >>>     "annotations/defect_001.xml"
        >>> )
    """

    def __init__(self, retrain_no_detect=False, save_dir=None, target_size=None, crop_size=640, stride=320,
                 verbose=False):
        """
        初始化图像裁剪处理器(基于带VOC标签格式的图片裁剪)

        Args:
            retrain_no_detect: 是否保留裁剪的没有缺陷的图片块
            save_dir: 保存目录
            target_size: 裁剪前图像缩放大小，None表示不进行缩放处理,(w,h)
            crop_size: 裁剪窗口大小
            stride: 滑动步长
        """
        self.retrain_no_detect = retrain_no_detect
        self.target_size = target_size
        self.crop_size = crop_size
        self.stride = stride
        self.logger = set_logging("TaggedImageCrop", verbose=verbose)

        # 创建保存目录
        self.save_img_dir = os.path.join(save_dir, "images")
        self.save_ok_img_dir = os.path.join(save_dir, "ok_images")
        self.save_xml_dir = os.path.join(save_dir, "xmls")

        self._create_directories()

    def _create_directories(self):
        """创建必要的目录结构"""
        os.makedirs(self.save_img_dir, exist_ok=True)
        os.makedirs(self.save_xml_dir, exist_ok=True)
        if self.retrain_no_detect:
            os.makedirs(self.save_ok_img_dir, exist_ok=True)

    def _parse_xml(self, xml_file, original_size):
        """解析XML标签文件,获取标注信息"""
        import xml.etree.ElementTree as ET
        try:
            tree = ET.parse(xml_file)
            annotations = []

            # 提取每个缺陷的标签信息
            for obj in tree.findall('object'):
                name = obj.find('name').text
                bndbox = obj.find('bndbox')
                box = (int(bndbox.find('xmin').text),
                       int(bndbox.find('ymin').text),
                       int(bndbox.find('xmax').text),
                       int(bndbox.find('ymax').text))

                # 判断是否需要进行缩放坐标映射
                if self.target_size:
                    box = resize_box_to_target(box, self.target_size, original_size)
                if name.endswith('U4U'):
                    box = [1, 1, original_size[0] - 1, original_size[1] - 1]
                annotations.append((name, box))
            return annotations
        except ET.ParseError as e:
            self.logger.error(f"XML解析错误: {xml_file}, 错误: {e}")
            return []
        except Exception as e:
            self.logger.error(f"解析XML时发生未知错误: {xml_file}, 错误: {e}")
            return []

    def is_defect_relevant(self, defect_name, intersect, defect_area):
        """根据缺陷类型判断是否符合条件"""
        inter_width, inter_height, intersect_area = intersect
        if defect_name in ['MP1U', 'ML3U']:
            # MP1U 类型：交集面积占缺陷总面积的比例 > 50%
            return intersect_area / defect_area > 0.5
        elif defect_name == 'MU2U':
            # MU2U 类型：交集面积 > 40960 且宽高大于10
            return intersect_area > 40960 and min(inter_width, inter_height) > 10
        else:
            # 其他缺陷：交集面积占总面积 > 5% 且宽高大于3
            return intersect_area / defect_area > 0.05 and min(inter_width, inter_height) > 3

    def _update_labels_for_crop(self, annotations, x_offset, y_offset, crop_size):
        """更新裁剪块中的标签"""
        new_annotations = []
        for name, box in annotations:
            xmin, ymin, xmax, ymax = box
            # 如果标签在裁剪区域内
            if xmin < x_offset + crop_size and ymin < y_offset + crop_size and xmax > x_offset and ymax > y_offset:
                # 计算标签在裁剪块内的位置
                new_xmin = max(0, xmin - x_offset)
                new_ymin = max(0, ymin - y_offset)
                new_xmax = min(crop_size, xmax - x_offset)
                new_ymax = min(crop_size, ymax - y_offset)

                # 计算重叠面积
                intersect_area = (new_xmax - new_xmin) * (new_ymax - new_ymin)
                defect_area = (xmax - xmin) * (ymax - ymin)

                if intersect_area > 0:
                    # 计算交集的宽度和高度
                    inter_width = new_xmax - new_xmin
                    inter_height = new_ymax - new_ymin

                    # 判断是否满足缺陷条件
                    if self.is_defect_relevant(name, (inter_width, inter_height, intersect_area), defect_area):
                        new_annotations.append((name, new_xmin, new_ymin, new_xmax, new_ymax))
        return new_annotations

    def _save(self, crop_image, cropped_labels, image_filename, xml_filename, crop_index):
        """保存裁剪后的图像和标签"""
        # 保存裁剪后的图像
        if not cropped_labels and self.retrain_no_detect:
            save_dir = self.save_ok_img_dir
            suffix = '_ok'
        else:
            save_dir = self.save_img_dir
            suffix = ''
        crop_image_filename = os.path.join(save_dir, f"{image_filename}{suffix}_{crop_index}.jpg")

        cv2.imwrite(crop_image_filename, crop_image)

        # 保存XML文件
        if cropped_labels:
            xml_save_path = os.path.join(self.save_xml_dir, f"{xml_filename}_{crop_index}.xml")

            from .annotation_convert import VOCAnnotation
            voc_ann = VOCAnnotation(xml_filename, image_size=(self.crop_size, self.crop_size))
            for label in cropped_labels:
                voc_ann.add_object(
                    name=label[0],
                    bbox=[float(label[1]), float(label[2]), float(label[3]), float(label[4])]
                )
            voc_ann.save(xml_save_path)

    def crop_image_and_labels(self, image_path, xml_path):
        """
        图像裁剪和标签修改

        读取图像和对应的VOC标注文件，进行滑动窗口裁剪，并调整标注信息。

        Args:
            image_path: 输入图像文件路径
            xml_path: 对应的VOC格式XML标注文件路径

        Returns:
            Dict[str, int]: 裁剪统计信息，包含:
                - 'total_crops': 总裁剪块数
                - 'ng_crops': 包含目标的裁剪块数
                - 'ok_crops': 无目标的裁剪块数

        Example:
            >>> # 处理单张图像
            >>> stats = processor.crop_image_and_labels("image1.jpg", "annotation1.xml")
            >>> print(f"总裁剪块: {stats['total_crops']}, 有目标块: {stats['ng_crops']}, 无目标块: {stats['ok_crops']}")
            >>>
            >>> # 处理后的文件结构:
            >>> # output_crops/
            >>> #   ├── images/         # 包含目标的裁剪图像
            >>> #   ├── ok_images/      # 无目标的裁剪图像（如果retrain_no_detect=True）
            >>> #   └── xmls/           # 对应的VOC标注文件
        """
        # 读取图像
        if not os.path.exists(image_path):
            self.logger.error(f"图像文件不存在: {image_path}")

        image = cv2.imread(image_path)
        if image is None:
            self.logger.error(f"无法读取图像: {image_path}")

        original_size = image.shape[1], image.shape[0]

        # 缩放图像
        if self.target_size:
            image = cv2.resize(image, self.target_size, interpolation=cv2.INTER_LINEAR)

        # 解析XML标签
        annotations = self._parse_xml(xml_path, original_size)

        # 获取文件名
        image_filename = os.path.splitext(os.path.basename(image_path))[0]
        xml_filename = os.path.splitext(os.path.basename(xml_path))[0]

        ng_crop_index, ok_crop_index, crop_index = 0, 0, 0

        # 对图像进行裁剪
        crops = sliding_crop_image(image, self.crop_size, self.stride)
        for crop_img, x_offset, y_offset in crops:
            # 更新标签
            cropped_labels = self._update_labels_for_crop(annotations, x_offset, y_offset, self.crop_size)

            if cropped_labels:
                ng_crop_index += 1
                crop_index = ng_crop_index
            elif not cropped_labels and self.retrain_no_detect:
                ok_crop_index += 1
                crop_index = ok_crop_index
            else:
                continue

            # 保存裁剪后的图像和标签
            self._save(crop_img, cropped_labels, image_filename, xml_filename, crop_index)


def _single_image_cropping(args, verbose=False):
    """包装单张图片处理逻辑供线程池调用"""
    logger = set_logging("single_image_cropping", verbose=verbose)
    img_path, processor = args
    xml_path = img_path.replace('.jpg', '.xml')
    try:
        processor.crop_image_and_labels(img_path, xml_path)
        return True
    except Exception as e:
        logger.error(f"Error processing {img_path}: {str(e)}")
        return False


def batch_multithreaded_image_cropping(img_path_list, processor, max_workers=10, verbose=False):
    """
    批量多线程处理图像裁剪任务

    Args:
    img_path_list: 待处理的图片路径列表，每个元素为图片的完整文件路径
    processor: 包含crop_image_and_labels方法的处理器实例
    max_workers: 最大线程数（建议设为CPU核心数*2）

    Example:
        >>> processor = TaggedImageCrop(...)
        >>> image_paths = ["img1.jpg", "img2.jpg", "img3.jpg"]
        >>> batch_multithreaded_image_cropping(image_paths, processor, max_workers=8)
        Processing images: 100%|██████████| 3/3 [00:05<00:00, 1.67s/it]
        Completed: 3/3 (100.0%)
    """
    logger = set_logging("batch_multithreaded_image_cropping", verbose=verbose)
    # 准备线程池参数
    task_args = [(img_path, processor) for img_path in img_path_list]

    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 使用tqdm显示进度条
        results = list(tqdm(
            executor.map(_single_image_cropping, task_args),
            total=len(img_path_list),
            desc="Processing image cropping"
        ))

    # 统计处理结果
    success_count = sum(results)
    logger.info(
        f"\nCompleted: {success_count}/{len(img_path_list)} ({(success_count / len(img_path_list)) * 100:.1f}%)")

