import json
import os
import cv2
from pathlib import Path
from typing import List, Dict, Tuple
from ..utils.basic import set_logging


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

    def __init__(self, class_names: List[str], verbose=False):
        """
        初始化YOLO标注器

        Args:
            class_names: 类别名称列表，列表索引将作为class_id使用
                        例如：['person', 'car'] 表示 class_id 0=person, 1=car
        """
        self.class_names = class_names
        self.logger = set_logging("YOLOAnnotation", verbose=verbose)
        self.annotations = []

    def add_annotation(self, class_id: int, normalized_points: List[float]):
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

    def to_txt_lines(self):
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
        lines = []
        for class_id, normalized_points in self.annotations:
            lines.append(f"{class_id} " + " ".join(map(str, normalized_points)))
        return lines

    def save(self, txt_path):
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

    Attributes:
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

    def __init__(self, image_path: str, image_size: tuple, shapes: List[Dict] = None, verbose=False):
        """
        初始化LabelMe标注器

        Args:
            image_path: 图像文件路径（用于获取文件名）
            image_size: 图像尺寸元组 (height, width)
            shapes: 预定义的形状列表（可选）
        """
        self.version = "5.1.1"
        self.flags = {}
        self.shapes = shapes if shapes else []
        self.imagePath = str(Path(image_path).name)
        self.imageData = None
        self.imageHeight, self.imageWidth = image_size
        self.logger = set_logging("LabelMeAnnotation", verbose=verbose)

    def add_shape(self, label: str, points: List[List[float]], shape_type: str = "polygon"):
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

    def to_dict(self) -> Dict:
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

    def save(self, json_path: str):
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

    Attributes:
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
        self.name = name
        self.bbox = bbox  # [xmin, ymin, xmax, ymax]
        self.difficult = difficult

    def to_xml(self) -> str:
        """
        生成VOC格式的XML object节点

        Returns:
            str: 符合VOC XML格式的object节点字符串

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
        xmin, ymin, xmax, ymax = self.bbox
        return f"""
                <object>
                    <name>{self.name}</name>
                    <pose>Unspecified</pose>
                    <truncated>0</truncated>
                    <difficult>{self.difficult}</difficult>
                    <bndbox>
                        <xmin>{xmin}</xmin>
                        <ymin>{ymin}</ymin>
                        <xmax>{xmax}</xmax>
                        <ymax>{ymax}</ymax>
                    </bndbox>
                </object>"""


class VOCAnnotation:
    """
    VOC格式标注文件处理类

    用于创建、管理和保存Pascal VOC格式的XML标注文件。
    支持目标检测任务的标准VOC格式，包含图像信息和多个对象标注。

    Attributes:
        image_path (str): 图像文件路径（绝对或相对路径）
        image_width (int): 图像宽度（像素）
        image_height (int): 图像高度（像素）
        objects (List[VOCObject]): VOC对象标注列表

    Example:
        >>> # 初始化标注器，指定图像路径和尺寸
        >>> annotator = VOCAnnotation("images/001.jpg", (640, 480))
        >>>
        >>> # 添加多个对象标注
        >>> annotator.add_object("person", [100, 50, 200, 150])
        >>> annotator.add_object("car", [300, 200, 450, 300], difficult=1)
        >>>
        >>> # 保存为VOC XML文件
        >>> annotator.save("annotations/001.xml")
        >>>
        >>> # 批量添加对象
        >>> objects = [
        >>>     VOCObject("dog", [150, 100, 250, 200]),
        >>>     VOCObject("cat", [400, 100, 500, 200])
        >>> ]
        >>> batch_annotator = VOCAnnotation("images/002.jpg", (640, 480), objects)
        >>> batch_annotator.save("annotations/002.xml")
    """

    def __init__(self, image_path: str, image_size: Tuple[int, int], objects: List[VOCObject] = None, verbose=False):
        """
        初始化VOC标注器

        Args:
            image_path: 图像文件路径
            image_size: 图像尺寸元组 (width, height)
            objects: 预定义的VOCObject列表（可选）
        """
        self.image_path = image_path
        self.image_width, self.image_height = image_size
        self.objects = objects if objects else []
        self.logger = set_logging("VOCAnnotation", verbose=verbose)

    def add_object(self, name: str, bbox: List[float], difficult: int = 0):
        """
        添加一个VOC格式的对象标注

        Args:
            name: 对象类别名称（如"person", "car"）
            bbox: 边界框坐标 [xmin, ymin, xmax, ymax]
            difficult: 难度标志（0=容易，1=困难）

        Example:
            >>> # 添加普通对象
            >>> annotator.add_object("person", [100, 50, 200, 150])
            >>>
            >>> # 添加困难样本
            >>> annotator.add_object("car", [300, 200, 450, 300], difficult=1)
            >>>
            >>> # 添加部分可见对象
            >>> annotator.add_object("dog", [150, 100, 250, 200], difficult=0)
        """
        self.objects.append(VOCObject(name, bbox, difficult))

    def save(self, xml_path: str):
        """
        保存为VOC格式的XML文件

        Args:
            xml_path: 输出的XML文件路径

        Raises:
            IOError: 当文件写入失败时
            PermissionError: 当没有文件写入权限时

        Example:
            >>> annotator.save("path/to/annotations/001.xml")
            >>> # 生成的文件结构:
            >>> # <annotation>
            >>> #     <folder>images</folder>
            >>> #     <filename>001.jpg</filename>
            >>> #     <size>
            >>> #         <width>640</width>
            >>> #         <height>480</height>
            >>> #         <depth>3</depth>
            >>> #     </size>
            >>> #     <object>...</object>
            >>> # </annotation>
        """
        xml_content = f"""<annotation>
            <folder>{Path(self.image_path).parent.name}</folder>
            <filename>{Path(self.image_path).name}</filename>
            <path>{self.image_path}</path>
            <source>
                <database>Unknown</database>
            </source>
            <size>
                <width>{self.image_width}</width>
                <height>{self.image_height}</height>
                <depth>3</depth>
            </size>
            <segmented>0</segmented>
        """
        for obj in self.objects:
            xml_content += obj.to_xml()

        xml_content += "\n</annotation>"

        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        self.logger.info(f"VOC XML 保存成功: {xml_path}")


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

    Attributes:
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

    def _get_image_size(self, image_path: str) -> tuple:
        """
        获取图像尺寸

        Args:
            image_path: 图像文件路径

        Returns:
            图像尺寸元组 (height, width)
        """
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"无法读取图像: {image_path}")
        return img.shape[:2]  # (height, width)

    def labelme_to_yolo_seg(self, json_path: str, output_dir: str = None) -> str:
        """
        LabelMe分割标注 → YOLO分割格式

        将LabelMe的多边形分割标注转换为YOLO分割格式。

        Args:
            json_path: LabelMe JSON文件路径
            output_dir: 输出目录（默认为父目录的labels文件夹）

        Returns:
            生成的YOLO TXT文件路径

        Raises:
            ValueError: 当标签不在class_names中时

        Example:
            >>> converter.labelme_to_yolo_seg('labelme/001.json')
            >>> # 输出: labels/001.txt
            >>>
            >>> # 指定输出目录
            >>> converter.labelme_to_yolo_seg('001.json', 'yolo_labels')
        """
        if output_dir is None:
            output_dir = str(Path(json_path).parent.parent / "labels")
        os.makedirs(output_dir, exist_ok=True)

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        yolo_ann = YOLOAnnotation(self.class_names, verbose=self.verbose)
        img_width = data['imageWidth']
        img_height = data['imageHeight']

        for shape in data['shapes']:
            label = shape['label']
            if label not in self.class_names:
                raise ValueError(f"标签 '{label}' 不在 class_names 中")

            class_id = self.class_names.index(label)
            points = shape['points']
            if len(points) > 2:
                normalized_points = []

                for x, y in points:
                    nx = x / img_width
                    ny = y / img_height
                    normalized_points.extend([round(nx, 6), round(ny, 6)])

                yolo_ann.add_annotation(class_id, normalized_points)

        txt_path = os.path.join(output_dir, Path(json_path).stem + ".txt")
        yolo_ann.save(txt_path)
        return txt_path

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
        if output_dir is None:
            output_dir = str(Path(txt_path).parent.parent / "jsons")
        os.makedirs(output_dir, exist_ok=True)

        img_height, img_width = self._get_image_size(img_path)
        labelme_ann = LabelMeAnnotation(img_path, (img_height, img_width), verbose=self.verbose)

        with open(txt_path, 'r') as f:
            lines = f.readlines()

        for line in lines:
            parts = line.strip().split()
            class_id = int(parts[0])

            if class_id >= len(self.class_names):
                raise ValueError(f"类别 ID {class_id} 超出范围")

            points = []
            if len(parts) > 5:
                for i in range(1, len(parts), 2):
                    x = float(parts[i]) * img_width
                    y = float(parts[i + 1]) * img_height
                    points.append([round(x, 2), round(y, 2)])

                labelme_ann.add_shape(
                    label=self.class_names[class_id],
                    points=points,
                    shape_type="polygon"
                )

        json_path = os.path.join(output_dir, Path(txt_path).stem + ".json")
        labelme_ann.save(json_path)
        return json_path

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
        if output_dir is None:
            output_dir = str(Path(json_path).parent.parent / "labels")
        os.makedirs(output_dir, exist_ok=True)

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        yolo_ann = YOLOAnnotation(self.class_names, verbose=self.verbose)
        img_width = data['imageWidth']
        img_height = data['imageHeight']

        for shape in data['shapes']:
            label = shape['label']
            if label not in self.class_names:
                raise ValueError(f"标签 '{label}' 不在 class_names 中")

            class_id = self.class_names.index(label)
            points = shape['points']

            # 计算边界框
            x_coords = [p[0] for p in points]
            y_coords = [p[1] for p in points]
            x_min, x_max = min(x_coords), max(x_coords)
            y_min, y_max = min(y_coords), max(y_coords)

            # 转换为YOLO格式
            cx = (x_min + x_max) / 2 / img_width
            cy = (y_min + y_max) / 2 / img_height
            w = (x_max - x_min) / img_width
            h = (y_max - y_min) / img_height

            yolo_ann.add_annotation(class_id, [round(cx, 6), round(cy, 6), round(w, 6), round(h, 6)])

        txt_path = os.path.join(output_dir, Path(json_path).stem + ".txt")
        yolo_ann.save(txt_path)
        return txt_path

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
        if output_dir is None:
            output_dir = str(Path(txt_path).parent.parent / "jsons")
        os.makedirs(output_dir, exist_ok=True)

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
                raise ValueError(f"类别 ID {class_id} 超出范围")

            cx, cy, w, h = map(float, parts[1:])

            # 转换为矩形坐标
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

        json_path = os.path.join(output_dir, Path(txt_path).stem + ".json")
        labelme_ann.save(json_path)
        return json_path

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
        if output_dir is None:
            output_dir = str(Path(json_path).parent.parent / "voc")
        os.makedirs(output_dir, exist_ok=True)

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        voc_ann = VOCAnnotation(
            image_path=data['imagePath'],
            image_size=(data['imageWidth'], data['imageHeight']),
            verbose=self.verbose
        )

        for shape in data['shapes']:
            label = shape['label']
            if label not in self.class_names:
                raise ValueError(f"标签 '{label}' 不在 class_names 中")

            points = shape['points']
            x_coords = [p[0] for p in points]
            y_coords = [p[1] for p in points]

            voc_ann.add_object(
                name=label,
                bbox=[min(x_coords), min(y_coords), max(x_coords), max(y_coords)]
            )

        xml_path = os.path.join(output_dir, Path(json_path).stem + ".xml")
        voc_ann.save(xml_path)
        return xml_path

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
        if output_dir is None:
            output_dir = str(Path(xml_path).parent.parent / "jsons")
        os.makedirs(output_dir, exist_ok=True)

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
            if label not in self.class_names:
                raise ValueError(f"标签 '{label}' 不在 class_names 中")

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

        json_path = os.path.join(output_dir, Path(xml_path).stem + ".json")
        labelme_ann.save(json_path)
        return json_path

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
        if output_dir is None:
            output_dir = str(Path(txt_path).parent.parent / "voc")
        os.makedirs(output_dir, exist_ok=True)

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
                raise ValueError(f"类别 ID {class_id} 超出范围")

            cx, cy, w, h = map(float, parts[1:])

            # 转换为矩形坐标
            x_min = round((cx - w / 2) * img_width, 6)
            y_min = round((cy - h / 2) * img_height, 6)
            x_max = round((cx + w / 2) * img_width, 6)
            y_max = round((cy + h / 2) * img_height, 6)

            voc_ann.add_object(
                name=self.class_names[class_id],
                bbox=[x_min, y_min, x_max, y_max]
            )

        xml_path = os.path.join(output_dir, Path(txt_path).stem + ".xml")
        voc_ann.save(xml_path)
        return xml_path

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
        if output_dir is None:
            output_dir = str(Path(xml_path).parent.parent / "labels")
        os.makedirs(output_dir, exist_ok=True)

        import xml.etree.ElementTree as ET
        tree = ET.parse(xml_path)
        root = tree.getroot()

        img_path = root.find('path').text
        size = root.find('size')
        img_width = int(size.find('width').text)
        img_height = int(size.find('height').text)

        yolo_ann = YOLOAnnotation(self.class_names, verbose=self.verbose)

        for obj in root.findall('object'):
            label = obj.find('name').text
            if label not in self.class_names:
                raise ValueError(f"标签 '{label}' 不在 class_names 中")

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

        txt_path = os.path.join(output_dir, Path(xml_path).stem + ".txt")
        yolo_ann.save(txt_path)
        return txt_path

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
            output_dir = str(Path(img_path).parent.parent / "labels")
        os.makedirs(output_dir, exist_ok=True)

        txt_path = os.path.join(output_dir, Path(img_path).stem + ".txt")
        with open(txt_path, 'w') as f:
            pass  # 创建空文件

        self.logger.info(f"创建空YOLO标签: {txt_path}")
        return txt_path
