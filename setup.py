from setuptools import setup, find_packages
import os


# 自动读取版本号（假设ultralytics/__init__.py中有__version__）
def get_version():
    with open("ultralytics/__init__.py") as f:
        for line in f:
            if line.startswith("__version__"):
                return eval(line.split("=")[-1])

def read_requirements():
    """读取requirements.txt"""
    with open('ultralytics/requirements.txt') as f:
        return [line.strip() for line in f if line.strip()]

setup(
    name="ultralytics",
    version=get_version(),
    packages=find_packages(),  # 自动发现所有包
    include_package_data=True,  # 包含非代码文件

    # 重要：包含模型权重和其他资源文件
    package_data={
        "ultralytics": [
            "*.txt",
            "cfg/*.yaml",
            "cfg/**/**/*.yaml",
        ],
    },

    install_requires=[],
    # # YOLO的依赖项（根据requirements.txt调整）
    # install_requires=read_requirements(),

    # 元数据
    author="Glenn Jocher, Jing Qiu",
    author_email="Glenn Jocher <glenn.jocher@ultralytics.com>, Jing Qiu <jing.qiu@ultralytics.com>",
    description="YOLOv13",
    license="AGPL-3.0",
    python_requires=">=3.11",  # Python版本要求
)
