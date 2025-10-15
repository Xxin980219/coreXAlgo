import cv2
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
    if len(polygon) < 4:
        raise ValueError("Polygon must have at least 2 points (4 coordinates)")

    # Ensure even length (ignore last element if odd)
    coords = np.asarray(polygon[:len(polygon) // 2 * 2], dtype=np.float32)
    points = coords.reshape(-1, 2)  # Reshape to [N, 2]

    l, t = np.min(points, axis=0)
    r, b = np.max(points, axis=0)
    return [l, t, r, b]


def draw_bboxes_on_img(img, bboxes, labels=None, color=(255, 0, 0),
                       font_scale=1, thickness=3, font_offset=(0, 0)):
    """
    Draw bounding boxes and labels on an image.

    Args:
        img: Input image (numpy array or OpenCV UMat)
        bboxes: List of bounding boxes in [(left, top, right, bottom), ...] format
        labels: Optional list of labels for each bounding box
        color: RGB color for boxes and text (default: red)
        font_scale: Font size scaling factor
        thickness: Line thickness for boxes and text
        font_offset: (x, y) offset for text position relative to bottom-left corner

    Returns:
        Image with drawn bounding boxes and labels

    Example:
        >>> # 创建一个空白图像
        >>> img = np.zeros((100, 100, 3), dtype=np.uint8)
        >>> # 定义两个边界框
        >>> bboxes = [[10, 10, 50, 50], [60, 60, 90, 90]]
        >>> labels = ["目标1", "目标2"]
        >>> # 绘制绿色边界框和标签
        >>> result = draw_bboxes_on_img(img, bboxes, labels, color=(0, 255, 0))
        >>> cv2.imwrite("result.jpg", result)
    """
    if not bboxes:
        return img

    # Validate inputs
    if labels and len(labels) != len(bboxes):
        raise ValueError("Length of labels must match length of bboxes")

    # Handle OpenCV UMat if needed
    if hasattr(img, 'get') and callable(img.get):  # Check if it's UMat
        img = img.get()
    else:
        img = img.copy()
    for i, bbox in enumerate(bboxes):
        l, t, r, b = map(int, bbox[:4])
        # Draw bounding box
        cv2.rectangle(img, (l, t), (r, b), color=color, thickness=thickness)
        if labels:
            text_position = (l + font_offset[0], b + font_offset[1])
            cv2.putText(img, str(labels[i]), text_position, cv2.FONT_ITALIC, font_scale, color, thickness)
    return img


def draw_polygons_on_img_pro(img, polygons, labels=None, colors=None, alpha=0.5, is_rect=False):
    """
    Draw polygons/rectangles on image with high-quality rendering

    Args:
        img: Input image (H,W) or (H,W,3)
        polygons: List of polygons [(x1,y1,x2,y2,...), ...]
        labels: Optional list of text labels
        colors: Optional list of colors for each polygon
        alpha: Opacity (0-1)
        is_rect: If True, treat polygons as rectangles (x1,y1,x2,y2)

    Returns:
        Image with drawn polygons (uint8 numpy array)

    Example:
        >>> # 读取图像
        >>> img = cv2.imread("input.jpg")
        >>> # 定义多边形和标签
        >>> polygons = [[10, 10, 50, 10, 50, 50, 10, 50], [60, 60, 90, 60, 90, 90, 60, 90]]
        >>> labels = ["区域A", "区域B"]
        >>> colors = ['red', 'blue']
        >>> # 高质量绘制
        >>> result = draw_polygons_on_img_pro(img, polygons, labels, colors, alpha=0.7)
        >>> cv2.imwrite("high_quality_result.jpg", result)
    """
    import matplotlib as mpl
    import matplotlib.colors as mplc
    import matplotlib.figure as mplfigure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    _SMALL_OBJECT_AREA_THRESH = 1000  # Area threshold for small objects

    # Input validation
    if not polygons:
        return img.copy()

    if labels and len(labels) != len(polygons):
        raise ValueError("labels length must match polygons length")
    if colors and len(colors) != len(polygons):
        raise ValueError("colors length must match polygons length")

    height, width = img.shape[:2]

    # Setup figure
    fig = mplfigure.Figure(frameon=False)
    dpi = fig.get_dpi()
    fig.set_size_inches((width + 1e-2) / dpi, (height + 1e-2) / dpi)
    canvas = FigureCanvasAgg(fig)
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.axis("off")
    ax.set_xlim(0.0, width)
    ax.set_ylim(height)
    ax.invert_yaxis()  # Match image coordinates

    # Calculate adaptive font size
    default_font_size = max(np.sqrt(height * width) // 90, 10)

    def _change_color_brightness(color, brightness_factor):
        assert brightness_factor >= -1.0 and brightness_factor <= 1.0
        import colorsys
        color = mplc.to_rgb(color)
        polygon_color = colorsys.rgb_to_hls(*mplc.to_rgb(color))
        modified_lightness = polygon_color[1] + (brightness_factor * polygon_color[1])
        modified_lightness = 0.0 if modified_lightness < 0.0 else modified_lightness
        modified_lightness = 1.0 if modified_lightness > 1.0 else modified_lightness
        modified_color = colorsys.hls_to_rgb(polygon_color[0], modified_lightness, polygon_color[2])
        return modified_color

    for i, polygon in enumerate(polygons):
        color = colors[i] if colors else 'gold'

        if is_rect:
            x0, y0, x1, y1 = map(float, polygon[:4])

            patch = mpl.patches.Rectangle(
                (x0, y0), x1 - x0, y1 - y0,
                fill=False, edgecolor=color,
                linewidth=max(default_font_size / 4, 1),
                alpha=alpha, linestyle='-',
            )
        else:
            box = polygon_to_bbox(polygon)
            x0, y0, x1, y1 = box[:4]
            # make edge color darker than the polygon color
            if alpha > 0.8:
                edge_color = _change_color_brightness(color, brightness_factor=-0.7)
            else:
                edge_color = color
                edge_color = mplc.to_rgb(edge_color) + (1,)

            polygon = np.array(polygon).reshape(-1, 2)
            patch = mpl.patches.Polygon(
                polygon,
                fill=True,
                facecolor=mplc.to_rgb(color) + (alpha,),
                edgecolor=edge_color,
                linewidth=max(default_font_size // 15, 1),
            )
        ax.add_patch(patch)

        # Add label if specified
        if labels:
            text = str(labels[i])

            area = (y1 - y0) * (x1 - x0)
            text_pos = (x0, y0)
            if area < _SMALL_OBJECT_AREA_THRESH or y1 - y0 < 40:
                text_pos = (x1, y0) if y1 >= height - 5 else (x0, y1)

            height_ratio = (y1 - y0) / np.sqrt(height * width)
            text_color = _change_color_brightness(color, brightness_factor=0.7)
            font_size = np.clip((height_ratio - 0.02) / 0.08 + 1, 1.2, 2) * 0.5 * default_font_size

            text_color = np.maximum(mplc.to_rgb(text_color), [0.2, 0.2, 0.2])
            text_color[np.argmax(text_color)] = max(0.8, np.max(text_color))

            ax.text(
                *text_pos, text,
                size=font_size, family="sans-serif",
                bbox={"facecolor": "black", "alpha": 0.8, "pad": 0.7, "edgecolor": "none"},
                verticalalignment="top", horizontalalignment="left",
                color=text_color, zorder=10, rotation=0,
            )

    canvas.draw()
    buffer = np.frombuffer(canvas.buffer_rgba(), dtype=np.uint8)
    overlay = buffer.reshape(height, width, 4)

    # Blend with original image
    img_out = img.copy()
    if img_out.ndim == 2:
        img_out = np.dstack([img_out] * 3)
    alpha_channel = overlay[..., 3:].astype(np.float32) / 255.0
    visualized_image = (img_out * (1 - alpha_channel) + overlay[..., :3] * alpha_channel).astype(np.uint8)

    return visualized_image


def draw_bboxes_on_img_pro(img, bboxes, labels=None, colors=None, alpha=0.5):
    """
    Draw rectangles on image with high-quality rendering

    Args:
        img: Input image (H,W) or (H,W,3)
        polygons: List of polygons [(x1,y1,x2,y2,...), ...]
        labels: Optional list of text labels
        colors: Optional list of colors for each polygon
        alpha: Opacity (0-1)

    Returns:
        Image with drawn polygons (uint8 numpy array)

    Example:
        >>> # 读取图像
        >>> img = cv2.imread("image.jpg")
        >>> # 定义边界框和标签
        >>> bboxes = [[10, 10, 50, 50], [60, 60, 90, 90]]
        >>> labels = ["目标1", "目标2"]
        >>> colors = ['red', 'blue']
        >>> # 高质量绘制边界框
        >>> result = draw_bboxes_on_img_pro(img, bboxes, labels, colors, alpha=0.6)
        >>> cv2.imwrite("bboxes_result.jpg", result)
    """
    return draw_polygons_on_img_pro(img, bboxes, labels=labels,
                                    colors=colors, alpha=alpha, is_rect=True)


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


def mask_to_polygon(mask: np.ndarray):
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
    if not isinstance(mask, np.ndarray) or mask.ndim != 2:
        return None

    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None

    polygons = []
    for cnt in contours:
        if cv2.contourArea(cnt) > area_threshold:
            if poly := cnt_to_polygon(cnt):  # Walrus operator requires Python 3.8+
                polygons.append(poly)

    return polygons if polygons else None
