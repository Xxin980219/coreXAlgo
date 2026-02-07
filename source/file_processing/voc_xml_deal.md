# Voc_xml_deal

VOC XML 标注文件处理器

## 核心功能

- **类别更新**：更新 XML 文件中的类别名称
- **无标注检测**：提取无标注的图片
- **缺陷统计**：统计缺陷类别及其出现次数
- **类别过滤**：提取包含特定类别的图片
- **类别分组**：获取按类别分组的图片列表
- **详细统计**：获取详细的类别统计信息
- **批量处理**：批量处理多个 XML 文件
- **多线程处理**：使用多线程提高处理效率

## 使用示例

### 按类别分组获取图片

```python
from coreXAlgo.file_processing import VOCXMLProcessor

# 创建处理器实例
processor = VOCXMLProcessor()

# 获取按类别分组的图片列表
category_images = processor.get_images_by_category('annotations/')
for category, images in category_images.items():
    print(f"Category: {category}, Image count: {len(images)}")
```

### 获取详细的类别统计信息

```python
from coreXAlgo.file_processing import VOCXMLProcessor

# 创建处理器实例
processor = VOCXMLProcessor()

# 获取详细的类别统计信息
stats = processor.get_category_statistics('annotations/')
print(f"Total categories: {stats['total_categories']}")
print(f"Total images: {stats['total_images']}")
print("\nCategory distribution:")
for category, count in stats['category_counts'].items():
    print(f"  {category}: {count} images")
```

```{eval-rst}
.. automodule:: coreXAlgo.file_processing.voc_xml_deal
   :members:
   :undoc-members:
   :show-inheritance:
```