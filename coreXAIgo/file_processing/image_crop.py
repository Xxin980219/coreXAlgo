import os
import cv2
from tqdm import tqdm

from ..utils.basic import set_logging


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

    Args:
        retrain_no_detect (bool): 是否保留没有目标的裁剪块
        separate_ok_ng (bool): 是否将OK（无缺陷）和NG（有缺陷）图像分开保存
        save_dir (str): 保存目录路径
        target_size (Tuple[int, int]): 裁剪前图像缩放目标尺寸 (width, height)
        crop_size (int): 裁剪窗口大小（正方形）
        stride (int): 滑动步长
        verbose (bool): 是否显示详细日志

    Example:
        >>> # 基本用法：仅裁剪有缺陷的区域
        >>> processor = TaggedImageCrop(
        >>>     retrain_no_detect=False,          # 不保留无缺陷图像块
        >>>     save_dir="./output",              # 输出目录
        >>>     crop_size=640,                    # 裁剪为640x640块
        >>>     stride=320                        # 50%重叠率
        >>> )
        >>> stats = processor.crop_image_and_labels("image.jpg", "annotation.xml")
        >>>
        >>> # 高级用法：包含正负样本，分开保存
        >>> processor = TaggedImageCrop(
        >>>     retrain_no_detect=True,           # 保留无缺陷图像块
        >>>     separate_ok_ng=True,              # OK和NG图像分开保存
        >>>     save_only_ok=False,               # False 正常模式 , True 只保存OK图片
        >>>     save_dir="./dataset",             # 输出目录
        >>>     target_size=(2000, 1500),        # 先缩放到2000x1500
        >>>     crop_size=640,                    # 裁剪尺寸
        >>>     stride=320,                       # 滑动步长
        >>>     verbose=True                      # 显示详细日志
        >>> )
        >>> stats = processor.crop_image_and_labels("defect_image.jpg", "defect_annotation.xml")
        >>> print(f"总裁剪块: {stats['total_crops']}, NG块: {stats['ng_crops']}, OK块: {stats['ok_crops']}")
    """

    def __init__(self, retrain_no_detect=False, separate_ok_ng=False,save_only_ok=False, save_dir=None, target_size=None, crop_size=640,
                 stride=320, verbose=False):
        """
        初始化图像裁剪处理器

        Args:
            retrain_no_detect (bool): 是否保留裁剪的没有缺陷的图片块
                - True: 保留所有裁剪块（包括无缺陷的）
                - False: 只保留包含缺陷的裁剪块
            separate_ok_ng (bool): 是否将OK和NG图像区分保存
                - True: OK图像保存到ok_images目录，NG图像保存到images目录
                - False: 所有图像都保存到images目录
            save_only_ok (bool): 是否只保存OK图片（无目标的裁剪块）
                - True: 只保存无目标的裁剪块
                - False: 根据retrain_no_detect和separate_ok_ng参数决定
            save_dir (str): 保存目录路径，如果为None则不保存
            target_size (Tuple[int, int]): 裁剪前图像缩放大小，格式为(width, height)
                - None: 不进行缩放处理
                - (w, h): 缩放到指定尺寸
            crop_size (int): 裁剪窗口大小（正方形）
            stride (int): 滑动步长，控制裁剪块的重叠率
                - stride = crop_size: 无重叠
                - stride < crop_size: 有重叠（如stride=320，crop_size=640，重叠50%）
            verbose (bool): 是否显示详细日志信息
        """
        self.retrain_no_detect = retrain_no_detect
        self.separate_ok_ng = separate_ok_ng
        self.save_only_ok = save_only_ok
        self.target_size = target_size
        self.crop_size = crop_size
        self.stride = stride
        self.verbose = verbose
        self.logger = set_logging("TaggedImageCrop", verbose=self.verbose)

        # 创建保存目录
        if save_dir:
            self.save_dir = save_dir

            if self.save_only_ok:
                # 如果只保存OK图片，创建ok_images目录
                self.save_ok_img_dir = os.path.join(save_dir, "ok_images")
                self.save_img_dir = None
                self.save_xml_dir = None
                os.makedirs(self.save_ok_img_dir, exist_ok=True)
                if self.verbose:
                    self.logger.info(f"只保存OK图片到: {self.save_ok_img_dir}")
            else:
                # 正常模式
                self.save_img_dir = os.path.join(save_dir, "images")
                self.save_xml_dir = os.path.join(save_dir, "xmls")
                os.makedirs(self.save_img_dir, exist_ok=True)
                os.makedirs(self.save_xml_dir, exist_ok=True)

                if self.retrain_no_detect and self.separate_ok_ng:
                    self.save_ok_img_dir = os.path.join(save_dir, "ok_images")
                    os.makedirs(self.save_ok_img_dir, exist_ok=True)
                else:
                    self.save_ok_img_dir = None
        else:
            self.save_dir = None
            self.save_img_dir = None
            self.save_ok_img_dir = None
            self.save_xml_dir = None

    def _parse_xml(self, xml_file, original_size):
        """解析XML标签文件,获取标注信息"""
        import xml.etree.ElementTree as ET
        try:
            tree = ET.parse(xml_file)
            annotations = []
            orig_w, orig_h = original_size

            for obj in tree.findall('object'):
                name = obj.find('name').text
                bndbox = obj.find('bndbox')
                box = (
                    int(float(bndbox.find('xmin').text)),
                    int(float(bndbox.find('ymin').text)),
                    int(float(bndbox.find('xmax').text)),
                    int(float(bndbox.find('ymax').text))
                )

                # 边界检查
                box = (
                    max(0, box[0]),
                    max(0, box[1]),
                    min(orig_w, box[2]),
                    min(orig_h, box[3])
                )

                if box[2] <= box[0] or box[3] <= box[1]:
                    continue

                # 缩放坐标
                if self.target_size:
                    target_w, target_h = self.target_size
                    box = resize_box_to_target(box, (target_w, target_h), (orig_w, orig_h))

                # 注意：这里移除了U4U的特殊扩展代码
                # 让U4U保持原始大小，在_is_defect_in_crop中特殊处理
                annotations.append((name, box))

            if self.verbose:
                self.logger.info(f"解析XML: {xml_file}, 找到 {len(annotations)} 个标注")
                for name, box in annotations:
                    if name.endswith('U4U'):
                        self.logger.info(f"  U4U标注: 大小={(box[2] - box[0])}x{(box[3] - box[1])}")

            return annotations
        except Exception as e:
            self.logger.error(f"解析XML错误 {xml_file}: {e}")
            return []

    def _is_defect_in_crop(self, defect_box, crop_box, defect_name):
        """
        判断缺陷是否在裁剪区域内

        Args:
            defect_box: 缺陷边界框 [xmin, ymin, xmax, ymax]
            crop_box: 裁剪区域边界框 [xmin, ymin, xmax, ymax]
            defect_name: 缺陷名称

        Returns:
            bool: 是否在裁剪区域内
            tuple: 裁剪块内的坐标 (xmin, ymin, xmax, ymax)

        修复了原逻辑的问题：
        1. 对于大缺陷，从裁剪块角度计算比例
        2. 添加绝对面积阈值
        3. 特殊处理U4U等覆盖性缺陷
        """
        # 计算交集
        inter_xmin = max(defect_box[0], crop_box[0])
        inter_ymin = max(defect_box[1], crop_box[1])
        inter_xmax = min(defect_box[2], crop_box[2])
        inter_ymax = min(defect_box[3], crop_box[3])

        if inter_xmax <= inter_xmin or inter_ymax <= inter_ymin:
            return False, None

        inter_width = inter_xmax - inter_xmin
        inter_height = inter_ymax - inter_ymin
        intersect_area = inter_width * inter_height

        # 计算裁剪块面积
        crop_width = crop_box[2] - crop_box[0]
        crop_height = crop_box[3] - crop_box[1]
        crop_area = crop_width * crop_height

        # 计算缺陷面积
        defect_width = defect_box[2] - defect_box[0]
        defect_height = defect_box[3] - defect_box[1]
        defect_area = defect_width * defect_height

        # 调试信息
        if self.verbose and defect_name.endswith('U4U'):
            self.logger.debug(f"U4U缺陷检查: 交集面积={intersect_area}, 缺陷面积={defect_area}, "
                              f"裁剪块面积={crop_area}, 交集尺寸={inter_width}x{inter_height}")

        # 特殊处理U4U
        if defect_name.endswith('U4U'):
            # U4U通常很大，只要交集面积足够大就保留
            if intersect_area > 0.1 * crop_area:  # 交集占裁剪块10%以上
                return True, (inter_xmin - crop_box[0], inter_ymin - crop_box[1],
                              inter_xmax - crop_box[0], inter_ymax - crop_box[1])

        # 根据缺陷类型设置不同策略
        if defect_name in ['MP1U', 'ML3U']:
            # 策略1：相对面积
            defect_ratio = intersect_area / defect_area if defect_area > 0 else 0
            # 策略2：绝对面积
            condition1 = defect_ratio > 0.3  # 降低阈值到30%
            condition2 = intersect_area > 20000  # 绝对面积

            if condition1 or condition2:
                return True, (inter_xmin - crop_box[0], inter_ymin - crop_box[1],
                              inter_xmax - crop_box[0], inter_ymax - crop_box[1])

        elif defect_name == 'MU2U':
            # MU2U策略
            if intersect_area > 40960 and min(inter_width, inter_height) > 10:
                return True, (inter_xmin - crop_box[0], inter_ymin - crop_box[1],
                              inter_xmax - crop_box[0], inter_ymax - crop_box[1])

        else:
            # 通用策略：多重条件判断
            # 条件1：相对面积（缺陷角度）
            defect_ratio = intersect_area / defect_area if defect_area > 0 else 0
            # 条件2：相对面积（裁剪块角度）
            crop_ratio = intersect_area / crop_area if crop_area > 0 else 0
            # 条件3：绝对面积
            absolute_area = intersect_area
            # 条件4：最小尺寸
            min_dimension = min(inter_width, inter_height)

            # 组合判断
            condition1 = defect_ratio > 0.05 and min_dimension > 3
            condition2 = crop_ratio > 0.15  # 交集占裁剪块15%以上
            condition3 = absolute_area > 3000 and min_dimension > 5

            if condition1 or condition2 or condition3:
                if self.verbose:
                    self.logger.debug(f"缺陷 {defect_name} 在裁剪块内: "
                                      f"defect_ratio={defect_ratio:.2%}, "
                                      f"crop_ratio={crop_ratio:.2%}, "
                                      f"area={absolute_area}, "
                                      f"min_dim={min_dimension}")
                return True, (inter_xmin - crop_box[0], inter_ymin - crop_box[1],
                              inter_xmax - crop_box[0], inter_ymax - crop_box[1])

        return False, None
    def _update_labels_for_crop(self, annotations, x_offset, y_offset, crop_size):
        """更新裁剪块中的标签"""
        new_annotations = []
        crop_box = [x_offset, y_offset, x_offset + crop_size, y_offset + crop_size]

        for name, box in annotations:
            # 判断缺陷是否在裁剪区域内
            is_in_crop, crop_coords = self._is_defect_in_crop(box, crop_box, name)

            if is_in_crop and crop_coords:
                # 确保坐标在裁剪块内
                xmin, ymin, xmax, ymax = crop_coords
                xmin = max(0, min(xmin, crop_size - 1))
                ymin = max(0, min(ymin, crop_size - 1))
                xmax = max(1, min(xmax, crop_size))
                ymax = max(1, min(ymax, crop_size))

                # 确保坐标有效
                if xmax > xmin and ymax > ymin:
                    new_annotations.append((name, xmin, ymin, xmax, ymax))
                else:
                    self.logger.warning(f"无效的裁剪坐标: {crop_coords}")

        return new_annotations

    def _save(self, crop_image, cropped_labels, base_filename, crop_index):
        """保存裁剪后的图像和标签"""
        if not self.save_dir:
            return

        # 明确判断是否有标签
        has_labels = len(cropped_labels) > 0 if cropped_labels else False

        # 如果设置了只保存OK图片，但有标签，则跳过
        if self.save_only_ok and has_labels:
            if self.verbose:
                self.logger.debug(f"跳过保存（有标签）: {base_filename}_{crop_index}")
            return

        # 如果设置了只保存OK图片，且无标签，则保存到ok_images目录
        if self.save_only_ok and not has_labels:
            img_save_path = self.save_ok_img_dir
            save_type = "OK(only)"
        else:
            # 正常模式
            if not has_labels and self.retrain_no_detect and self.separate_ok_ng and self.save_ok_img_dir:
                # 无标签 + 保留无标签图片 + 分开保存 -> 保存到ok_images
                img_save_path = self.save_ok_img_dir
                save_type = "OK"
            else:
                # 其他情况保存到images目录
                img_save_path = self.save_img_dir
                save_type = "NG" if has_labels else "OK(images)"

            # 生成文件名
        img_filename = f"{base_filename}_{crop_index}.jpg"
        img_full_path = os.path.join(img_save_path, img_filename)

        # 确保目录存在
        os.makedirs(os.path.dirname(img_full_path), exist_ok=True)

        # 保存图片
        try:
            cv2.imwrite(img_full_path, crop_image)
            if self.verbose:
                self.logger.debug(f"保存图片: {img_filename} ({save_type}) -> {os.path.basename(img_save_path)}")
        except Exception as e:
            self.logger.error(f"保存图片失败 {img_filename}: {e}")
            return

        # 如果只保存OK图片，不保存XML
        if not self.save_only_ok and has_labels and cropped_labels:
            # 保存XML文件
            xml_filename = f"{base_filename}_{crop_index}.xml"
            xml_full_path = os.path.join(self.save_xml_dir, xml_filename)

            try:
                from .annotation_convert import VOCAnnotation
                voc_ann = VOCAnnotation(
                    img_full_path,
                    image_size=(crop_image.shape[1], crop_image.shape[0]),
                    verbose=self.verbose
                )
                for label in cropped_labels:
                    voc_ann.add_object(
                        name=label[0],
                        bbox=[float(label[1]), float(label[2]), float(label[3]), float(label[4])]
                    )
                voc_ann.save(xml_full_path)
                if self.verbose:
                    self.logger.debug(f"保存XML: {xml_filename} 包含 {len(cropped_labels)} 个目标")
            except Exception as e:
                self.logger.error(f"保存XML失败 {xml_filename}: {e}")
    def _process_image(self, image_path):
        """读取并预处理图像"""
        # 读取图像
        if not os.path.exists(image_path):
            self.logger.error(f"图像文件不存在: {image_path}")

        image = cv2.imread(image_path)
        if image is None:
            self.logger.error(f"无法读取图像: {image_path}")
        original_size = image.shape[:2][::-1]

        if self.target_size:
            image = cv2.resize(image, self.target_size, interpolation=cv2.INTER_LINEAR)
        return image, original_size

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
        image, original_size = self._process_image(image_path)

        # 解析XML标签
        annotations = []
        if xml_path is not None and os.path.exists(xml_path):
            annotations = self._parse_xml(xml_path, original_size)
            if self.verbose:
                self.logger.info(f"解析到 {len(annotations)} 个标注")
                for name, box in annotations:
                    if name.endswith('U4U'):
                        self.logger.info(f"U4U缺陷: 原始大小={(box[2] - box[0])}x{(box[3] - box[1])}")
        elif xml_path is not None:
            self.logger.warning(f"XML文件不存在: {xml_path}")

        # 获取文件名
        base_name = os.path.splitext(os.path.basename(image_path))[0]

        # 统计信息
        stats = {
            'total_crops': 0,
            'ng_crops': 0,  # 有缺陷的裁剪块
            'ok_crops': 0  # 无缺陷的裁剪块
        }

        # 对图像进行裁剪
        crops = sliding_crop_image(image, self.crop_size, self.stride)
        stats['total_crops'] = len(crops)

        for idx, (crop_img, x, y) in enumerate(crops):
            # 更新标签
            cropped_labels = []
            if annotations:  # 只在有原始标注时才处理
                cropped_labels = self._update_labels_for_crop(annotations, x, y, self.crop_size)

            has_labels = len(cropped_labels) > 0

            # 判断是否需要保存
            should_save = True

            if self.save_only_ok:
                # 只保存OK图片模式：只有无标签时才保存
                if has_labels:
                    should_save = False
            else:
                # 正常模式
                if not self.retrain_no_detect and not has_labels:
                    # 如果不保留无缺陷图片且当前裁剪块无缺陷，则跳过
                    should_save = False

            if should_save:
                # 保存裁剪块
                self._save(crop_img, cropped_labels, base_name, idx)

                # 更新统计
                if has_labels:
                    stats['ng_crops'] += 1
                else:
                    stats['ok_crops'] += 1

        if self.verbose:
            self.logger.info(f"处理完成: {base_name} - 总裁剪块: {stats['total_crops']}, "
                             f"NG块: {stats['ng_crops']}, OK块: {stats['ok_crops']}")

        return stats


def _single_image_cropping(args, verbose=False):
    """
    包装单张图片处理逻辑供线程池调用
    Args:
        args: 包含 (img_path, processor_instance) 的元组
    """
    logger = set_logging("single_image_cropping", verbose=verbose)
    img_path, processor = args

    # 查找对应的XML文件
    xml_path = os.path.splitext(img_path)[0] + '.xml'
    if not os.path.exists(xml_path):
        xml_path = None
        if verbose:
            logger.warning(f"没有找到XML文件: {xml_path}")

    try:
        # 直接调用处理器的 crop_image_and_labels 方法
        result = processor.crop_image_and_labels(img_path, xml_path)
        return True, result
    except Exception as e:
        logger.error(f"处理失败 {img_path}: {str(e)}")
        return False, None


def batch_multithreaded_image_cropping(img_path_list, processor, max_workers=10, verbose=False):
    """
    批量多线程处理图像裁剪任务

    Args:
        img_path_list: 待处理的图片路径列表，每个元素为图片的完整文件路径
        processor: TaggedImageCrop 实例
        max_workers: 最大线程数（建议设为CPU核心数*2）

    Example:
        >>> processor = TaggedImageCrop(...)
        >>> image_paths = ["img1.jpg", "img2.jpg", "img3.jpg"]
        >>> batch_multithreaded_image_cropping(image_paths, processor, max_workers=8)
        Processing image cropping: 100%|██████████| 3/3 [00:05<00:00, 1.67s/it]
        Completed: 3/3 (100.0%)
    """
    logger = set_logging("batch_multithreaded_image_cropping", verbose=verbose)

    if not img_path_list:
        logger.warning("没有图片需要处理")
        return

    # 验证processor
    if not hasattr(processor, 'crop_image_and_labels'):
        logger.error("processor必须是TaggedImageCrop类的实例")
        return

    # 准备参数
    task_args = [(img_path, processor) for img_path in img_path_list]

    import concurrent.futures

    # 总统计
    total_stats = {
        'total_images': len(img_path_list),
        'success_count': 0,
        'total_crops': 0,
        'total_ng': 0,
        'total_ok': 0
    }

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 使用列表推导式创建futures
        futures = [executor.submit(_single_image_cropping, args, verbose) for args in task_args]

        # 使用tqdm显示进度
        for future in tqdm(concurrent.futures.as_completed(futures),
                           total=len(futures),
                           desc="批量裁剪进度"):
            try:
                success, stats = future.result()
                if success and stats:
                    total_stats['success_count'] += 1
                    total_stats['total_crops'] += stats.get('total_crops', 0)
                    total_stats['total_ng'] += stats.get('ng_crops', 0)
                    total_stats['total_ok'] += stats.get('ok_crops', 0)
            except Exception as e:
                logger.error(f"处理结果时出错: {e}")

    # 输出总统计
    logger.info(f"\n处理完成!")
    logger.info(f"成功处理: {total_stats['success_count']}/{total_stats['total_images']} 张图片")
    logger.info(f"总裁剪块: {total_stats['total_crops']}")
    logger.info(f"有目标块: {total_stats['total_ng']}")
    logger.info(f"无目标块: {total_stats['total_ok']}")

    return total_stats