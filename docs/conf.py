import os
import sys
sys.path.insert(0,os.path.abspath(".."))

author="Krzesimir Hyżyk"
autodoc_member_order="groupwise"
copyright="2025, Krzesimir Hyżyk"
extensions=["sphinx.ext.autodoc"]
html_theme="sphinx_rtd_theme"
project="LEDSign"
rst_prolog="""
.. role:: python(code)
   :language: python
   :class: highlight
"""
