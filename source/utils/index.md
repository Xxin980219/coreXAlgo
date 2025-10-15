# Utils Module

utils 模块包含算法开发中常用的基础工具函数和类，旨在提高开发效率，减少重复代码编写。


## Components
::::{grid} 2 2 2 3
:gutter: 2
:padding: 1

:::{grid-item-card} {octicon}`codescan` Basic
:link: basic
:link-type: doc

基础函数
:::

:::{grid-item-card} {octicon}`diamond` Bbox_util
:link: bbox_util
:link-type: doc

标注文件转换，LabelMe ↔ VOC ↔ YOLO 标注格式互转
:::

:::{grid-item-card} {octicon}`cloud` Ftp_client
:link: ftp_client
:link-type: doc

图像裁剪（支持voc标签）
:::

:::{grid-item-card} {octicon}`cache` Mt_db_client
:link: mt_db_client
:link-type: doc

xml文件处理
:::


:::{grid-item-card} {octicon}`download` Mt_ftp_downloader
:link: mt_ftp_downloader
:link-type: doc

xml文件处理
:::

:::{grid-item-card} {octicon}`cloud` Sftp_client
:link: sftp_client
:link-type: doc

xml文件处理
:::
::::


```{toctree}
:caption: utils
:hidden:

basic
bbox_util
ftp_client
mt_db_client
mt_ftp_downloader
sftp_client
```
