# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'zumiAI_python'
copyright = '2025, robolink'
author = 'robolink'
release = '1.0.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',   # 코드의 docstring을 가져와 자동 문서화
    'sphinx.ext.napoleon',  # Google/NumPy 스타일 docstring 파싱 지원
    'sphinx_copybutton', #코드 블록에 복사 버튼을 추가하여 사용자가 코드를 쉽게 복사할 수 있게 합니다.
    'sphinx.ext.autosummary',
]

autosummary_generate = True # 이 옵션을 True로 설정해야 autosummary가 자동으로 .rst 파일을 생성합니다.

templates_path = ['_templates', 'autosummary_templates']
exclude_patterns = []

language = 'ko'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
#html_static_path = ['_static']
#html_static_path = ['..\build\html\source\_static']

# custom.css is inside one of the html_static_path folders (e.g. _static)
#html_css_files = ["custom.css"]
# html_theme_options = {
#     'collapse_navigation': False, # 이 값을 False로 변경해보세요
#     # 다른 옵션들...
# }
# html_theme_options = {
#     'analytics_id': 'G-XXXXXXXXXX',  #  Provided by Google in your dashboard
#     'analytics_anonymize_ip': False,
#     'logo_only': False,
#     'prev_next_buttons_location': 'bottom',
#     'style_external_links': False,
#     'vcs_pageview_mode': '',
#     #'style_nav_header_background': html_css_files,
#     'flyout_display': 'hidden',
#     'version_selector': True,
#     'language_selector': True,
#     # Toc options
#     'collapse_navigation': True,
#     'sticky_navigation': True,
#     'navigation_depth': 4,
#     'includehidden': True,
#     'titles_only': False
# }

autodoc_member_order = 'bysource'

# import os
# import sys
# # docs/source에서 두 단계 올라간 후 src 폴더 추가
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'Zumi_AI')))

import os
import sys

os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

# 현재 conf.py 파일이 있는 디렉토리
current_conf_dir = os.path.abspath(os.path.dirname(__file__))
print(f"DEBUG: current_conf_dir = {current_conf_dir}")

# docs/source에서 두 단계 올라간 후 Zumi_AI 폴더 추가
# 예상 경로: your_project_root/Zumi_AI
#target_path = os.path.abspath(os.path.join(current_conf_dir, '..', '..', 'Zumi_AI'))
target_path = os.path.abspath(os.path.join(current_conf_dir, '..', '..', '..','Zumi_AI'))
sys.path.insert(0, target_path)

print(f"DEBUG: Zumi_AI target_path added to sys.path = {target_path}")
print(f"DEBUG: sys.path after insert = {sys.path}")