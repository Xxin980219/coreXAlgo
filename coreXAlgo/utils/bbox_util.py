import json
import os
try:
    from typing import Dict, Tuple, Union, Optional, List, Literal, TYPE_CHECKING
except ImportError:
    from typing import Dict, Tuple, Union, Optional, List
    from typing_extensions import Literal
    from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np


def polygon_to_bbox(polygon):
    """
    Convert a polygon to a bounding box [left, top, right, bottom].

    Args:
        polygon: A list or array of coordinates in format [x1,y1, x2,y2, ...].
                 If length is odd, the last value is ignored.

    Returns:
        List[float]: [left, top, right, bottom]

    Example:
        >>> # 创建一个四边形坐标
        >>> polygon = [10, 10, 50, 10, 50, 50, 10, 50]
        >>> bbox = polygon_to_bbox(polygon)
        >>> print(bbox)  # 输出: [10, 10, 50, 50]
    """
    import numpy as np
    if len(polygon) < 4:
        raise ValueError("Polygon must have at least 2 points (4 coordinates)")

    # Ensure even length (ignore last element if odd)
    coords = np.asarray(polygon[:len(polygon) // 2 * 2], dtype=np.float32)
    points = coords.reshape(-1, 2)  # Reshape to [N, 2]

    l, t = np.min(points, axis=0)
    r, b = np.max(points, axis=0)
    return [l, t, r, b]


def cnt_to_polygon(cnt):
    """
    Convert contour to simplified polygon coordinates.

    Args:
        cnt: Input contour as numpy array with shape (N,2)

    Returns:
        List of polygon coordinates [x1,y1,x2,y2,...] or empty list if conversion fails

    Example:
        >>> # 创建一个简单的三角形轮廓
        >>> contour = np.array([[10, 10], [50, 10], [30, 50]])
        >>> polygon = cnt_to_polygon(contour)
        >>> print(polygon)  # 输出简化的多边形坐标
        [10.0, 10.0, 50.0, 10.0, 30.0, 50.0, 10.0, 10.0]
    """
    import numpy as np
    from shapely import geometry
    from shapely.geometry import Polygon, MultiPolygon
    if not isinstance(cnt, (np.ndarray, list)) or len(cnt) < 3:
        return []

    try:
        # Convert contour to Shapely Polygon with small buffer for cleaning
        poly = Polygon(np.asarray(cnt).reshape(-1, 2)).buffer(1)
    except (ValueError, AttributeError):
        return []

        # Handle different geometry types
    if isinstance(poly, geometry.Polygon):
        poly = MultiPolygon([poly])
    elif isinstance(poly, (geometry.LineString, geometry.MultiLineString,
                           geometry.Point, geometry.MultiPoint,
                           geometry.GeometryCollection)):
        return []  # Ignore non-polygon geometries

        # Find largest polygon if multipolygon
    if isinstance(poly, MultiPolygon):
        max_poly = max(poly.geoms, key=lambda p: p.area, default=None)
        if max_poly is None:
            return []
    else:
        max_poly = poly

        # Flatten coordinates [x1,y1,x2,y2,...]
    return [coord for xy in max_poly.exterior.coords for coord in xy]


def mask_to_polygon(mask: 'np.ndarray'):
    """
    Convert binary mask to polygon coordinates.

    Args:
        mask (np.ndarray): Binary mask of shape (H,W) where 1 indicates object

    Returns:
        List[float] or None: Polygon coordinates [x1,y1,x2,y2,...] or None if no contour found

    Example:
        >>> # 创建一个简单的二值掩码
        >>> mask = np.zeros((100, 100), dtype=np.uint8)
        >>> mask[20:80, 20:80] = 1  # 创建一个方形区域
        >>> # 转换为多边形
        >>> polygon = mask_to_polygon(mask)
        >>> print(f"多边形坐标长度: {len(polygon)}")
        >>> # 可以用于绘制或进一步处理
    """
    import numpy as np
    import cv2
    if not isinstance(mask, np.ndarray) or mask.ndim != 2:
        return None
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None
    # Get largest contour by area
    largest_cnt = max(contours, key=cv2.contourArea)
    return cnt_to_polygon(largest_cnt)


def mask_to_polygons(mask, area_threshold=25):
    """
    Convert binary mask to multiple polygon coordinates.

    Args:
        mask: Binary mask of shape (H,W) where 1 indicates object
        area_threshold: Minimum area threshold for including a polygon

    Returns:
        List of polygon coordinates [[x1,y1,x2,y2,...], ...] or None if no valid contours found

    Example:
        >>> # 创建包含多个区域的掩码
        >>> mask = np.zeros((100, 100), dtype=np.uint8)
        >>> mask[10:30, 10:30] = 1  # 第一个区域
        >>> mask[60:80, 60:80] = 1  # 第二个区域
        >>> # 转换为多个多边形（过滤小面积区域）
        >>> polygons = mask_to_polygons(mask, area_threshold=50)
        >>> print(f"找到 {len(polygons)} 个多边形")
        >>> # 可以用于批量绘制或分析
    """
    import numpy as np
    import cv2
    if not isinstance(mask, np.ndarray) or mask.ndim != 2:
        return None

    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None

    polygons = []
    for cnt in contours:
        if cv2.contourArea(cnt) > area_threshold:
            poly = cnt_to_polygon(cnt)
            if poly:  # Traditional if statement for Python 3.7+
                polygons.append(poly)

    return polygons if polygons else None


def merge_boxes_by_expansion(detections, threshold=20):
    """
    合并重叠和相邻的矩形框（将多个框合并成一个更大的框）
    基于扩展分组的合并算法

    Args:
        detections: 检测框列表，每个元素格式为 [置信度, 左边界, 上边界, 右边界, 下边界]
        threshold: 合并阈值（像素）

    Returns:
        合并后的矩形框列表
    """
    import numpy as np
    if not detections:
        return []

    boxes_array = np.array([box[1:] for box in detections])  # 坐标
    scores = np.array([box[0] for box in detections])  # 置信度

    # 扩展框，使相邻的框变成重叠框
    boxes_expanded = boxes_array.copy()
    boxes_expanded[:, 0] -= threshold / 2  # 左边界向左扩展
    boxes_expanded[:, 1] -= threshold / 2  # 上边界向上扩展
    boxes_expanded[:, 2] += threshold / 2  # 右边界向右扩展
    boxes_expanded[:, 3] += threshold / 2  # 下边界向下扩展

    merged = []
    used = [False] * len(detections)

    for i in range(len(detections)):
        if used[i]:
            continue

        # 初始化当前合并组
        current_group = [i]
        used[i] = True

        # 查找所有与当前框重叠的框
        changed = True
        while changed:
            changed = False
            for j in range(len(detections)):
                if used[j]:
                    continue

                # 检查是否与当前组中的任何框重叠
                overlap_with_group = False
                for k in current_group:
                    # 计算两个扩展框的IoU
                    box1 = boxes_expanded[k]
                    box2 = boxes_expanded[j]

                    # 计算重叠区域
                    xx1 = max(box1[0], box2[0])
                    yy1 = max(box1[1], box2[1])
                    xx2 = min(box1[2], box2[2])
                    yy2 = min(box1[3], box2[3])

                    w = max(0, xx2 - xx1)
                    h = max(0, yy2 - yy1)

                    if w > 0 and h > 0:  # 有重叠
                        overlap_with_group = True
                        break

                if overlap_with_group:
                    current_group.append(j)
                    used[j] = True
                    changed = True

        # 合并当前组中的所有框
        if current_group:
            # 取所有框的最小外接矩形
            group_boxes = boxes_array[current_group]
            x1 = np.min(group_boxes[:, 0])
            y1 = np.min(group_boxes[:, 1])
            x2 = np.max(group_boxes[:, 2])
            y2 = np.max(group_boxes[:, 3])

            # 取组中最大置信度
            group_scores = scores[current_group]
            max_score = np.max(group_scores)

            merged.append([float(max_score), int(x1), int(y1), int(x2), int(y2)])

    return merged


def merge_boxes_by_conditions(detections, merge_threshold=50, touching_threshold=5):
    """
    合并重叠、相邻、包含以及边相切（紧贴但不相交）的框（迭代合并算法）
    基于多条件迭代的合并算法

    这个函数用于合并重叠或邻近的检测框，特别适用于密集小目标的检测场景。
    与标准NMS（非极大值抑制）不同，此算法不仅合并重叠框，还会合并邻近框、包含关系的框和边相切的框。

    Args:
        detections: 检测框列表，每个元素格式为 [置信度, 左边界, 上边界, 右边界, 下边界]
                    例如: [[0.9, 10, 10, 50, 50], [0.8, 30, 30, 70, 70]]
        merge_threshold: 合并阈值（像素），默认50。当两个框边缘距离小于此值时，即使不重叠也会合并。
        touching_threshold: 边相切判定阈值（像素），默认5。当两个框边缘紧贴但不相交时，允许的微小间隙。

    Returns:
        list: 合并后的检测框列表，格式同输入。
              例如: [[0.9, 10, 10, 70, 70]]

    Notes:
        1. 算法会优先处理置信度高的框
        2. 合并时取并集区域作为新框
        3. 合并后的置信度取原框中最大值
        4. 通过迭代确保所有可合并的框都被合并
    """
    import numpy as np
    if not detections:
        return []

    detections = sorted(detections, key=lambda x: -x[0])
    merged_boxes = []

    def should_merge(box1, box2):
        """
        判断两个框是否应该合并

        参数:
            box1: 第一个框，格式 [置信度, 左, 上, 右, 下]
            box2: 第二个框，格式同上

        返回:
            bool: 如果应该合并返回True，否则返回False

        合并判断逻辑（满足以下任一条件即合并）:
        1. 两个框有重叠区域
        2. 两个框边缘距离小于merge_threshold（邻近框）
        3. 一个框完全包含另一个框
        4. 一个框完全在另一个框内
        5. 两个框边相切（紧贴但有微小间隙，间隙小于touching_threshold）
        """
        l1, t1, r1, b1 = box1[1:]
        l2, t2, r2, b2 = box2[1:]

        # 1. 检查包含关系
        contained = (l1 >= l2 and r1 <= r2 and t1 >= t2 and b1 <= b2)
        containing = (l1 <= l2 and r1 >= r2 and t1 <= t2 and b1 >= b2)

        if contained or containing:
            return True

        # 2. 计算重叠区域
        inter_w = min(r1, r2) - max(l1, l2)
        inter_h = min(b1, b2) - max(t1, t2)

        # 如果有重叠，直接返回True
        if inter_w > 0 and inter_h > 0:
            return True

        # 3. 计算X轴和Y轴方向的最小边缘距离
        # 水平方向最小距离
        horizontal_dist = max(0, max(l1, l2) - min(r1, r2))
        # 垂直方向最小距离
        vertical_dist = max(0, max(t1, t2) - min(b1, b2))

        # 4. 计算两个框中心点的距离（可选，用于更宽松的合并条件）
        center1_x, center1_y = (l1 + r1) / 2, (t1 + b1) / 2
        center2_x, center2_y = (l2 + r2) / 2, (t2 + b2) / 2
        center_dist = np.sqrt((center1_x - center2_x) ** 2 + (center1_y - center2_y) ** 2)

        # 5. 判断是否是边相切的情况
        # 水平方向：一个框的右边与另一个框的左边紧贴
        horizontal_touching = (abs(r1 - l2) <= touching_threshold or
                               abs(r2 - l1) <= touching_threshold)

        # 垂直方向：一个框的下边与另一个框的上边紧贴
        vertical_touching = (abs(b1 - t2) <= touching_threshold or
                             abs(b2 - t1) <= touching_threshold)

        # 对角相切：一个角与另一个角紧贴
        corner_touching = ((abs(r1 - l2) <= touching_threshold and abs(b1 - t2) <= touching_threshold) or
                           (abs(r2 - l1) <= touching_threshold and abs(b2 - t1) <= touching_threshold) or
                           (abs(r1 - l2) <= touching_threshold and abs(t1 - b2) <= touching_threshold) or
                           (abs(r2 - l1) <= touching_threshold and abs(t2 - b1) <= touching_threshold))

        # 6. 综合判断条件
        # 条件1：有重叠（已处理）
        # 条件2：边缘距离小于阈值
        edge_close = (horizontal_dist < merge_threshold and vertical_dist < merge_threshold)

        # 条件3：边相切
        touching = (horizontal_touching or vertical_touching or corner_touching)

        # 可选：如果两个框在同一个水平/垂直线附近，并且距离很近
        same_line_horizontal = (abs(t1 - t2) <= merge_threshold / 2 and abs(b1 - b2) <= merge_threshold / 2)
        same_line_vertical = (abs(l1 - l2) <= merge_threshold / 2 and abs(r1 - r2) <= merge_threshold / 2)

        # 如果中心点距离较近，也考虑合并
        center_close = center_dist < max(merge_threshold, touching_threshold * 2)

        return edge_close or touching or (center_close and (same_line_horizontal or same_line_vertical))

    # 初始合并
    for current in detections:
        conf, *curr_box = current
        is_merged = False

        for i, (m_conf, *m_box) in enumerate(merged_boxes):
            if should_merge((conf, *curr_box), (m_conf, *m_box)):
                # 合并策略：取并集
                merged_boxes[i] = [
                    max(conf, m_conf),
                    min(curr_box[0], m_box[0]),
                    min(curr_box[1], m_box[1]),
                    max(curr_box[2], m_box[2]),
                    max(curr_box[3], m_box[3])
                ]
                is_merged = True
                break

        if not is_merged:
            merged_boxes.append(current)

    # 迭代合并：检查已合并的框之间是否还能合并
    changed = True
    while changed and len(merged_boxes) > 1:
        changed = False
        i = 0

        while i < len(merged_boxes):
            j = i + 1
            while j < len(merged_boxes):
                if should_merge(merged_boxes[i], merged_boxes[j]):
                    merged_boxes[i] = [
                        max(merged_boxes[i][0], merged_boxes[j][0]),
                        min(merged_boxes[i][1], merged_boxes[j][1]),
                        min(merged_boxes[i][2], merged_boxes[j][2]),
                        max(merged_boxes[i][3], merged_boxes[j][3]),
                        max(merged_boxes[i][4], merged_boxes[j][4])
                    ]
                    merged_boxes.pop(j)
                    changed = True
                else:
                    j += 1
            i += 1

    return merged_boxes


def merge_adjacent_boxes(detections, vertical_threshold=20, horizontal_threshold=20):
    """
    合并相邻的矩形框（针对YOLO检测结果，已通过NMS处理，框之间不重叠）

    Args:
        detections: 检测框列表，格式为 [置信度, 左边界, 上边界, 右边界, 下边界]
        vertical_threshold: 垂直方向合并阈值（像素），上下框间距小于此值则合并
        horizontal_threshold: 水平方向合并阈值（像素），左右框间距小于此值则合并

    Returns:
        合并后的矩形框列表
    """
    if not detections:
        return []

    # 转换为numpy数组
    boxes_array = np.array([box[1:] for box in detections], dtype=np.float32)  # 坐标
    scores = np.array([box[0] for box in detections], dtype=np.float32)  # 置信度

    n = len(detections)
    used = [False] * n
    merged = []

    for i in range(n):
        if used[i]:
            continue

        # 当前框
        current_box = boxes_array[i]

        # 初始化合并组
        group_indices = [i]
        used[i] = True
        y_min = current_box[1]
        y_max = current_box[3]
        x_min = current_box[0]
        x_max = current_box[2]
        max_score = scores[i]

        # 查找相邻框
        changed = True
        while changed:
            changed = False
            for j in range(n):
                if used[j]:
                    continue

                other_box = boxes_array[j]

                # 计算框之间的相对位置
                # 水平方向：检查重叠和距离
                x_overlap = min(x_max, other_box[2]) - max(x_min, other_box[0])
                y_overlap = min(y_max, other_box[3]) - max(y_min, other_box[1])

                # 计算最小距离（考虑相切情况）
                horizontal_distance = 0
                vertical_distance = 0

                if x_overlap > 0:  # 水平有重叠
                    horizontal_distance = 0
                elif other_box[2] < x_min:  # 其他框在左侧
                    horizontal_distance = x_min - other_box[2]
                else:  # 其他框在右侧
                    horizontal_distance = other_box[0] - x_max

                if y_overlap > 0:  # 垂直有重叠
                    vertical_distance = 0
                elif other_box[3] < y_min:  # 其他框在上方
                    vertical_distance = y_min - other_box[3]
                else:  # 其他框在下方
                    vertical_distance = other_box[1] - y_max

                # 检查是否相邻
                is_adjacent = False

                # 垂直方向相邻：水平有重叠，垂直距离在阈值内（包含0）
                if x_overlap > 0:  # 水平有重叠
                    if 0 <= vertical_distance <= vertical_threshold:
                        is_adjacent = True

                # 水平方向相邻：垂直有重叠，水平距离在阈值内（包含0）
                if y_overlap > 0:  # 垂直有重叠
                    if 0 <= horizontal_distance <= horizontal_threshold:
                        is_adjacent = True

                if is_adjacent:
                    # 符合合并条件
                    group_indices.append(j)
                    used[j] = True

                    # 更新合并组的边界
                    y_min = min(y_min, other_box[1])
                    y_max = max(y_max, other_box[3])
                    x_min = min(x_min, other_box[0])
                    x_max = max(x_max, other_box[2])

                    # 更新当前框为合并后的边界，继续查找
                    current_box = np.array([x_min, y_min, x_max, y_max])
                    changed = True

                    # 更新最大置信度
                    max_score = max(max_score, scores[j])

        # 生成合并后的框
        merged_box = [
            float(max_score),
            int(x_min),
            int(y_min),
            int(x_max),
            int(y_max)
        ]
        merged.append(merged_box)

    return merged


class DetectionVisualizer:
    """
    目标检测可视化器 - 集成快速绘制和高质量渲染功能

    核心特性：
        - ✅ 双模式渲染：快速模式(OpenCV) 和 高质量模式(Matplotlib)
        - ✅ 智能颜色分配：为不同类别自动生成视觉区分度高的颜色
        - ✅ 智能标签位置：根据形状位置自动调整标签显示位置
        - ✅ 自适应参数：根据图像尺寸自动调整线宽、字体大小等参数
        - ✅ 输入验证：严格的格式检查和错误处理
        - ✅ 多形状支持：矩形框(rectangle)、线段(line)、多边形(polygon)

    使用示例：
    >>> visualizer = EnhancedVisualizer()
    >>> # 统一格式的结果数据
    >>> detections = [['person', 0.95, 50, 50, 150, 150], ['car', 0.87, 200, 100, 350, 200]]
    >>> # 新数据格式：
    >>> detections = [
    >>>     {'label': 'MB1U', 'shapeType': 'rectangle', 'points': [[5100, 2076], [5128, 2141]], 'result': {'confidence': 0.123}},
    >>>     {'label': 'line1', 'shapeType': 'line', 'points': [[100, 100], [200, 200]], 'result': {'confidence': 0.95}},
    >>>     {'label': 'poly1', 'shapeType': 'polygon', 'points': [[300, 300], [400, 300], [350, 400]], 'result': {'confidence': 0.87}}
    >>> ]
    >>> # 快速模式
    >>> result_fast = visualizer.draw_detection_results(image, detections, quality='fast')
    >>> # 高质量模式
    >>> result_hq = visualizer.draw_detection_results(image, detections, quality='high')
    """

    COLOR_PALETTE: Dict[str, Tuple[int, int, int]] = {}
    DEFAULT_FONT = None
    TEXT_COLOR = (255, 255, 255)
    LABEL_BG_ALPHA = 0.6
    SMALL_OBJ_AREA_THRESH = 1000
    # 标签位置优先级常量
    LABEL_POSITIONS = ['top', 'bottom', 'left', 'right', 'center']

    def __init__(self):
        """初始化可视化器"""
        pass

    @classmethod
    def _get_default_font(cls):
        """获取默认字体"""
        import cv2
        if cls.DEFAULT_FONT is None:
            cls.DEFAULT_FONT = cv2.FONT_HERSHEY_SIMPLEX
        return cls.DEFAULT_FONT

    @classmethod
    def visualize(
            cls,
            image: 'np.ndarray',
            detections: List[dict],
            output_path: Optional[str] = None,
            mode: Literal['fast', 'high'] = 'fast',
            **kwargs
    ) -> 'np.ndarray':
        """
        主可视化方法 - 支持新数据格式和多形状绘制

        参数:
            image: 输入图像 (H,W,C) 或灰度图 (H,W)
            detections: 检测结果列表 [{'label':, 'shapeType':, 'points':, 'result': {}}, ...]
            output_path: 可选输出文件路径
            mode: 渲染模式 'fast'|'high'
            **kwargs: 扩展参数

        返回:
            添加了检测可视化的图像副本
        """
        if image is None or image.size == 0:
            raise ValueError("输入图像为空")

        cls._validate_new_detection_format(detections)

        result_img = image.copy()
        if result_img.ndim == 2:
            result_img = cv2.cvtColor(result_img, cv2.COLOR_GRAY2BGR)

        try:
            if mode == 'fast':
                result_img = cls._render_fast_mode_new(result_img, detections, **kwargs)
            else:
                result_img = cls._render_high_quality_mode_new(result_img, detections, **kwargs)

            if output_path:
                cls._save_image(result_img, output_path)

        except Exception as e:
            print(f"[可视化错误] 渲染失败: {str(e)}")
            return image.copy()

        return result_img

    @classmethod
    def _validate_new_detection_format(cls, detections: List[dict]):
        """验证新格式的检测结果"""
        if not isinstance(detections, list):
            raise ValueError("检测结果必须是列表格式")

        for i, detection in enumerate(detections):
            if not isinstance(detection, dict):
                raise ValueError(f"第{i}个检测结果必须是字典格式")

            # 检查必需字段
            required_fields = ['label', 'shapeType', 'points']
            for field in required_fields:
                if field not in detection:
                    raise ValueError(f"第{i}个检测结果缺少必需字段: {field}")

            # 验证shapeType
            shape_type = detection['shapeType']
            if shape_type not in ['rectangle', 'line', 'polygon']:
                raise ValueError(f"第{i}个检测结果的shapeType必须是: rectangle, line 或 polygon")

            # 验证points格式
            points = detection['points']
            if not isinstance(points, list) or len(points) < 2:
                raise ValueError(f"第{i}个检测结果的points格式错误")

            # 根据shapeType验证points数量
            if shape_type == 'rectangle' and len(points) != 2:
                raise ValueError(f"第{i}个矩形检测需要2个点(左上和右下)")
            elif shape_type == 'line' and len(points) != 2:
                raise ValueError(f"第{i}个线段检测需要2个点(起点和终点)")
            elif shape_type == 'polygon' and len(points) < 3:
                raise ValueError(f"第{i}个多边形检测需要至少3个点")

            # 验证坐标数据
            for j, point in enumerate(points):
                if not isinstance(point, list) or len(point) != 2:
                    raise ValueError(f"第{i}个检测的第{j}个点格式错误")
                try:
                    x, y = map(float, point)
                except (ValueError, TypeError):
                    raise ValueError(f"第{i}个检测的第{j}个点包含无效坐标")

    @classmethod
    def _render_fast_mode_new(cls, image: 'np.ndarray', detections: List[dict], **kwargs) -> 'np.ndarray':
        """快速渲染模式 - 支持新数据格式"""
        rendered_image = image.copy()

        for detection in detections:
            try:
                label = detection['label']
                shape_type = detection['shapeType']
                points = detection['points']
                confidence = detection.get('result', {}).get('confidence', 0)

                # 根据shapeType选择绘制方法
                if shape_type == 'rectangle':
                    cls._draw_rectangle_fast(rendered_image, label, confidence, points)
                elif shape_type == 'line':
                    cls._draw_line_fast(rendered_image, label, confidence, points)
                elif shape_type == 'polygon':
                    cls._draw_polygon_fast(rendered_image, label, confidence, points)

            except Exception as e:
                print(f"[警告] 快速模式绘制跳过异常检测: {str(e)}")
                continue

        return rendered_image

    @classmethod
    def _draw_rectangle_fast(cls, image: 'np.ndarray', label: str, confidence: float, points: List[List[float]]):
        """快速模式绘制矩形"""
        # 提取坐标点
        x1, y1 = map(int, points[0])
        x2, y2 = map(int, points[1])

        if not cls._is_valid_bbox(image, x1, y1, x2, y2):
            return

        # 自适应参数
        line_thickness = max(1, min(image.shape[:2]) // 400)
        font_scale = max(0.4, min(image.shape[:2]) / 2000)

        # 获取颜色
        bbox_color = cls._get_class_color(label)

        # 绘制矩形框
        cv2.rectangle(image, (x1, y1), (x2, y2), bbox_color, line_thickness)

        # 智能标签位置计算
        label_x, label_y, text_anchor = cls._get_smart_label_position(image, points, 'rectangle')

        # 绘制标签
        cls._draw_label_fast(image, label, confidence, label_x, label_y, bbox_color,
                             font_scale, text_anchor=text_anchor)

    @classmethod
    def _draw_line_fast(cls, image: 'np.ndarray', label: str, confidence: float, points: List[List[float]]):
        """快速模式绘制线段"""
        # 提取起点和终点
        x1, y1 = map(int, points[0])
        x2, y2 = map(int, points[1])

        # 坐标验证
        h, w = image.shape[:2]
        if not (0 <= x1 < w and 0 <= y1 < h and 0 <= x2 < w and 0 <= y2 < h):
            return

        # 自适应参数
        line_thickness = 1
        font_scale = max(0.4, min(image.shape[:2]) / 2000)

        # 获取颜色
        line_color = cls._get_class_color(label)

        # 绘制线段
        cv2.line(image, (x1, y1), (x2, y2), line_color, line_thickness)

        # 可选：绘制端点标记
        endpoint_radius = max(2, line_thickness // 2)
        cv2.circle(image, (x1, y1), endpoint_radius, line_color, -1)
        cv2.circle(image, (x2, y2), endpoint_radius, line_color, -1)

        # 智能标签位置计算
        label_x, label_y, text_anchor = cls._get_smart_label_position(image, points, 'line')

        # 绘制标签
        cls._draw_label_fast(image, label, confidence, label_x, label_y, line_color,
                             font_scale, text_anchor=text_anchor)

    @classmethod
    def _draw_polygon_fast(cls, image: 'np.ndarray', label: str, confidence: float, points: List[List[float]]):
        """快速模式绘制多边形"""
        # 转换坐标格式
        points_array = np.array(points, dtype=np.int32).reshape((-1, 1, 2))

        # 自适应参数
        line_thickness = max(1, min(image.shape[:2]) // 400)
        font_scale = max(0.4, min(image.shape[:2]) / 2000)

        # 获取颜色
        polygon_color = cls._get_class_color(label)

        # 绘制多边形边框
        cv2.polylines(image, [points_array], True, polygon_color, line_thickness)

        # 智能标签位置计算
        label_x, label_y, text_anchor = cls._get_smart_label_position(image, points, 'polygon')

        # 绘制标签
        cls._draw_label_fast(image, label, confidence, label_x, label_y, polygon_color,
                             font_scale, text_anchor=text_anchor)

    @classmethod
    def _get_smart_label_position(cls, image: 'np.ndarray', points: List[List[float]],
                                  shape_type: str) -> Tuple[int, int, str]:
        """
        智能计算标签位置，避免被遮挡

        参数:
            image: 输入图像
            points: 形状点列表
            shape_type: 形状类型 ('rectangle', 'line', 'polygon')

        返回:
            (label_x, label_y, text_anchor): 标签位置和文本锚点
        """
        h, w = image.shape[:2]

        if shape_type == 'rectangle':
            x1, y1 = points[0]
            x2, y2 = points[1]
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2

            # 计算到各边界的距离
            margin = 20
            top_space = y1
            bottom_space = h - y2
            left_space = x1
            right_space = w - x2

            # 检查各个位置是否合适
            positions = []

            # 1. 顶部（如果空间足够）
            if top_space > margin * 2:
                positions.append(('top', center_x, y1 - margin))

            # 2. 底部（如果空间足够）
            if bottom_space > margin * 2:
                positions.append(('bottom', center_x, y2 + margin))

            # 3. 左侧（如果空间足够）
            if left_space > margin * 2:
                positions.append(('left', x1 - margin, center_y))

            # 4. 右侧（如果空间足够）
            if right_space > margin * 2:
                positions.append(('right', x2 + margin, center_y))

            # 5. 中心（如果形状足够大）
            shape_width = x2 - x1
            shape_height = y2 - y1
            if shape_width > 50 and shape_height > 30:
                positions.append(('center', center_x, center_y))

            # 选择最佳位置（优先选择有最多空间的位置）
            if positions:
                # 按可用空间排序
                sorted_positions = sorted(positions, key=lambda p: cls._get_position_score(p, h, w))
                best_position = sorted_positions[0]
                label_x, label_y = int(best_position[1]), int(best_position[2])
                text_anchor = cls._get_text_anchor_for_position(best_position[0])
            else:
                # 回退到默认位置
                label_x, label_y = int(x1), int(max(y1, margin))
                text_anchor = 'center'

        elif shape_type == 'line':
            x1, y1 = points[0]
            x2, y2 = points[1]
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2

            # 计算线段角度
            angle = np.arctan2(y2 - y1, x2 - x1) if x2 != x1 else np.pi / 2

            # 根据角度选择垂直偏移
            margin = 20
            if abs(np.sin(angle)) > 0.5:  # 更垂直的线段
                label_x, label_y = center_x, (min(y1, y2) - margin)
                text_anchor = 'bottom' if y1 < y2 else 'top'
            else:  # 更水平的线段
                label_x, label_y = (max(x1, x2) + margin), center_y
                text_anchor = 'left'

        elif shape_type == 'polygon':
            # 计算多边形中心
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            center_x = np.mean(xs)
            center_y = np.mean(ys)

            # 计算多边形外接矩形
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)

            # 检查中心点是否在多边形内
            if cls._point_in_polygon(center_x, center_y, points):
                # 中心点在内，使用中心位置
                label_x, label_y = int(center_x), int(center_y)
                text_anchor = 'center'
            else:
                # 中心点在外，寻找最近的边界位置
                margin = 20
                if min_y > margin:
                    label_x, label_y = center_x, min_y - margin
                    text_anchor = 'bottom'
                elif max_y < h - margin:
                    label_x, label_y = center_x, max_y + margin
                    text_anchor = 'top'
                else:
                    # 回退到第一个顶点
                    label_x, label_y = int(xs[0]), int(ys[0])
                    text_anchor = 'center'

        return int(label_x), int(label_y), text_anchor

    @classmethod
    def _get_position_score(cls, position: Tuple[str, float, float], h: int, w: int) -> float:
        """
        计算位置得分，得分越低越优先
        """
        pos_type, x, y = position

        # 基础分数（位置类型优先级）
        base_scores = {
            'top': 1.0,
            'bottom': 1.2,
            'right': 1.4,
            'left': 1.6,
            'center': 2.0
        }

        score = base_scores.get(pos_type, 2.0)

        # 距离边界越近，分数越高（越可能被遮挡）
        if pos_type in ['top', 'bottom']:
            score += min(abs(x - 0), abs(x - w)) / w * 0.5
        elif pos_type in ['left', 'right']:
            score += min(abs(y - 0), abs(y - h)) / h * 0.5

        return score

    @classmethod
    def _get_text_anchor_for_position(cls, position: str) -> str:
        """根据位置获取文本锚点"""
        anchor_map = {
            'top': 'bottom',
            'bottom': 'top',
            'left': 'right',
            'right': 'left',
            'center': 'center'
        }
        return anchor_map.get(position, 'center')

    @classmethod
    def _point_in_polygon(cls, x: float, y: float, polygon: List[List[float]]) -> bool:
        """判断点是否在多边形内"""
        n = len(polygon)
        inside = False

        p1x, p1y = polygon[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside

    @classmethod
    def _draw_label_fast(cls, image: 'np.ndarray', label: str, confidence: float,
                         x: int, y: int, color: Tuple[int, int, int], font_scale: float,
                         text_anchor: str = 'center'):
        """
        改进的快速模式绘制标签，支持智能定位
        """
        label_text = f"{label}-{confidence:.2f}" if confidence > 0 else label

        (text_width, text_height), baseline = cv2.getTextSize(
            label_text, cls._get_default_font(), font_scale, 1)

        # 根据锚点计算文本背景位置
        if text_anchor == 'center':
            text_bg_x1 = x - text_width // 2
            text_bg_y1 = y - text_height // 2
        elif text_anchor == 'top':
            text_bg_x1 = x - text_width // 2
            text_bg_y1 = y
        elif text_anchor == 'bottom':
            text_bg_x1 = x - text_width // 2
            text_bg_y1 = y - text_height
        elif text_anchor == 'left':
            text_bg_x1 = x
            text_bg_y1 = y - text_height // 2
        elif text_anchor == 'right':
            text_bg_x1 = x - text_width
            text_bg_y1 = y - text_height // 2
        else:
            text_bg_x1 = x
            text_bg_y1 = y - text_height - baseline

        # 确保标签在图像内
        margin = 2
        text_bg_x1 = max(margin, min(text_bg_x1, image.shape[1] - text_width - margin))
        text_bg_y1 = max(margin, min(text_bg_y1, image.shape[0] - text_height - margin))

        text_bg_x2 = text_bg_x1 + text_width
        text_bg_y2 = text_bg_y1 + text_height

        # 绘制半透明背景
        overlay = image.copy()
        cv2.rectangle(overlay, (text_bg_x1, text_bg_y1),
                      (text_bg_x2, text_bg_y2), color, -1)
        cv2.addWeighted(overlay, cls.LABEL_BG_ALPHA, image, 1 - cls.LABEL_BG_ALPHA, 0, image)

        # 绘制文本
        text_y = text_bg_y2 - baseline // 2
        cv2.putText(image, label_text, (text_bg_x1, text_y),
                    cls._get_default_font(), font_scale, cls.TEXT_COLOR, 1)

    @classmethod
    def _render_high_quality_mode_new(cls, image: 'np.ndarray', detections: List[dict], **kwargs) -> 'np.ndarray':
        """高质量渲染模式 - 支持新数据格式"""
        height, width = image.shape[:2]

        # 初始化Matplotlib图形
        fig = mplfigure.Figure(frameon=False)
        dpi = fig.get_dpi()
        fig.set_size_inches((width + 1e-2) / dpi, (height + 1e-2) / dpi)
        canvas = FigureCanvasAgg(fig)
        ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
        ax.axis("off")
        ax.set_xlim(0.0, width)
        ax.set_ylim(height)
        ax.invert_yaxis()

        # 显示原始图像
        ax.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

        # 自适应字体大小
        base_font_size = max(np.sqrt(height * width) // 90, 10)

        # 绘制每个检测结果
        for detection in detections:
            try:
                label = detection['label']
                shape_type = detection['shapeType']
                points = detection['points']
                confidence = detection.get('result', {}).get('confidence', 0)

                color = cls._get_mpl_class_color(label)

                if shape_type == 'rectangle':
                    cls._draw_rectangle_hq(ax, label, confidence, points, color, base_font_size, height, width)
                elif shape_type == 'line':
                    cls._draw_line_hq(ax, label, confidence, points, color, base_font_size, height, width)
                elif shape_type == 'polygon':
                    cls._draw_polygon_hq(ax, label, confidence, points, color, base_font_size, height, width)

            except Exception as e:
                print(f"[警告] 高质量模式绘制跳过异常检测: {str(e)}")
                continue

        # 渲染到图像缓冲区
        canvas.draw()
        buffer = np.frombuffer(canvas.buffer_rgba(), dtype=np.uint8)
        overlay_img = buffer.reshape(height, width, 4)

        # 图像混合
        alpha_channel = overlay_img[..., 3:].astype(np.float32) / 255.0
        blended_img = (image * (1 - alpha_channel) + overlay_img[..., :3] * alpha_channel).astype(np.uint8)

        return blended_img

    @classmethod
    def _draw_rectangle_hq(cls, ax, label: str, confidence: float, points: List[List[float]],
                           color: str, base_font_size: float, height: int, width: int):
        """高质量模式绘制矩形"""
        x0, y0 = points[0]
        x1, y1 = points[1]

        if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
            return

        # 绘制矩形框
        bbox_patch = mpatches.Rectangle(
            (x0, y0), x1 - x0, y1 - y0,
            fill=False, edgecolor=color,
            linewidth=max(base_font_size / 4, 1),
            alpha=0.8, linestyle='-'
        )
        ax.add_patch(bbox_patch)

        # 智能添加标签
        label_text = f"{label}-{confidence:.2f}" if confidence > 0 else label
        cls._add_smart_shape_label(ax, label_text, x0, y0, x1, y1, color, base_font_size, height, width)

    @classmethod
    def _draw_line_hq(cls, ax, label: str, confidence: float, points: List[List[float]],
                      color: str, base_font_size: float, height: int, width: int):
        """高质量模式绘制线段"""
        x1, y1 = points[0]
        x2, y2 = points[1]

        # 绘制线段
        line = mpatches.FancyBboxPatch(
            (x1, y1), x2 - x1, y2 - y1,
            boxstyle=mpatches.BoxStyle("Round", pad=0),
            fill=False, edgecolor=color,
            linewidth=max(base_font_size / 3, 2),  # 线段稍粗
            alpha=0.9, linestyle='-'
        )
        ax.add_patch(line)

        # 绘制端点
        ax.scatter([x1, x2], [y1, y2], c=color, s=20, alpha=0.8)

        # 智能标签位置
        label_text = f"{label}-{confidence:.2f}" if confidence > 0 else label
        label_x, label_y, ha, va = cls._get_smart_line_label_position(x1, y1, x2, y2, height, width)

        ax.text(
            label_x, label_y, label_text, size=base_font_size * 0.8, family="sans-serif",
            bbox={"facecolor": "black", "alpha": 0.8, "pad": 0.7, "edgecolor": "none"},
            verticalalignment=va, horizontalalignment=ha,
            color="white", zorder=10
        )

    @classmethod
    def _draw_polygon_hq(cls, ax, label: str, confidence: float, points: List[List[float]],
                         color: str, base_font_size: float, height: int, width: int):
        """高质量模式绘制多边形"""
        polygon_array = np.array(points)

        # 绘制多边形
        polygon_patch = mpatches.Polygon(
            polygon_array,
            fill=False, edgecolor=color,
            linewidth=max(base_font_size / 4, 1),
            alpha=0.8, linestyle='-'
        )
        ax.add_patch(polygon_patch)

        # 智能标签位置
        label_text = f"{label}-{confidence:.2f}" if confidence > 0 else label
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        label_x, label_y, ha, va = cls._get_smart_polygon_label_position(xs, ys, height, width)

        ax.text(
            label_x, label_y, label_text, size=base_font_size * 0.8, family="sans-serif",
            bbox={"facecolor": "black", "alpha": 0.8, "pad": 0.7, "edgecolor": "none"},
            verticalalignment=va, horizontalalignment=ha,
            color="white", zorder=10
        )

    @classmethod
    def _get_smart_line_label_position(cls, x1: float, y1: float, x2: float, y2: float,
                                       height: int, width: int) -> Tuple[float, float, str, str]:
        """智能计算线段标签位置"""
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2

        # 计算线段角度
        dx = x2 - x1
        dy = y2 - y1
        angle = np.arctan2(dy, dx) if dx != 0 else np.pi / 2

        # 根据线段方向选择标签位置
        margin = 20

        if abs(np.sin(angle)) > 0.707:  # 更垂直的线段
            if y1 < y2:  # 从上到下
                label_x, label_y = center_x, max(y1, y2) + margin
                ha, va = 'center', 'bottom'
            else:  # 从下到上
                label_x, label_y = center_x, min(y1, y2) - margin
                ha, va = 'center', 'top'
        else:  # 更水平的线段
            if x1 < x2:  # 从左到右
                label_x, label_y = max(x1, x2) + margin, center_y
                ha, va = 'left', 'center'
            else:  # 从右到左
                label_x, label_y = min(x1, x2) - margin, center_y
                ha, va = 'right', 'center'

        # 确保标签在图像内
        label_x = max(margin, min(label_x, width - margin))
        label_y = max(margin, min(label_y, height - margin))

        return label_x, label_y, ha, va

    @classmethod
    def _get_smart_polygon_label_position(cls, xs: List[float], ys: List[float],
                                          height: int, width: int) -> Tuple[float, float, str, str]:
        """智能计算多边形标签位置"""
        center_x = np.mean(xs)
        center_y = np.mean(ys)
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        margin = 20
        positions = []

        # 检查各个位置是否合适
        if center_y - margin > 0:  # 中心上方
            positions.append((center_x, min_y - margin, 'center', 'bottom'))
        if center_y + margin < height:  # 中心下方
            positions.append((center_x, max_y + margin, 'center', 'top'))
        if center_x - margin > 0:  # 中心左侧
            positions.append((min_x - margin, center_y, 'right', 'center'))
        if center_x + margin < width:  # 中心右侧
            positions.append((max_x + margin, center_y, 'left', 'center'))

        # 如果中心点周围有空间，优先使用中心
        if len(xs) > 2 and cls._point_in_polygon(center_x, center_y,
                                                 list(zip(xs, ys))):
            positions.append((center_x, center_y, 'center', 'center'))

        # 选择最佳位置
        if positions:
            # 优先选择中心位置
            for pos in positions:
                if pos[4] == 'center':  # 位置描述在第五个元素
                    return pos
            return positions[0]

        # 回退到第一个顶点
        return xs[0], ys[0], 'center', 'center'

    @classmethod
    def _add_smart_shape_label(cls, ax, text: str, x0: float, y0: float, x1: float, y1: float,
                               color: str, base_font_size: float, height: int, width: int):
        """智能为形状添加标签"""
        # 计算可用空间
        margin = 0.01 * min(height, width)
        top_space = y0
        bottom_space = height - y1
        left_space = x0
        right_space = width - x1

        # 选择标签位置
        if top_space > bottom_space and top_space > margin * 2:
            # 放在顶部
            label_x, label_y = (x0 + x1) / 2, y0 - margin
            ha, va = 'center', 'bottom'
        elif bottom_space > margin * 2:
            # 放在底部
            label_x, label_y = (x0 + x1) / 2, y1 + margin
            ha, va = 'center', 'top'
        elif right_space > left_space and right_space > margin * 2:
            # 放在右侧
            label_x, label_y = x1 + margin, (y0 + y1) / 2
            ha, va = 'left', 'center'
        elif left_space > margin * 2:
            # 放在左侧
            label_x, label_y = x0 - margin, (y0 + y1) / 2
            ha, va = 'right', 'center'
        else:
            # 放在中心
            label_x, label_y = (x0 + x1) / 2, (y0 + y1) / 2
            ha, va = 'center', 'center'

        # 自适应字体大小
        shape_area = (x1 - x0) * (y1 - y0)
        image_area = height * width
        area_ratio = shape_area / image_area
        font_size = base_font_size * np.clip(np.sqrt(area_ratio * 20), 0.5, 2.0)

        # 添加标签
        ax.text(
            label_x, label_y, text, size=font_size, family="sans-serif",
            bbox={"facecolor": "black", "alpha": 0.8, "pad": 0.7, "edgecolor": "none"},
            verticalalignment=va, horizontalalignment=ha,
            color="white", zorder=10
        )

    # ==================== 保持原有功能，增加新格式支持 ====================

    @classmethod
    def draw_bounding_boxes(cls, image, detections, mode='fast', **kwargs):
        """
        兼容方法：支持新旧两种数据格式
        """
        # 自动检测数据格式并转换
        formatted_detections = cls._auto_format_detections(detections)
        return cls.visualize(image, formatted_detections, mode=mode, **kwargs)

    @classmethod
    def _auto_format_detections(cls, detections):
        """自动检测并转换数据格式"""
        if not detections:
            return []

        # 检测是否为旧格式
        first_det = detections[0]
        if isinstance(first_det, list) and len(first_det) >= 6:
            # 旧格式转换为新格式
            return cls._convert_old_to_new_format(detections)
        elif isinstance(first_det, dict):
            # 已经是新格式
            return detections
        else:
            raise ValueError("无法识别的检测结果格式")

    @classmethod
    def _convert_old_to_new_format(cls, old_detections):
        """将旧格式转换为新格式"""
        new_detections = []
        for det in old_detections:
            if len(det) >= 6:
                new_det = {
                    'label': det[0],
                    'shapeType': 'rectangle',
                    'points': [[det[2], det[3]], [det[4], det[5]]],
                    'result': {'confidence': det[1]}
                }
                new_detections.append(new_det)
        return new_detections

    # ==================== 保持其他原有方法不变 ====================

    @classmethod
    def _get_class_color(cls, class_name: str) -> Tuple[int, int, int]:
        """为类别生成唯一颜色 (BGR格式)"""
        if class_name not in cls.COLOR_PALETTE:
            hash_val = hash(class_name) % 180
            hue = (hash_val * 137) % 180
            hsv_color = np.uint8([[[hue, 200, 200]]])
            bgr_color = cv2.cvtColor(hsv_color, cv2.COLOR_HSV2BGR)
            cls.COLOR_PALETTE[class_name] = tuple(map(int, bgr_color[0][0]))
        return cls.COLOR_PALETTE[class_name]

    @classmethod
    def _get_mpl_class_color(cls, class_name: str) -> str:
        """为类别生成Matplotlib颜色"""
        bgr_color = cls._get_class_color(class_name)
        rgb_color = (bgr_color[2] / 255, bgr_color[1] / 255, bgr_color[0] / 255)
        return mplc.to_hex(rgb_color)

    @classmethod
    def _is_valid_bbox(cls, image: 'np.ndarray', x1: int, y1: int, x2: int, y2: int) -> bool:
        """验证边界框坐标有效性"""
        h, w = image.shape[:2]
        return (0 <= x1 < x2 <= w) and (0 <= y1 < y2 <= h)

    @classmethod
    def _save_image(cls, image: 'np.ndarray', path: str):
        """保存图像到文件"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        cv2.imwrite(path, image)

    # 快捷方法别名（保持兼容）
    @classmethod
    def fast_draw(cls, image, detections, **kwargs):
        return cls.visualize(image, detections, mode='fast', **kwargs)

    @classmethod
    def hq_draw(cls, image, detections, **kwargs):
        return cls.visualize(image, detections, mode='high', **kwargs)