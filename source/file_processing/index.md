# File_processing Module

<div class="module-header">
  <div class="module-content">
    <h1>File_processing Module</h1>
    <p class="module-description">文件处理模块</p>
    <p class="module-detail">为算法开发中常用的文件处理功能函数，特别是针对标注数据和图像处理的自定义工具函数</p>
  </div>
</div>

<style>
  .module-header {
    background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
    padding: 1.5rem;
    border-radius: 8px;
    margin-bottom: 1.5rem;
    color: white;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  }
  
  .module-content {
    max-width: 800px;
    margin: 0 auto;
  }
  
  .module-content h1 {
    font-size: 2rem;
    margin-bottom: 0.5rem;
    font-weight: bold;
  }
  
  .module-description {
    font-size: 1.1rem;
    margin-bottom: 0.5rem;
    opacity: 0.9;
  }
  
  .module-detail {
    font-size: 0.9rem;
    opacity: 0.8;
  }
  
  .component-card {
    border-radius: 8px;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    border: 1px solid #e9ecef;
  }
  
  .component-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
  }
  
  .component-icon {
    font-size: 1.5rem;
    margin-bottom: 0.5rem;
  }
</style>

## 📋 模块概览

**File_processing** 模块提供了一系列文件处理功能，专为算法开发中的数据管理和预处理任务设计。该模块包含了标注格式转换、图像裁剪、数据预处理等核心功能，旨在简化数据处理流程，提高开发效率。

## 🚀 核心功能

- **文件操作**：批量文件复制、移动、查找
- **标注转换**：YOLO、LabelMe、VOC 格式互转
- **图像裁剪**：基于标注的智能裁剪
- **数据预处理**：YOLO 数据集旋转、增强
- **压缩管理**：支持多种压缩格式
- **XML处理**：VOC 标注文件批量处理

## 📁 组件列表

::::{grid} 2 2 2 3
:gutter: 2
:padding: 1

:::{grid-item-card} {octicon}`codescan` Basic
:link: basic
:link-type: doc
:class-card: component-card

**基础函数**

提供文件查找、复制、移动、随机选择和清理不匹配文件等基础文件操作功能。
:::

:::{grid-item-card} {octicon}`arrow-switch` Annotation_convert
:link: annotation_convert
:link-type: doc
:class-card: component-card

**标注文件转换**

支持 LabelMe、VOC、YOLO 三种标注格式之间的相互转换，包含标签映射功能。
:::

:::{grid-item-card} {octicon}`image` Image_crop
:link: image_crop
:link-type: doc
:class-card: component-card

**图像裁剪**

基于 VOC 标注格式的智能图像裁剪，支持保留/丢弃无缺陷区域，分开保存 OK/NG 图像。
:::

:::{grid-item-card} {octicon}`archive` Voc_xml_deal
:link: voc_xml_deal
:link-type: doc
:class-card: component-card

**VOC XML 处理器**

批量处理 VOC XML 标注文件，支持类别更新、统计分析、按类别提取图片等功能。
:::

:::{grid-item-card} {octicon}`database` Data_preprocessing
:link: data_preprocessing
:link-type: doc
:class-card: component-card

**YOLO数据预处理**

支持 YOLO 数据集旋转处理，包括顺时针90度、逆时针90度、180度旋转等多种方式。
:::

:::{grid-item-card} {octicon}`archive` Archive
:link: archive
:link-type: doc
:class-card: component-card

**压缩解压管理器**

支持多种压缩格式的压缩和解压操作，包括 ZIP、TAR、7Z、RAR 等。
:::

::::

## 🔧 使用示例

```python
from coreXAlgo.file_processing import clean_unmatched_files, AnnotationConverter

# 清理不匹配的文件
clean_unmatched_files(
    folder_path='dataset/train',
    label_ext='.txt',
    delete_images=False,
    delete_labels=False,
    dry_run=True
)

# 标注格式转换
converter = AnnotationConverter(['person', 'car', 'dog'])
converter.voc_to_yolo_obj('voc/001.xml', 'yolo_labels/001.txt')
```

## 🎯 应用场景

- **数据集管理**：文件组织、批量操作、格式转换
- **标注处理**：格式转换、批量更新、统计分析
- **数据预处理**：图像裁剪、数据增强、旋转处理
- **文件管理**：压缩解压、批量复制、移动重命名
- **质量控制**：文件匹配检查、冗余文件清理

## 📚 相关资源

- [YOLO 官方文档](https://github.com/ultralytics/yolov5)
- [LabelMe 标注工具](https://github.com/wkentaro/labelme)
- [Pascal VOC 格式说明](http://host.robots.ox.ac.uk/pascal/VOC/)

```{toctree}
:caption: file_processing
:hidden:

basic
annotation_convert
image_crop
voc_xml_deal
data_preprocessing
archive
```
