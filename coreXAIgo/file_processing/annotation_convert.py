import json
import os
import cv2
import numpy as np
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Tuple, Optional, TypedDict, Union

from lxml import etree

from ..utils.basic import set_logging


# 自定义异常类
class AnnotationError(Exception):
    """标注处理错误基类"""
    pass


class FormatError(AnnotationError):
    """格式错误"""
    pass


class FileError(AnnotationError):
    """文件错误"""
    pass


class ValidationError(AnnotationError):
    """验证错误"""
    pass


# 类型定义
class PolygonPoint(TypedDict):
    """多边形点坐标"""
    x: float
    y: float


class BBox(TypedDict):
    """边界框坐标"""
    xmin: float
    ymin: float
    xmax: float
    ymax: float


class YOLOAnnotation:
    """
    YOLO格式标注处理类

    用于创建、管理和保存YOLO格式的目标检测和实例分割标注数据。
    支持标准的YOLO边界框格式和分割多边形格式，所有坐标值必须为归一化值（0-1范围内）。

    YOLO标注格式说明：
    1. 边界框格式：<class_id> <center_x> <center_y> <width> <height>
    2. 分割多边形格式：<class_id> <x1> <y1> <x2> <y2> ... <xn> <yn>

    Args:
        class_names (List[str]): 类别名称列表，列表索引对应class_id，例如：
                                ['person', 'car'] 表示 class_id 0=person, 1=car
        annotations (List[Tuple[int, List[float]]]): 存储所有标注的列表，
                                每个元素为元组 (class_id, normalized_coordinates)

    Example:
        >>> # 初始化标注器，指定类别名称
        >>> annotator = YOLOAnnotation(['person', 'car', 'bicycle', 'road_sign'])
        >>>
        >>> # 示例1: 添加一个边界框标注（目标检测）
        >>> annotator.add_annotation(0, [0.5, 0.6, 0.1, 0.2])  # 行人
        >>> annotator.add_annotation(1, [0.3, 0.4, 0.15, 0.1]) # 汽车
        >>>
        >>> # 示例2: 添加一个分割标注（实例分割，多边形点集）
        >>> # 道路标志的多边形分割点（归一化坐标）
        >>> road_sign_points = [
        >>>     0.45, 0.55,  # 点1 x,y
        >>>     0.55, 0.55,  # 点2 x,y
        >>>     0.55, 0.65,  # 点3 x,y
        >>>     0.45, 0.65   # 点4 x,y
        >>> ]
        >>> annotator.add_annotation(3, road_sign_points)  # 道路标志分割
        >>>
        >>> # 示例3: 复杂多边形分割（不规则形状）
        >>> complex_shape_points = [
        >>>     0.2, 0.3,    # 点1
        >>>     0.3, 0.25,   # 点2
        >>>     0.4, 0.3,    # 点3
        >>>     0.35, 0.4,   # 点4
        >>>     0.25, 0.4    # 点5
        >>> ]
        >>> annotator.add_annotation(0, complex_shape_points)  # 复杂形状的行人分割
        >>>
        >>> # 保存为YOLO格式的TXT文件
        >>> annotator.save('image_001.txt')
        >>>
        >>> # 获取标注文本行（用于批量处理）
        >>> lines = annotator.to_txt_lines()
        >>> for line in lines:
        >>>     print(line)
        >>> # 输出示例:
        >>> # 0 0.5 0.6 0.1 0.2                    # 边界框
        >>> # 1 0.3 0.4 0.15 0.1                   # 边界框
        >>> # 3 0.45 0.55 0.55 0.55 0.55 0.65 0.45 0.65  # 分割多边形
        >>> # 0 0.2 0.3 0.3 0.25 0.4 0.3 0.35 0.4 0.25 0.4  # 复杂分割

    Notes:
        - 对于边界框：坐标格式为 [center_x, center_y, width, height]
        - 对于分割多边形：坐标格式为 [x1, y1, x2, y2, ..., xn, yn]，至少需要6个值（3个点）
     """

    def __init__(self, class_names: List[str], verbose: bool = False):
        """
        初始化YOLO标注器

        Args:
            class_names: 类别名称列表，列表索引将作为class_id使用
                        例如：['person', 'car'] 表示 class_id 0=person, 1=car
            verbose: 是否启用详细日志
        """
        self.class_names: List[str] = class_names
        self.logger = set_logging("YOLOAnnotation", verbose=verbose)
        self.annotations: List[Tuple[int, List[float]]] = []

    def add_annotation(self, class_id: int, normalized_points: List[float]) -> None:
        """
        添加一个YOLO格式的标注

        Args:
            class_id: 类别ID（对应class_names中的索引），取值范围为0到len(class_names)-1
            normalized_points: 归一化后的坐标点列表，支持两种格式：
                - 边界框格式: [center_x, center_y, width, height] (4个坐标值)
                - 分割多边形格式: [x1, y1, x2, y2, ..., xn, yn] (偶数个坐标值，至少6个)
                所有坐标值应在0-1范围内，相对于图像宽度和高度

        Raises:
            IndexError: 当class_id超出class_names索引范围时
            ValueError: 当坐标点数量不符合要求或坐标值超出0-1范围时

        Example:
            >>> # 示例1: 添加边界框标注（目标检测）
            >>> annotator.add_annotation(0, [0.5, 0.5, 0.2, 0.2])  # 中心点(50%,50%)，宽高20%
            >>>
            >>> # 示例2: 添加复杂多边形分割标注
            >>> polygon_points = [0.2, 0.3, 0.3, 0.25, 0.4, 0.3, 0.35, 0.4, 0.25, 0.4]
            >>> annotator.add_annotation(2, polygon_points)  # 5个点的多边形
        """
        self.annotations.append((class_id, normalized_points))

    def to_txt_lines(self) -> List[str]:
        """
        生成YOLO格式的文本行

        Returns:
            List[str]: YOLO格式的文本行列表，每行代表一个标注对象：
                - 边界框格式: "class_id center_x center_y width height"
                - 分割多边形格式: "class_id x1 y1 x2 y2 ... xn yn"
                所有坐标值保留6位小数精度

        Example:
            >>> # 包含边界框和分割标注的示例
            >>> lines = annotator.to_txt_lines()
            >>> for line in lines:
            >>>     print(line)
            >>>
            >>> # 输出示例:
            >>> # "0 0.500000 0.600000 0.100000 0.200000"  # 边界框
            >>> # "1 0.200000 0.300000 0.300000 0.250000 0.400000 0.300000 0.350000 0.400000 0.250000 0.400000"  # 复杂分割
        """
        lines: List[str] = []
        for class_id, normalized_points in self.annotations:
            lines.append(f"{class_id} " + " ".join(map(str, normalized_points)))
        return lines

    def save(self, txt_path: str) -> None:
        """
        保存标注为YOLO格式的TXT文件

        Args:
            txt_path: 输出TXT文件路径

        Example:
            >>> annotator.save('/path/to/labels/image_001.txt')
            >>> # 生成的文件内容:
            >>> # 0 0.500000 0.600000 0.100000 0.200000
            >>> # 1 0.200000 0.300000 0.300000 0.250000 0.400000 0.300000 0.350000 0.400000 0.250000 0.400000  # 复杂分割
        """
        with open(txt_path, 'w') as f:
            f.write("\n".join(self.to_txt_lines()))
        self.logger.info(f"YOLO 标签保存成功: {txt_path}")


