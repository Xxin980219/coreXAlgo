# fmt: off
__version__ = '0.1.0'
# fmt: on


# -- Project information -----------------------------------------------------

project = 'coreXAIgo'
copyright = '2025, Xiong xin'
author = 'Xiong xin'

version = __version__
release = __version__

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    # 支持 Google/NumPy 风格的文档字符串
    "sphinx.ext.napoleon",
    # myst 解析器
    "myst_parser",
    # 代码块复制按钮扩展
    "sphinx_copybutton",
    # tab 面板插件
    'sphinx_tabs.tabs',
    # 折叠警告（注释、警告等）的功能按钮
    "sphinx_togglebutton",
]

templates_path = ['_templates']

source_suffix = ['.rst', '.md']

source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = "index"

language = 'zh_CN'

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

todo_include_todos = False

# -- Options for HTML output -------------------------------------------------

# html_theme = 'alabaster'
html_theme = 'sphinx_rtd_theme'

html_logo = "_static/snntorch_alpha_full.png"

html_static_path = ['_static']
# html_style = "custom.css"

html_theme_options = {
    'style_external_links': True,
}

# Output file base name for HTML help builder.
htmlhelp_basename = "coreXAIgo"
# 可选：修改 html_title 来控制浏览器标签页标题
html_title = 'coreXAIgo Documentation'


# -- Options for manual page output ------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [(master_doc, "corexAIgo", "corexAIgo Documentation", [author], 1)]

# -- Options for Texinfo output ----------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (
        master_doc,
        "corexAIgo",
        "corexAIgo Documentation",
        author,
        "corexAIgo",
        "One line description of project.",
        "Miscellaneous",
    ),
]


def setup(app):
    app.add_css_file('custom.css')

