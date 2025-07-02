import os
import sys

sys.path.insert(0, os.path.abspath(".."))

project = "microlens-submit"
copyright = "2025, RGES-PIT"
author = "RGES-PIT"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
}

html_theme = "sphinx_rtd_theme"
html_logo = "_static/rges-pit_logo.png"
html_theme_options = {
    "logo_only": False,
    "display_version": False,
}
html_static_path = ["_static"]

def setup(app):
    app.add_css_file("custom.css")