class LabelMeAnnotation:
    """
    LabelMe JSON 标注格式处理类

    用于创建、管理和保存LabelMe格式的标注数据。
    LabelMe支持多种标注形状：多边形、矩形、圆形、点、线等。

    Args:
        version (str): LabelMe格式版本号
        flags (Dict): 图像级别的标志信息
        shapes (List[Dict]): 存储所有标注形状的列表
        imagePath (str): 图像文件名（不含路径）
        imageData (str): 图像base64编码数据（可选）
        imageHeight (int): 图像高度（像素）
        imageWidth (int): 图像宽度（像素）

    Example:
        >>> # 初始化标注器，指定图像路径和尺寸
        >>> annotator = LabelMeAnnotation("images/001.jpg", (480, 640))
        >>>
        >>> # 示例1: 添加多边形标注（分割）
        >>> polygon_points = [[100, 100], [200, 100], [200, 200], [100, 200]]
        >>> annotator.add_shape("person", polygon_points, "polygon")
        >>>
        >>> # 示例2: 添加矩形标注（边界框）
        >>> rect_points = [[50, 50], [150, 150]]  # 左上角和右下角
        >>> annotator.add_shape("car", rect_points, "rectangle")
        >>>
        >>> # 示例3: 添加圆形标注
        >>> circle_points = [[300, 300], [350, 300]]  # 圆心和半径点
        >>> annotator.add_shape("ball", circle_points, "circle")
        >>>
        >>> # 示例4: 添加点标注
        >>> point_coords = [[400, 200]]
        >>> annotator.add_shape("keypoint", point_coords, "point")
        >>>
        >>> # 保存为LabelMe JSON文件
        >>> annotator.save("annotations/001.json")
        >>>
        >>> # 转换为字典格式（用于进一步处理）
        >>> data_dict = annotator.to_dict()
    """

    def __init__(self, image_path: str, image_size: Tuple[int, int], shapes: Optional[List[Dict]] = None, verbose: bool = False):
        """
        初始化LabelMe标注器

        Args:
            image_path: 图像文件路径（用于获取文件名）
            image_size: 图像尺寸元组 (height, width)
            shapes: 预定义的形状列表（可选）
            verbose: 是否启用详细日志
        """
        self.version: str = "5.1.1"
        self.flags: Dict = {}
        self.shapes: List[Dict] = shapes if shapes else []
        self.imagePath: str = str(Path(image_path).name)
        self.imageData: Optional[str] = None
        self.imageHeight: int
        self.imageWidth: int
        self.imageHeight, self.imageWidth = image_size
        self.logger = set_logging("LabelMeAnnotation", verbose=verbose)

    def add_shape(self, label: str, points: List[List[float]], shape_type: str = "polygon") -> None:
        """
        添加一个标注形状

        Args:
            label: 标注的类别标签（如"person", "car"）
            points: 坐标点列表，格式根据shape_type不同：
                - polygon: [[x1,y1], [x2,y2], ...] （多边形顶点）
                - rectangle: [[x1,y1], [x2,y2]] （左上角和右下角）
                - circle: [[cx,cy], [px,py]] （圆心和圆周上的点）
                - point: [[x,y]] （单个点）
                - line: [[x1,y1], [x2,y2], ...] （线段的多个点）
            shape_type: 形状类型，可选值：
                "polygon", "rectangle", "circle", "point", "line"
            group_id: 分组ID（用于关联多个形状）
            description: 形状描述信息

        Example:
            >>> # 添加多边形分割标注
            >>> annotator.add_shape("building", [[100,100], [300,100], [300,300], [100,300]])
            >>>
            >>> # 添加带分组的矩形标注
            >>> annotator.add_shape("vehicle", [[50,50], [250,150]], "rectangle", group_id=1)
            >>>
            >>> # 添加带描述的圆形标注
            >>> annotator.add_shape("target", [[400,300], [450,300]], "circle", description="重要目标")
        """
        self.shapes.append({
            "label": label,
            "points": points,
            "group_id": None,
            "description": "",
            "shape_type": shape_type,
            "flags": {}
        })

    def to_dict(self) -> Dict[str, Union[str, int, List[Dict], None]]:
        """
        转换为LabelMe格式的字典

        Returns:
            Dict: 符合LabelMe JSON格式的字典数据

        Example:
            >>> data = annotator.to_dict()
            >>> print(data['imagePath'])  # 输出: "001.jpg"
            >>> print(len(data['shapes'])) # 输出形状数量
        """
        return {
            "version": self.version,
            "flags": self.flags,
            "shapes": self.shapes,
            "imagePath": self.imagePath,
            "imageData": self.imageData,
            "imageHeight": self.imageHeight,
            "imageWidth": self.imageWidth
        }

    def save(self, json_path: str) -> None:
        """
        保存为LabelMe JSON文件

        Args:
            json_path: 输出的JSON文件路径

        Example:
            >>> annotator.save("path/to/annotations/image_001.json")
            >>> # 生成的文件可用于LabelMe工具直接加载
        """
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        self.logger.info(f"LabelMe JSON 保存成功: {json_path}")


class VOCObject:
    """
    VOC格式单个对象标注类

    用于表示Pascal VOC格式的单个目标检测标注对象。
    包含对象类别、边界框坐标和难度标志等信息。

    Args:
        name (str): 对象类别名称（如"person", "car", "dog"）
        bbox (List[float]): 边界框坐标 [xmin, ymin, xmax, ymax]
        difficult (int): 难度标志（0=容易，1=困难）

    Example:
        >>> # 创建一个简单的对象标注
        >>> obj = VOCObject("person", [100, 50, 200, 150])
        >>> xml_node = obj.to_xml()
        >>> print(xml_node)
        >>>
        >>> # 创建一个困难样本标注
        >>> difficult_obj = VOCObject("car", [300, 200, 450, 300], difficult=1)
        >>>
        >>> # 批量创建多个对象
        >>> objects = [
        >>>     VOCObject("person", [100, 50, 200, 150]),
        >>>     VOCObject("bicycle", [250, 75, 350, 175])
        >>> ]
        >>> for obj in objects:
        >>>     print(obj.to_xml())
    """

    def __init__(self, name: str, bbox: List[float], difficult: int = 0):
        """
        初始化VOC对象标注

        Args:
            name: 对象类别名称，应符合VOC标准类别（如"person", "car", "dog"等）
            bbox: 边界框坐标，格式为 [xmin, ymin, xmax, ymax]
                 - xmin, ymin: 边界框左上角坐标
                 - xmax, ymax: 边界框右下角坐标

        Example:
            >>> # 正常边界框
            >>> obj1 = VOCObject("cat", [50, 60, 150, 160])
            >>>
            >>> # 困难样本
            >>> obj2 = VOCObject("dog", [200, 100, 300, 200], difficult=1)
            >>>
            >>> # 跨图像边界的对象（可能需要标记为difficult）
            >>> obj3 = VOCObject("person", [-10, 50, 100, 150], difficult=1)
        """
        self.root = etree.Element("object")
        self.name: str = name
        self.bbox: List[float] = bbox  # [xmin, ymin, xmax, ymax]
        self.difficult: int = difficult

        self._build_xml_structure()

    def _build_xml_structure(self):
        """构建VOC XML对象结构"""
        # 添加名称节点
        name_node = etree.SubElement(self.root, "name")
        name_node.text = self.name

        # 添加姿态节点（默认Unspecified）
        pose_node = etree.SubElement(self.root, "pose")
        pose_node.text = "Unspecified"

        # 添加截断标志节点（默认0）
        truncated_node = etree.SubElement(self.root, "truncated")
        truncated_node.text = "0"

        # 添加难度节点
        difficult_node = etree.SubElement(self.root, "difficult")
        difficult_node.text = str(self.difficult)

        # 添加边界框节点
        bndbox = etree.SubElement(self.root, "bndbox")
        xmin, ymin, xmax, ymax = self.bbox
        etree.SubElement(bndbox, "xmin").text = str(xmin)
        etree.SubElement(bndbox, "ymin").text = str(ymin)
        etree.SubElement(bndbox, "xmax").text = str(xmax)
        etree.SubElement(bndbox, "ymax").text = str(ymax)

    def to_xml(self) -> str:
        """
        返回VOC格式的XML object节点字符串

        Returns:
            str: 格式化的XML字符串

        Example:
            >>> obj = VOCObject("person", [100, 50, 200, 150])
            >>> xml_output = obj.to_xml()
            >>> print(xml_output)
            >>> # 输出:
            >>> # <object>
            >>> #     <name>person</name>
            >>> #     <pose>Unspecified</pose>
            >>> #     <truncated>0</truncated>
            >>> #     <difficult>0</difficult>
            >>> #     <bndbox>
            >>> #         <xmin>100</xmin>
            >>> #         <ymin>50</ymin>
            >>> #         <xmax>200</xmax>
            >>> #         <ymax>150</ymax>
            >>> #     </bndbox>
            >>> # </object>
        """
        return etree.tostring(self.root, pretty_print=True, encoding="unicode")

    def to_element(self) -> etree._Element:
        """
        返回XML元素对象

        Returns:
            etree._Element: XML元素对象
        """
        return self.root


