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

bbox框处理和可视化
:::

:::{grid-item-card} {octicon}`cloud` Ftp_client
:link: ftp_client
:link-type: doc

FTP客户端下载和上传
:::

:::{grid-item-card} {octicon}`cache` Mt_db_client
:link: mt_db_client
:link-type: doc

轻量级多数据库查询客户端
:::


:::{grid-item-card} {octicon}`download` Mt_file_downloader
:link: mt_file_downloader
:link-type: doc

多线程并行下载ftp/sftp文件夹的所有文件
:::

:::{grid-item-card} {octicon}`cloud` Sftp_client
:link: sftp_client
:link-type: doc

SFTP客户端下载和上传，优化了连接稳定性
:::
::::



```{toctree}
:caption: utils
:hidden:

basic
bbox_util
ftp_client
mt_db_client
mt_file_downloader
sftp_client
```
