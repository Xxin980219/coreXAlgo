# File_processing Module

file_processing 模块为算法开发中常用的文件处理功能函数，特别是针对标注数据和图像处理的自定义工具函数


## Components
::::{grid} 2 2 2 3
:gutter: 2
:padding: 1

:::{grid-item-card} {octicon}`codescan` Basic
:link: basic
:link-type: doc

基础函数
:::

:::{grid-item-card} {octicon}`arrow-switch` Annotation_convert
:link: annotation_convert
:link-type: doc

标注文件转换，LabelMe ↔ VOC ↔ YOLO 标注格式互转
:::

:::{grid-item-card} {octicon}`image` Image_crop
:link: image_crop
:link-type: doc

图像裁剪（支持voc标签）
:::

:::{grid-item-card} {octicon}`archive` Voc_xml_deal
:link: voc_xml_deal
:link-type: doc

xml文件处理
:::
::::


```{toctree}
:caption: file_processing
:hidden:

basic
annotation_convert
image_crop
voc_xml_deal
```
