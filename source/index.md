# coreXAlgo Documentation  

该算法开发工具库是一个根据本人自身算法工程师日常工作而构建的综合性工具集合。

本库整合了算法开发过程中常用的核心功能模块：计算机视觉处理技术、文件操作工具和基础实用函数。通过模块化的设计，为算法研发提供高效、可靠的技术支持，显著提升开发效率，减少重复性工作，确保代码质量和可维护性。

:::{dropdown} {octicon}`checklist;1em`&nbsp; 项目架构
:animate: fade-in-slide-down

根目录/  
├── adv_cv/ # 计算机视觉技术改进模块  
├── file_processing/ # 文件处理功能模块  
└── utils/ # 基础工具函数模块
:::

## {octicon}`book` Modules 

::::{grid}

:::{grid-item-card} {octicon}`rocket` Adv_cv Module
:link: adv_cv/index
:link-type: doc

常用的计算机视觉技术和处理方法,以及对OpenCV函数的改进版
:::

:::{grid-item-card} {octicon}`file` File_processing Module
:link: file_processing/index
:link-type: doc

常用的文件处理功能函数，特别是针对标注数据和图像处理的自定义工具函数
:::

:::{grid-item-card} {octicon}`hubot` Utils Module
:link: utils/index
:link-type: doc

常用的基础工具函数和类

::::

```{toctree}
:caption: Modules
:hidden:

adv_cv/index
file_processing/index
utils/index
```