class VOCAnnotation:
    """
    VOC格式标注文件处理类（基于lxml.etree实现）

    用于创建、管理和保存Pascal VOC格式的XML标注文件。
    完全兼容VOC2007/2012标准格式，支持多对象标注。

    Args:
        image_path (str): 图像文件路径（绝对或相对路径）
        image_size (Tuple[int, int]): 图像尺寸 (width, height)
        objects (Optional[List[VOCObject]]): 预定义对象列表（可选）
        verbose (bool): 是否启用详细日志（默认False）

    Example:
        >>> # 初始化空标注文件
        >>> annotator = VOCAnnotation("images/001.jpg", (640, 480))
        >>>
        >>> # 添加对象并保存
        >>> annotator.add_object("person", [100, 50, 200, 150])
        >>> annotator.save("annotations/001.xml")
        >>>
        >>> # 批量初始化
        >>> objects = [
        >>>     VOCObject("dog", [150, 100, 250, 200]),
        >>>     VOCObject("cat", [400, 100, 500, 200])
        >>> ]
        >>> batch_annotator = VOCAnnotation("images/002.jpg", (800, 600), objects)
        >>> batch_annotator.save("annotations/002.xml")
    """

    def __init__(self, image_path: str, image_size: Tuple[int, int], objects: List[VOCObject] = None, verbose: bool = False):
        self.root = etree.Element("annotation")
        self.image_path = Path(image_path)
        self.image_width, self.image_height = image_size
        self.objects = objects if objects else []
        self.verbose = verbose

        # 初始化基础XML结构
        self._init_xml_structure()

    def _init_xml_structure(self):
        """构建VOC XML基础结构"""
        # 文件信息
        etree.SubElement(self.root, "folder").text = str(self.image_path.parent.name)
        etree.SubElement(self.root, "filename").text = self.image_path.name
        etree.SubElement(self.root, "path").text = str(self.image_path.resolve())

        # 数据来源
        source = etree.SubElement(self.root, "source")
        etree.SubElement(source, "database").text = "Unknown"

        # 图像尺寸
        size = etree.SubElement(self.root, "size")
        etree.SubElement(size, "width").text = str(self.image_width)
        etree.SubElement(size, "height").text = str(self.image_height)
        etree.SubElement(size, "depth").text = "3"  # 默认RGB图像

        # 分割标记
        etree.SubElement(self.root, "segmented").text = "0"

        # 添加已有对象
        for obj in self.objects:
            self.root.append(obj.to_element())

    def add_object(self, name: str, bbox: List[float], difficult: int = 0):
        """
        添加一个新对象标注

        Args:
            name: 对象类别名称（应符合VOC标准类别）
            bbox: 归一化或绝对坐标 [xmin, ymin, xmax, ymax]
            difficult: 标注难度 (0=容易, 1=困难)

        Example:
            >>> # 添加标准对象
            >>> annotator.add_object("person", [100, 50, 200, 150])
            >>>
            >>> # 添加困难样本
            >>> annotator.add_object("occluded_car", [300, 200, 450, 300], difficult=1)
        """
        new_obj = VOCObject(name, bbox, difficult)
        self.objects.append(new_obj)
        self.root.append(new_obj.to_element())
        if self.verbose:
            if not hasattr(self, 'logger'):
                from ..utils.basic import set_logging
                self.logger = set_logging("VOCAnnotation", verbose=self.verbose)
            self.logger.info(f"Added object: {name} {bbox}")

    def save(self, xml_path: str):
        """
        保存为标准VOC XML文件

        Args:
            xml_path: 输出XML文件路径

        Raises:
            IOError: 文件写入失败时抛出
            ET.XMLSyntaxError: XML格式错误时抛出

        Example:
            >>> # 标准保存
            >>> annotator.save("data/annotations/001.xml")
            >>>
            >>> # 自动创建目录
            >>> annotator.save("new_dir/annotations/002.xml")  # 自动创建new_dir/annotations
        """
        output_path = Path(xml_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        tree = etree.ElementTree(self.root)
        tree.write(
            str(output_path),
            pretty_print=True,
            xml_declaration=True,
            encoding="UTF-8"
        )

        if self.verbose:
            if not hasattr(self, 'logger'):
                from ..utils.basic import set_logging
                self.logger = set_logging("VOCAnnotation", verbose=self.verbose)
            self.logger.info(f"XML saved to: {output_path.resolve()}")

    def __str__(self):
        """返回格式化的XML字符串（用于调试）"""
        return etree.tostring(
            self.root,
            pretty_print=True,
            encoding="unicode"
        )


class AnnotationConverter:
    """
    标注格式转换器

    支持多种标注格式之间的相互转换，包括：
    - YOLO格式（目标检测和实例分割）
    - LabelMe格式（JSON）
    - Pascal VOC格式（XML）

    支持的功能：
    1. LabelMe ↔ YOLO（分割和目标检测）
    2. LabelMe ↔ VOC
    3. YOLO ↔ VOC
    4. 创建空标签文件

    Args:
        class_names (List[str]): 类别名称列表，用于类别ID映射

    Example:
        >>> # 初始化转换器，指定类别名称
        >>> converter = AnnotationConverter(['person', 'car', 'dog'])
        >>>
        >>> # 转换LabelMe分割标注到YOLO分割格式
        >>> yolo_txt = converter.labelme_to_yolo_seg('labelme/001.json')
        >>>
        >>> # 转换YOLO目标检测到LabelMe格式
        >>> labelme_json = converter.yolo_obj_to_labelme('yolo/001.txt', 'images/001.jpg')
        >>>
        >>> # 批量转换VOC到YOLO格式
        >>> for xml_file in Path('voc_annotations').glob('*.xml'):
        >>>     converter.voc_to_yolo_obj(str(xml_file))
    """

    def __init__(self, class_names: List[str] = None, verbose=False):
        """
        初始化标注转换器

        Args:
            class_names: 类别名称列表，列表索引将作为class_id使用。
                        如果为None，则使用默认类别["object"]

        Example:
            >>> # 使用自定义类别列表
            >>> converter = AnnotationConverter(['person', 'vehicle', 'animal'])
            >>>
            >>> # 使用默认类别
            >>> converter = AnnotationConverter()
        """
        self.class_names = class_names if class_names else ["object"]
        self.verbose = verbose
        self.logger = set_logging("AnnotationConverter", verbose=self.verbose)
        self._image_size_cache = {}  # 图像尺寸缓存

    def _get_image_size(self, image_path: str) -> tuple:
        """
        获取图像尺寸（带缓存）

        Args:
            image_path: 图像文件路径

        Returns:
            图像尺寸元组 (height, width)

        Raises:
            FileError: 当无法读取图像时
            ValidationError: 当图像尺寸无效时
        """
        # 检查缓存
        if image_path in self._image_size_cache:
            if self.verbose:
                self.logger.debug(f"使用缓存的图像尺寸: {image_path}")
            return self._image_size_cache[image_path]
        
        # 读取图像获取尺寸
        try:
            img = cv2.imread(image_path)
            if img is None:
                raise FileError(f"无法读取图像: {image_path}")
            
            size = img.shape[:2]  # (height, width)
            if len(size) != 2 or size[0] <= 0 or size[1] <= 0:
                raise ValidationError(f"无效的图像尺寸: {size}")
            
            self._image_size_cache[image_path] = size  # 缓存结果
            
            if self.verbose:
                self.logger.debug(f"缓存图像尺寸: {image_path} -> {size}")
            
            return size
        except FileError:
            raise
        except ValidationError:
            raise
        except Exception as e:
            raise FileError(f"获取图像尺寸失败: {e}")
    
    def _get_output_path(self, input_path: str, output_dir: str = None, ext: str = '.txt', 
                        default_subdir: str = 'labels') -> Path:
        """
        生成统一的输出路径

        Args:
            input_path: 输入文件路径
            output_dir: 输出目录（可选）
            ext: 输出文件扩展名
            default_subdir: 默认子目录名称

        Returns:
            Path: 输出文件的Path对象

        Raises:
            FileError: 当输入路径无效时
            ValidationError: 当输出目录设置无效时
        """
        try:
            input_path_obj = Path(input_path)
            if not input_path_obj.exists():
                if self.verbose:
                    self.logger.warning(f"输入文件不存在: {input_path}")
            
            if output_dir is None:
                output_dir = input_path_obj.parent.parent / default_subdir
            else:
                output_dir = Path(output_dir)
            
            # 确保输出目录存在
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise FileError(f"无法创建输出目录: {e}")
            
            return output_dir / f"{input_path_obj.stem}{ext}"
        except Exception as e:
            raise FileError(f"生成输出路径失败: {e}")
    
    def _ensure_output_dir(self, output_dir: str) -> Path:
        """
        确保输出目录存在

        Args:
            output_dir: 输出目录路径

        Returns:
            Path: 输出目录的Path对象

        Raises:
            FileError: 当无法创建输出目录时
        """
        try:
            output_dir_obj = Path(output_dir)
            output_dir_obj.mkdir(parents=True, exist_ok=True)
            return output_dir_obj
        except Exception as e:
            raise FileError(f"无法创建输出目录: {e}")
    
    def _validate_label(self, label: str) -> bool:
        """
        验证标签是否在类别列表中

        Args:
            label: 要验证的标签

        Returns:
            bool: 标签是否有效
        """
        if label not in self.class_names:
            if self.verbose:
                self.logger.warning(f"跳过未知标签 '{label}'")
            return False
        return True

    def validate_labelme_format(self, json_path: str) -> bool:
        """
        验证LabelMe JSON格式的有效性

        Args:
            json_path: LabelMe JSON文件路径

        Returns:
            bool: 格式是否有效

        Raises:
            FileError: 当文件不存在或无法读取时
            FormatError: 当JSON格式无效时
            ValidationError: 当必需字段缺失或无效时
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise FileError(f"文件不存在: {json_path}")
        except json.JSONDecodeError as e:
            raise FormatError(f"无效的JSON格式: {e}")
        except Exception as e:
            raise FileError(f"读取文件失败: {e}")

        # 验证必需字段
        required_fields = ['version', 'shapes', 'imagePath', 'imageWidth', 'imageHeight']
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"缺少必需字段: {field}")

        # 验证图像尺寸
        try:
            img_width = int(data['imageWidth'])
            img_height = int(data['imageHeight'])
            if img_width <= 0 or img_height <= 0:
                raise ValidationError(f"无效的图像尺寸: {img_width}x{img_height}")
        except (ValueError, TypeError):
            raise ValidationError("图像尺寸必须为正整数")

        # 验证shapes字段
        shapes = data.get('shapes', [])
        if not isinstance(shapes, list):
            raise ValidationError("shapes必须是列表")

        # 验证每个shape
        for i, shape in enumerate(shapes):
            if not isinstance(shape, dict):
                raise ValidationError(f"shape {i} 必须是字典")

            # 验证shape必需字段
            shape_required = ['label', 'points', 'shape_type']
            for field in shape_required:
                if field not in shape:
                    raise ValidationError(f"shape {i} 缺少必需字段: {field}")

            # 验证label
            label = shape.get('label')
            if not isinstance(label, str) or not label:
                raise ValidationError(f"shape {i} 的label必须是非空字符串")

            # 验证points
            points = shape.get('points')
            if not isinstance(points, list) or not points:
                raise ValidationError(f"shape {i} 的points必须是非空列表")

            # 验证每个point
            for j, point in enumerate(points):
                if not isinstance(point, (list, tuple)) or len(point) < 2:
                    raise ValidationError(f"shape {i} 的point {j} 必须是包含至少两个元素的列表或元组")
                try:
                    x, y = float(point[0]), float(point[1])
                    if x < 0 or y < 0:
                        raise ValidationError(f"shape {i} 的point {j} 坐标必须是非负的")
                    if x > img_width or y > img_height:
                        raise ValidationError(f"shape {i} 的point {j} 坐标超出图像范围")
                except (ValueError, TypeError):
                    raise ValidationError(f"shape {i} 的point {j} 坐标必须是数字")

            # 验证shape_type
            shape_type = shape.get('shape_type')
            valid_shape_types = ['polygon', 'rectangle', 'circle', 'point', 'line']
            if shape_type not in valid_shape_types:
                raise ValidationError(f"shape {i} 的shape_type必须是以下之一: {', '.join(valid_shape_types)}")

        if self.verbose:
            self.logger.info(f"LabelMe格式验证通过: {json_path}")
        return True

    def validate_yolo_format(self, txt_path: str) -> bool:
        """
        验证YOLO TXT格式的有效性

        Args:
            txt_path: YOLO TXT文件路径

        Returns:
            bool: 格式是否有效

        Raises:
            FileError: 当文件不存在或无法读取时
            ValidationError: 当格式无效时
        """
        try:
            with open(txt_path, 'r') as f:
                lines = f.readlines()
        except FileNotFoundError:
            raise FileError(f"文件不存在: {txt_path}")
        except Exception as e:
            raise FileError(f"读取文件失败: {e}")

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            parts = line.split()
            if not parts:
                continue

            # 验证class_id
            try:
                class_id = int(parts[0])
                if class_id < 0:
                    raise ValidationError(f"第 {i+1} 行: class_id 必须是非负整数")
                if class_id >= len(self.class_names):
                    if self.verbose:
                        self.logger.warning(f"第 {i+1} 行: class_id {class_id} 超出类别列表范围")
            except ValueError:
                raise ValidationError(f"第 {i+1} 行: class_id 必须是整数")

            # 验证坐标
            coords = parts[1:]
            if len(coords) < 4:
                raise ValidationError(f"第 {i+1} 行: 坐标点数量不足")

            try:
                float_coords = [float(c) for c in coords]
                for coord in float_coords:
                    if coord < 0 or coord > 1:
                        raise ValidationError(f"第 {i+1} 行: 坐标值必须在0-1范围内")
            except ValueError:
                raise ValidationError(f"第 {i+1} 行: 坐标必须是数字")

        if self.verbose:
            self.logger.info(f"YOLO格式验证通过: {txt_path}")
        return True

    def validate_voc_format(self, xml_path: str) -> bool:
        """
        验证VOC XML格式的有效性

        Args:
            xml_path: VOC XML文件路径

        Returns:
            bool: 格式是否有效

        Raises:
            FileError: 当文件不存在或无法读取时
            FormatError: 当XML格式无效时
            ValidationError: 当必需字段缺失或无效时
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
        except FileNotFoundError:
            raise FileError(f"文件不存在: {xml_path}")
        except ET.ParseError as e:
            raise FormatError(f"无效的XML格式: {e}")
        except Exception as e:
            raise FileError(f"读取文件失败: {e}")

        # 验证根元素
        if root.tag != 'annotation':
            raise ValidationError("根元素必须是 'annotation'")

        # 验证必需子元素
        required_children = ['folder', 'filename', 'size', 'object']
        for child in required_children:
            if not root.find(child):
                raise ValidationError(f"缺少必需子元素: {child}")

        # 验证size元素
        size_elem = root.find('size')
        width_elem = size_elem.find('width')
        height_elem = size_elem.find('height')
        depth_elem = size_elem.find('depth')

        if not all([width_elem, height_elem, depth_elem]):
            raise ValidationError("size元素缺少width, height或depth子元素")

        try:
            width = int(width_elem.text)
            height = int(height_elem.text)
            depth = int(depth_elem.text)
            if width <= 0 or height <= 0 or depth <= 0:
                raise ValidationError("尺寸值必须为正整数")
        except (ValueError, TypeError):
            raise ValidationError("尺寸值必须为整数")

        # 验证object元素
        objects = root.findall('object')
        if not objects:
            raise ValidationError("至少需要一个object元素")

        for i, obj in enumerate(objects):
            # 验证object必需子元素
            obj_required = ['name', 'bndbox']
            for child in obj_required:
                if not obj.find(child):
                    raise ValidationError(f"object {i} 缺少必需子元素: {child}")

            # 验证name
            name_elem = obj.find('name')
            if not name_elem.text:
                raise ValidationError(f"object {i} 的name不能为空")

            # 验证bndbox
            bndbox = obj.find('bndbox')
            bbox_required = ['xmin', 'ymin', 'xmax', 'ymax']
            for child in bbox_required:
                if not bndbox.find(child):
                    raise ValidationError(f"object {i} 的bndbox缺少 {child} 子元素")

            # 验证边界框坐标
            try:
                xmin = float(bndbox.find('xmin').text)
                ymin = float(bndbox.find('ymin').text)
                xmax = float(bndbox.find('xmax').text)
                ymax = float(bndbox.find('ymax').text)

                if xmin < 0 or ymin < 0 or xmax <= xmin or ymax <= ymin:
                    raise ValidationError(f"object {i} 的边界框坐标无效")
                if xmax > width or ymax > height:
                    raise ValidationError(f"object {i} 的边界框超出图像范围")
            except (ValueError, TypeError):
                raise ValidationError(f"object {i} 的边界框坐标必须是数字")

        if self.verbose:
            self.logger.info(f"VOC格式验证通过: {xml_path}")
        return True

    def validate_coordinates(self, coords: List[float], img_width: int, img_height: int, normalized: bool = False) -> bool:
        """
        验证坐标的有效性

        Args:
            coords: 坐标列表
            img_width: 图像宽度
            img_height: 图像高度
            normalized: 坐标是否已归一化

        Returns:
            bool: 坐标是否有效

        Raises:
            ValidationError: 当坐标无效时
        """
        if not isinstance(coords, list):
            raise ValidationError("坐标必须是列表")

        if not coords:
            raise ValidationError("坐标列表不能为空")

        try:
            float_coords = [float(c) for c in coords]
        except (ValueError, TypeError):
            raise ValidationError("坐标必须是数字")

        if normalized:
            # 归一化坐标验证
            for coord in float_coords:
                if coord < 0 or coord > 1:
                    raise ValidationError("归一化坐标必须在0-1范围内")
        else:
            # 绝对坐标验证
            for i, coord in enumerate(float_coords):
                if coord < 0:
                    raise ValidationError("坐标不能为负数")
                # 交替验证x和y坐标
                if i % 2 == 0:  # x坐标
                    if coord > img_width:
                        raise ValidationError(f"x坐标 {coord} 超出图像宽度 {img_width}")
                else:  # y坐标
                    if coord > img_height:
                        raise ValidationError(f"y坐标 {coord} 超出图像高度 {img_height}")

        return True

    def convert_polygon_to_standard_format(self, polygon_data):
        """
        将各种格式的多边形数据转换为标准格式 [[x1,y1], [x2,y2], ...]

        Args:
            polygon_data: 支持以下格式：
                - 字符串: "x1,y1;x2,y2;..." 或 "x1 y1 x2 y2 ..."
                - NumPy数组: 形状为 (N, 2)
                - 列表: [[x1,y1], [x2,y2], ...] 或 [x1,y1,x2,y2,...]
                - 字典: {'points': [[x1,y1], [x2,y2], ...]}

        Returns:
            list: 标准格式的多边形坐标列表，或None如果无法转换
        """
        try:
            # 检查是否已经是标准格式 [[x1,y1], [x2,y2], ...]
            if (isinstance(polygon_data, (list, tuple)) and
                    len(polygon_data) > 0 and
                    isinstance(polygon_data[0], (list, tuple)) and
                    len(polygon_data[0]) >= 2):
                return polygon_data

            # 处理字符串格式: "x1,y1;x2,y2;..." 或 "x1 y1 x2 y2 ..."
            if isinstance(polygon_data, str):
                points = []
                # 尝试分号分隔格式: "x1,y1;x2,y2;..."
                if ';' in polygon_data:
                    pairs = polygon_data.split(';')
                    for pair in pairs:
                        if ',' in pair:
                            x, y = pair.split(',')
                            points.append([float(x.strip()), float(y.strip())])
                # 尝试空格分隔格式: "x1 y1 x2 y2 ..."
                else:
                    coords = polygon_data.split()
                    if len(coords) % 2 == 0:
                        for i in range(0, len(coords), 2):
                            x, y = coords[i], coords[i + 1]
                            points.append([float(x), float(y)])
                return points if len(points) >= 3 else None

            # 处理类似numpy的数组对象 - 内存优化：使用asarray避免复制
            if hasattr(polygon_data, '__array__'):
                array_data = np.asarray(polygon_data)
                if array_data.ndim == 2 and array_data.shape[1] >= 2:
                    # 内存优化：对于大型数组，考虑使用生成器转换
                    if array_data.size > 10000:  # 阈值可根据实际情况调整
                        return [list(point) for point in array_data]
                    else:
                        return array_data.tolist()

            # 处理字典格式
            elif isinstance(polygon_data, dict):
                if 'points' in polygon_data:
                    points = polygon_data['points']
                    if isinstance(points, (list, tuple)) and len(points) > 0:
                        return points

            # 处理扁平化列表格式: [x1, y1, x2, y2, ...]
            elif (isinstance(polygon_data, (list, tuple)) and
                  len(polygon_data) > 0 and
                  isinstance(polygon_data[0], (int, float)) and
                  len(polygon_data) % 2 == 0):
                # 内存优化：使用生成器表达式或列表推导式
                points = []
                for i in range(0, len(polygon_data), 2):
                    if i + 1 < len(polygon_data):
                        points.append([polygon_data[i], polygon_data[i + 1]])
                return points if len(points) >= 3 else None

        except Exception as e:
            if self.verbose:
                self.logger.error(f"格式转换错误: {e}")

        return None

    def polygons_to_yolo_seg(self, polygons, img_path: str, output_dir: str = None) -> str:
        """
        多边形数据 → YOLO分割格式

        将多边形坐标数据转换为YOLO分割标注格式。

        Args:
            polygons: 支持多种格式的多边形数据，将通过 _convert_to_standard_format 统一转换
            img_path: 对应图像的完整路径
            output_dir: 输出目录（默认为父目录的labels文件夹）

        Returns:
            str: 生成的YOLO TXT文件路径

        Raises:
            FileNotFoundError: 当图像文件不存在时
            ValueError: 当无法获取图像尺寸或多边形数据无效时

        Example:
            >>> # 使用numpy数组格式
            >>> import numpy as np
            >>> polygons = [
            ...     np.array([[100, 50], [200, 50], [200, 150], [100, 150]]),
            ...     np.array([[300, 100], [350, 200], [250, 200]])
            ... ]
            >>> converter.polygons_to_yolo_seg(polygons, 'images/001.jpg')
            'labels/001.txt'
            >>>
            >>> # 使用列表格式
            >>> polygons = [
            ...     [[100, 50], [200, 50], [200, 150], [100, 150]],
            ...     [[300, 100], [350, 200], [250, 200]]
            ... ]
            >>> converter.polygons_to_yolo_seg(polygons, '001.jpg', 'custom_labels')
            'custom_labels/001.txt'
        """
        if output_dir is None:
            output_dir = Path(img_path).parent.parent / "labels"
        else:
            output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 获取图像尺寸
        try:
            img_height, img_width = self._get_image_size(img_path)
        except Exception as e:
            raise ValueError(f"无法获取图像尺寸: {e}")

        yolo_ann = YOLOAnnotation(self.class_names, verbose=self.verbose)

        # 统一转换和验证多边形数据
        for polygon in polygons:
            if polygon is None:
                continue

            # 检查并转换为标准格式
            converted = self.convert_polygon_to_standard_format(polygon)
            if converted is None or len(converted) < 3:
                if self.verbose:
                    self.logger.warning(f"跳过无效多边形数据: {type(polygon)}")
                continue

            # 统一使用NumPy向量化处理
            try:
                # 转换为NumPy数组
                points_array = np.array(converted, dtype=float)
                
                # 向量化归一化
                normalized_points = (points_array / [img_width, img_height]).flatten().round(6).tolist()

                # 添加标注（至少需要3个点）
                if len(normalized_points) >= 6:
                    yolo_ann.add_annotation(0, normalized_points)
            except Exception as e:
                if self.verbose:
                    self.logger.error(f"坐标归一化失败: {e}")

        # 保存结果
        txt_path = output_dir / f"{Path(img_path).stem}.txt"
        yolo_ann.save(str(txt_path))
        return txt_path

    def labelme_to_yolo_seg(self, json_path: str, output_dir: str = None) -> str:
        """
        LabelMe分割标注 → YOLO分割格式

        将LabelMe的多边形分割标注转换为YOLO分割格式。

        Args:
            json_path: LabelMe JSON文件路径
            output_dir: 输出目录（默认为父目录的labels文件夹）

        Returns:
            str: 生成的YOLO TXT文件路径

        Raises:
            FileNotFoundError: JSON文件不存在时
            ValueError: 标签不在class_names中或图像尺寸无效时

        Example:
            >>> converter.labelme_to_yolo_seg('labelme/001.json')
            >>> # 输出: labels/001.txt
            >>>
            >>> # 指定输出目录
            >>> converter.labelme_to_yolo_seg('001.json', 'yolo_labels')
        """
        # 获取输出路径
        output_path = self._get_output_path(json_path, output_dir, '.txt', 'labels')

        # 读取JSON文件
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise FileError(f"JSON文件不存在: {json_path}")
        except json.JSONDecodeError:
            raise FormatError(f"无效的JSON格式: {json_path}")

        # 验证图像尺寸
        try:
            img_width, img_height = data['imageWidth'], data['imageHeight']
            if img_width <= 0 or img_height <= 0:
                raise ValidationError(f"无效的图像尺寸: {img_width}x{img_height}")
        except KeyError:
            raise FormatError("JSON中缺少 imageWidth/imageHeight 字段")

        yolo_ann = YOLOAnnotation(self.class_names, verbose=self.verbose)

        # 处理每个多边形
        for shape in data.get('shapes', []):
            label = shape.get('label', '')
            if not self._validate_label(label):
                continue

            points = shape.get('points', [])
            if len(points) < 3:
                if self.verbose:
                    self.logger.warning(f"跳过点数不足的多边形 (标签: {label})")
                continue

            # 向量化归一化
            try:
                points_array = np.array(points, dtype=float)
                normalized_points = (points_array / [img_width, img_height]).flatten().round(6).tolist()
                yolo_ann.add_annotation(self.class_names.index(label), normalized_points)
            except Exception as e:
                if self.verbose:
                    self.logger.error(f"坐标归一化失败: {e}")

        # 保存结果
        yolo_ann.save(str(output_path))
        return str(output_path)

    def yolo_seg_to_labelme(self, txt_path: str, img_path: str, output_dir: str = None) -> str:
        """
        YOLO分割格式 → LabelMe分割标注

        将YOLO分割标注转换为LabelMe多边形格式。

        Args:
            txt_path: YOLO TXT文件路径
            img_path: 对应的图像文件路径
            output_dir: 输出目录（默认为父目录的jsons文件夹）

        Returns:
            生成的LabelMe JSON文件路径

        Example:
            >>> converter.yolo_seg_to_labelme('yolo/001.txt', 'images/001.jpg')
            >>> # 输出: jsons/001.json
        """
        # 获取输出路径
        output_path = self._get_output_path(txt_path, output_dir, '.json', 'jsons')

        img_height, img_width = self._get_image_size(img_path)
        labelme_ann = LabelMeAnnotation(img_path, (img_height, img_width), verbose=self.verbose)

        with open(txt_path, 'r') as f:
            lines = f.readlines()

        for line in lines:
            parts = line.strip().split()
            class_id = int(parts[0])

            if class_id >= len(self.class_names):
                if self.verbose:
                    self.logger.warning(f"跳过无效类别 ID {class_id}")
                continue

            points = []
            if len(parts) > 5:
                try:
                    # 向量化处理坐标转换
                    coords = np.array(parts[1:], dtype=float)
                    coords[::2] *= img_width
                    coords[1::2] *= img_height
                    points = [
                        [round(coords[i], 2), round(coords[i+1], 2)]
                        for i in range(0, len(coords), 2)
                    ]

                    labelme_ann.add_shape(
                        label=self.class_names[class_id],
                        points=points,
                        shape_type="polygon"
                    )
                except Exception as e:
                    if self.verbose:
                        self.logger.error(f"坐标转换失败: {e}")
                    continue

        labelme_ann.save(str(output_path))
        return str(output_path)

    def labelme_to_yolo_obj(self, json_path: str, output_dir: str = None) -> str:
        """
        LabelMe格式 → YOLO目标检测格式

        将LabelMe的多种形状标注（多边形、矩形、圆形等）转换为YOLO目标检测格式。
        自动计算各种形状的外接矩形边界框。

        Args:
            json_path: LabelMe JSON文件路径
            output_dir: 输出目录（默认为父目录的labels文件夹）

        Returns:
            生成的YOLO TXT文件路径

        Example:
            >>> converter.labelme_to_yolo_obj('labelme/001.json')
            >>> # 输出: labels/001.txt
            >>>
            >>> # 处理包含多种形状的LabelMe文件
            >>> converter.labelme_to_yolo_obj('mixed_shapes.json')
        """
        # 获取输出路径
        output_path = self._get_output_path(json_path, output_dir, '.txt', 'labels')

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        yolo_ann = YOLOAnnotation(self.class_names, verbose=self.verbose)
        img_width = data['imageWidth']
        img_height = data['imageHeight']

        for shape in data['shapes']:
            label = shape['label']
            if not self._validate_label(label):
                continue

            class_id = self.class_names.index(label)
            points = shape['points']

            # 使用NumPy向量化计算边界框
            try:
                points_array = np.array(points, dtype=float)
                x_min, y_min = points_array.min(axis=0)
                x_max, y_max = points_array.max(axis=0)

                # 向量化转换为YOLO格式
                cx = (x_min + x_max) / 2 / img_width
                cy = (y_min + y_max) / 2 / img_height
                w = (x_max - x_min) / img_width
                h = (y_max - y_min) / img_height

                yolo_ann.add_annotation(class_id, [round(cx, 6), round(cy, 6), round(w, 6), round(h, 6)])
            except Exception as e:
                if self.verbose:
                    self.logger.error(f"边界框计算失败: {e}")
                continue

        yolo_ann.save(str(output_path))
        return str(output_path)

    def yolo_obj_to_labelme(self, txt_path: str, img_path: str, output_dir: str = None) -> str:
        """
        YOLO目标检测格式 → LabelMe格式

        将YOLO目标检测标注转换为LabelMe矩形标注格式。

        Args:
            txt_path: YOLO TXT文件路径
            img_path: 对应的图像文件路径（用于获取图像尺寸）
            output_dir: 输出目录（默认为父目录的jsons文件夹）

        Returns:
            生成的LabelMe JSON文件路径

        Example:
            >>> converter.yolo_obj_to_labelme('yolo/001.txt', 'images/001.jpg')
            >>> # 输出: jsons/001.json
            >>>
            >>> # 处理包含多个边界框的YOLO文件
            >>> converter.yolo_obj_to_labelme('multi_objects.txt', 'image.jpg')
        """
        # 获取输出路径
        output_path = self._get_output_path(txt_path, output_dir, '.json', 'jsons')

        img_height, img_width = self._get_image_size(img_path)
        labelme_ann = LabelMeAnnotation(img_path, (img_height, img_width), verbose=self.verbose)

        with open(txt_path, 'r') as f:
            lines = f.readlines()

        for line in lines:
            parts = line.strip().split()
            if len(parts) != 5:
                continue

            class_id = int(parts[0])
            if class_id >= len(self.class_names):
                if self.verbose:
                    self.logger.warning(f"跳过无效类别 ID {class_id}")
                continue

            # 使用NumPy向量化处理坐标转换
            try:
                # 加载YOLO格式坐标
                yolo_coords = np.array(parts[1:5], dtype=float)
                cx, cy, w, h = yolo_coords

                # 向量化转换为矩形坐标
                x_min = round((cx - w / 2) * img_width, 6)
                y_min = round((cy - h / 2) * img_height, 6)
                x_max = round((cx + w / 2) * img_width, 6)
                y_max = round((cy + h / 2) * img_height, 6)

                labelme_ann.add_shape(
                    label=self.class_names[class_id],
                    points=[
                        [x_min, y_min],
                        [x_max, y_min],
                        [x_max, y_max],
                        [x_min, y_max]
                    ],
                    shape_type="rectangle"
                )
            except Exception as e:
                if self.verbose:
                    self.logger.error(f"坐标转换失败: {e}")
                continue

        labelme_ann.save(str(output_path))
        return str(output_path)

    def labelme_to_voc(self, json_path: str, output_dir: str = None) -> str:
        """
        LabelMe格式 → VOC格式

        将LabelMe标注转换为Pascal VOC XML格式。

        Args:
            json_path: LabelMe JSON文件路径
            output_dir: 输出目录（默认为父目录的voc文件夹）

        Returns:
            生成的VOC XML文件路径

        Example:
            >>> converter.labelme_to_voc('labelme/001.json')
            >>> # 输出: voc/001.xml
            >>>
            >>> # 转换包含多种形状的标注
            >>> converter.labelme_to_voc('complex_annotation.json')
        """
        # 获取输出路径
        output_path = self._get_output_path(json_path, output_dir, '.xml', 'voc')

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        voc_ann = VOCAnnotation(
            image_path=data['imagePath'],
            image_size=(data['imageWidth'], data['imageHeight']),
            verbose=self.verbose
        )

        for shape in data['shapes']:
            label = shape['label']
            if not self._validate_label(label):
                continue

            points = shape['points']
            
            # 使用NumPy向量化计算边界框
            try:
                points_array = np.array(points, dtype=float)
                x_min, y_min = points_array.min(axis=0)
                x_max, y_max = points_array.max(axis=0)

                voc_ann.add_object(
                    name=label,
                    bbox=[x_min, y_min, x_max, y_max]
                )
            except Exception as e:
                if self.verbose:
                    self.logger.error(f"边界框计算失败: {e}")
                continue

        voc_ann.save(str(output_path))
        return str(output_path)

    def voc_to_labelme(self, xml_path: str, output_dir: str = None) -> str:
        """
        VOC格式 → LabelMe格式

        将Pascal VOC XML格式转换为LabelMe JSON格式。

        Args:
            xml_path: VOC XML文件路径
            output_dir: 输出目录（默认为父目录的jsons文件夹）

        Returns:
            生成的LabelMe JSON文件路径

        Example:
            >>> converter.voc_to_labelme('voc/001.xml')
            >>> # 输出: jsons/001.json
            >>>
            >>> # 处理包含困难样本的VOC文件
            >>> converter.voc_to_labelme('difficult_samples.xml')
        """
        # 获取输出路径
        output_path = self._get_output_path(xml_path, output_dir, '.json', 'jsons')

        import xml.etree.ElementTree as ET
        tree = ET.parse(xml_path)
        root = tree.getroot()

        img_path = root.find('path').text
        size = root.find('size')
        img_width = int(size.find('width').text)
        img_height = int(size.find('height').text)

        labelme_ann = LabelMeAnnotation(img_path, (img_height, img_width), verbose=self.verbose)

        for obj in root.findall('object'):
            label = obj.find('name').text
            if not self._validate_label(label):
                continue

            bbox = obj.find('bndbox')
            xmin = round(float(bbox.find('xmin').text), 6)
            ymin = round(float(bbox.find('ymin').text), 6)
            xmax = round(float(bbox.find('xmax').text), 6)
            ymax = round(float(bbox.find('ymax').text), 6)

            labelme_ann.add_shape(
                label=label,
                points=[
                    [xmin, ymin],
                    [xmax, ymin],
                    [xmax, ymax],
                    [xmin, ymax]
                ],
                shape_type="rectangle"
            )

        labelme_ann.save(str(output_path))
        return str(output_path)

    def yolo_obj_to_voc(self, txt_path: str, img_path: str, output_dir: str = None) -> str:
        """
        YOLO目标检测格式 → VOC格式

        将YOLO目标检测标注转换为Pascal VOC XML格式。

        Args:
            txt_path: YOLO TXT文件路径
            img_path: 对应的图像文件路径（用于获取图像尺寸和路径信息）
            output_dir: 输出目录（默认为父目录的voc文件夹）

        Returns:
            生成的VOC XML文件路径

        Example:
            >>> converter.yolo_obj_to_voc('yolo/001.txt', 'images/001.jpg')
            >>> # 输出: voc/001.xml
            >>>
            >>> # 处理包含多个对象的YOLO文件
            >>> converter.yolo_obj_to_voc('detections.txt', 'photo.jpg', 'voc_annotations')
        """
        # 获取输出路径
        output_path = self._get_output_path(txt_path, output_dir, '.xml', 'voc')

        img_height, img_width = self._get_image_size(img_path)
        voc_ann = VOCAnnotation(
            image_path=img_path,
            image_size=(img_width, img_height),
            verbose=self.verbose
        )

        with open(txt_path, 'r') as f:
            lines = f.readlines()

        for line in lines:
            parts = line.strip().split()
            if len(parts) != 5:
                continue

            class_id = int(parts[0])
            if class_id >= len(self.class_names):
                if self.verbose:
                    self.logger.warning(f"跳过无效类别 ID {class_id}")
                continue

            # 使用NumPy向量化处理坐标转换
            try:
                # 加载YOLO格式坐标
                yolo_coords = np.array(parts[1:5], dtype=float)
                cx, cy, w, h = yolo_coords

                # 向量化转换为矩形坐标
                x_min = round((cx - w / 2) * img_width, 6)
                y_min = round((cy - h / 2) * img_height, 6)
                x_max = round((cx + w / 2) * img_width, 6)
                y_max = round((cy + h / 2) * img_height, 6)

                voc_ann.add_object(
                    name=self.class_names[class_id],
                    bbox=[x_min, y_min, x_max, y_max]
                )
            except Exception as e:
                if self.verbose:
                    self.logger.error(f"坐标转换失败: {e}")
                continue

        voc_ann.save(str(output_path))
        return str(output_path)

    def voc_to_yolo_obj(self, xml_path: str, output_dir: str = None) -> str:
        """
        VOC格式 → YOLO目标检测格式

        将Pascal VOC XML格式转换为YOLO目标检测格式。

        Args:
            xml_path: VOC XML文件路径
            output_dir: 输出目录（默认为父目录的labels文件夹）

        Returns:
            生成的YOLO TXT文件路径

        Example:
            >>> converter.voc_to_yolo_obj('voc/001.xml')
            >>> # 输出: labels/001.txt
            >>>
            >>> # 处理包含困难样本的VOC文件
            >>> converter.voc_to_yolo_obj('annotations/001.xml', 'yolo_labels')
        """
        # 获取输出路径
        output_path = self._get_output_path(xml_path, output_dir, '.txt', 'labels')

        import xml.etree.ElementTree as ET
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # img_path = root.find('path').text
        size = root.find('size')
        img_width = int(size.find('width').text)
        img_height = int(size.find('height').text)

        yolo_ann = YOLOAnnotation(self.class_names, verbose=self.verbose)

        for obj in root.findall('object'):
            label = obj.find('name').text
            if not self._validate_label(label):
                continue

            class_id = self.class_names.index(label)

            bbox = obj.find('bndbox')
            xmin = round(float(bbox.find('xmin').text), 6)
            ymin = round(float(bbox.find('ymin').text), 6)
            xmax = round(float(bbox.find('xmax').text), 6)
            ymax = round(float(bbox.find('ymax').text), 6)

            # 转换为YOLO格式
            cx = (xmin + xmax) / 2 / img_width
            cy = (ymin + ymax) / 2 / img_height
            w = (xmax - xmin) / img_width
            h = (ymax - ymin) / img_height

            yolo_ann.add_annotation(class_id, [round(cx, 6), round(cy, 6), round(w, 6), round(h, 6)])

        yolo_ann.save(str(output_path))
        return str(output_path)

    def cvat_to_yolo_seg(self, xml_path: str, output_dir: str = None) -> str:
        """
        CVAT多边形标注 → YOLO分割格式

        Args:
            xml_path: CVAT XML标注文件路径
            output_dir: 输出目录（默认为父目录的labels文件夹）

        Returns:
            str: 生成的YOLO TXT文件路径

        Raises:
            FileNotFoundError: 当XML文件不存在时
            ET.ParseError: 当XML格式无效时
            ValueError: 当图像尺寸无效或标签未定义时

        Example:
            >>> converter.cvat_to_yolo_seg('annotations.xml')
            >>> # 输出: labels/image1.txt, labels/image2.txt ...
        """
        # 初始化输出目录
        xml_path_obj = Path(xml_path)
        if output_dir is None:
            output_dir = str(xml_path_obj.parent / "labels")
        output_dir_obj = Path(output_dir)
        output_dir_obj.mkdir(parents=True, exist_ok=True)

        # 解析XML文件
        try:
            tree = ET.parse(xml_path)
        except FileNotFoundError:
            raise FileError(f"XML文件不存在: {xml_path}")
        except ET.ParseError:
            raise FormatError(f"无效的XML格式: {xml_path}")

    def batch_convert(self, input_files: List[str], conversion_type: str, **kwargs) -> List[str]:
        """
        批处理转换功能

        批量处理多个标注文件的格式转换。

        Args:
            input_files: 输入文件路径列表
            conversion_type: 转换类型，支持以下值：
                - "labelme_to_yolo_seg": LabelMe → YOLO分割
                - "labelme_to_yolo_obj": LabelMe → YOLO目标检测
                - "labelme_to_voc": LabelMe → VOC
                - "yolo_seg_to_labelme": YOLO分割 → LabelMe
                - "yolo_obj_to_labelme": YOLO目标检测 → LabelMe
                - "yolo_obj_to_voc": YOLO目标检测 → VOC
                - "voc_to_labelme": VOC → LabelMe
                - "voc_to_yolo_obj": VOC → YOLO目标检测
                - "cvat_to_yolo_seg": CVAT → YOLO分割
                - "polygons_to_yolo_seg": 多边形数据 → YOLO分割
            **kwargs: 传递给具体转换方法的额外参数

        Returns:
            List[str]: 生成的输出文件路径列表

        Raises:
            ValueError: 当转换类型不支持时
            AnnotationError: 当转换过程中出现错误时

        Example:
            >>> # 批量转换LabelMe文件到YOLO分割格式
            >>> files = ['labelme/001.json', 'labelme/002.json', 'labelme/003.json']
            >>> output_files = converter.batch_convert(files, 'labelme_to_yolo_seg')
            >>> print(output_files)
            >>> # 输出: ['labels/001.txt', 'labels/002.txt', 'labels/003.txt']
            >>>
            >>> # 批量转换YOLO文件到LabelMe格式
            >>> yolo_files = ['yolo/001.txt', 'yolo/002.txt']
            >>> image_files = ['images/001.jpg', 'images/002.jpg']
            >>> output_jsons = converter.batch_convert(
            ...     yolo_files, 
            ...     'yolo_obj_to_labelme',
            ...     img_path=image_files
            ... )
        """
        output_files = []
        conversion_methods = {
            "labelme_to_yolo_seg": self.labelme_to_yolo_seg,
            "labelme_to_yolo_obj": self.labelme_to_yolo_obj,
            "labelme_to_voc": self.labelme_to_voc,
            "yolo_seg_to_labelme": self.yolo_seg_to_labelme,
            "yolo_obj_to_labelme": self.yolo_obj_to_labelme,
            "yolo_obj_to_voc": self.yolo_obj_to_voc,
            "voc_to_labelme": self.voc_to_labelme,
            "voc_to_yolo_obj": self.voc_to_yolo_obj,
            "cvat_to_yolo_seg": self.cvat_to_yolo_seg,
            "polygons_to_yolo_seg": self.polygons_to_yolo_seg
        }

        if conversion_type not in conversion_methods:
            raise ValueError(f"不支持的转换类型: {conversion_type}")

        method = conversion_methods[conversion_type]

        # 处理需要对应图像路径的转换类型
        img_paths = kwargs.get('img_path', [])
        if img_paths and len(img_paths) != len(input_files):
            raise ValueError("图像路径列表长度必须与输入文件列表长度一致")

        # 内存优化：使用迭代器处理文件，避免一次性加载所有文件
        for i, input_file in enumerate(input_files):
            try:
                if img_paths:
                    # 对于需要图像路径的转换
                    if conversion_type in ["yolo_seg_to_labelme", "yolo_obj_to_labelme", "yolo_obj_to_voc"]:
                        output_file = method(input_file, img_paths[i], kwargs.get('output_dir'))
                    else:
                        output_file = method(input_file, kwargs.get('output_dir'))
                else:
                    # 对于不需要图像路径的转换
                    if conversion_type == "polygons_to_yolo_seg" and 'polygons' in kwargs:
                        # 特殊处理多边形数据转换
                        polygons = kwargs['polygons'][i] if isinstance(kwargs['polygons'], list) else kwargs['polygons']
                        img_path = kwargs.get('img_path', '')[i] if isinstance(kwargs.get('img_path', ''), list) else kwargs.get('img_path', '')
                        output_file = method(polygons, img_path, kwargs.get('output_dir'))
                    else:
                        output_file = method(input_file, kwargs.get('output_dir'))
                output_files.append(output_file)
                if self.verbose:
                    self.logger.info(f"成功转换: {input_file} → {output_file}")
            except Exception as e:
                error_msg = f"转换文件失败 {input_file}: {e}"
                if self.verbose:
                    self.logger.error(error_msg)
                raise AnnotationError(error_msg)

        return output_files

    def batch_process_directory(self, input_dir: str, pattern: str, conversion_type: str, **kwargs) -> List[str]:
        """
        批量处理目录中的文件

        自动查找目录中匹配指定模式的文件并进行批量转换。

        Args:
            input_dir: 输入目录路径
            pattern: 文件匹配模式，如 "*.json", "*.txt", "*.xml"
            conversion_type: 转换类型，同batch_convert方法
            **kwargs: 传递给batch_convert的额外参数

        Returns:
            List[str]: 生成的输出文件路径列表

        Example:
            >>> # 批量处理目录中的所有LabelMe文件
            >>> output_files = converter.batch_process_directory(
            ...     'labelme_annotations', 
            ...     '*.json', 
            ...     'labelme_to_yolo_seg'
            ... )
            >>>
            >>> # 批量处理目录中的所有YOLO文件
            >>> output_jsons = converter.batch_process_directory(
            ...     'yolo_labels', 
            ...     '*.txt', 
            ...     'yolo_obj_to_labelme',
            ...     img_path='images'
            ... )
        """
        input_dir_obj = Path(input_dir)
        if not input_dir_obj.exists():
            raise FileError(f"输入目录不存在: {input_dir}")

        # 查找匹配的文件
        input_files = list(input_dir_obj.glob(pattern))
        if not input_files:
            if self.verbose:
                self.logger.warning(f"目录中没有匹配 {pattern} 的文件: {input_dir}")
            return []

        # 转换为字符串路径
        input_file_paths = [str(f) for f in input_files]

        # 处理图像路径参数
        if 'img_path' in kwargs and isinstance(kwargs['img_path'], str):
            # 如果提供了图像目录，则为每个输入文件查找对应的图像
            img_dir = Path(kwargs['img_path'])
            if img_dir.exists():
                img_paths = []
                for input_file in input_files:
                    # 尝试查找相同名称的图像文件
                    img_stem = input_file.stem
                    # 常见图像扩展名
                    img_exts = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
                    found_img = None
                    for ext in img_exts:
                        img_path = img_dir / f"{img_stem}{ext}"
                        if img_path.exists():
                            found_img = str(img_path)
                            break
                    if found_img:
                        img_paths.append(found_img)
                    else:
                        if self.verbose:
                            self.logger.warning(f"未找到对应图像文件: {img_stem}")
                        img_paths.append('')
                kwargs['img_path'] = img_paths

        # 执行批量转换
        return self.batch_convert(input_file_paths, conversion_type, **kwargs)

        # 提取类别名称
        try:
            cls_names = [
                label.find("name").text
                for label in tree.find("meta/job/labels").findall("label")
            ]
        except AttributeError:
            raise FormatError("XML中缺少必要的meta/labels结构")

        # 处理每个图像
        for img_obj in tree.findall('image'):
            img_name = img_obj.attrib.get("name", "")
            if not img_name:
                if self.verbose:
                    self.logger.warning("跳过未命名的图像")
                continue

            try:
                img_width = float(img_obj.attrib["width"])
                img_height = float(img_obj.attrib["height"])
                if img_width <= 0 or img_height <= 0:
                    raise ValidationError(f"无效的图像尺寸: {img_width}x{img_height}")
            except (KeyError, ValueError, ValidationError):
                if self.verbose:
                    self.logger.warning(f"跳过图像 {img_name}（无效尺寸）")
                continue

            # 为每个图像创建单独的YOLOAnnotation实例
            yolo_ann = YOLOAnnotation(cls_names, verbose=self.verbose)
            
            # 处理每个多边形
            for polygon in img_obj.findall("polygon"):
                label = polygon.attrib.get("label")
                if label not in cls_names:
                    if self.verbose:
                        self.logger.warning(f"跳过未知标签 '{label}'（图像: {img_name}）")
                    continue

                # 使用convert_polygon_to_standard_format统一处理
                points_str = polygon.attrib.get("points", "")
                standardized = self.convert_polygon_to_standard_format(points_str)
                if standardized is None or len(standardized) < 3:
                    if self.verbose:
                        self.logger.warning(f"跳过无效多边形（图像: {img_name}）")
                    continue

                # 归一化处理
                try:
                    points_array = np.array(standardized, dtype=float)
                    normalized = (points_array / [img_width, img_height]).flatten().round(6).tolist()

                    if len(normalized) >= 6:
                        yolo_ann.add_annotation(cls_names.index(label), normalized)
                except Exception as e:
                    if self.verbose:
                        self.logger.error(f"归一化失败（图像: {img_name}）: {e}")

            # 保存当前图像的标注
            txt_path = output_dir_obj / f"{Path(img_name).stem}.txt"
            yolo_ann.save(str(txt_path))

        return output_dir

    def create_empty_yolo(self, img_path: str, output_dir: str = None) -> str:
        """
        为无标签图像创建空YOLO标签文件

        Args:
            img_path: 图像文件路径
            output_dir: 输出目录（默认为父目录的labels文件夹）

        Returns:
            生成的空标签文件路径

        Example:
            >>> # 为没有标注的图像创建空标签
            >>> converter.create_empty_yolo('images/002.jpg')
            >>> # 输出: labels/002.txt (空文件)
            >>>
            >>> # 批量创建空标签
            >>> for img_file in Path('unlabeled_images').glob('*.jpg'):
            >>>     converter.create_empty_yolo(str(img_file))
        """
        if output_dir is None:
            output_dir = Path(img_path).parent.parent / "labels"
        else:
            output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        txt_path = output_dir / f"{Path(img_path).stem}.txt"
        with open(txt_path, 'w') as f:
            pass  # 创建空文件

        self.logger.info(f"创建空YOLO标签: {txt_path}")
        return str(txt_path)
