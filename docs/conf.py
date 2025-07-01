import os
import sys
sys.path.insert(0, os.path.abspath('..'))

project = 'microlens-submit'
copyright = '2025, RGES-PIT'
author = 'RGES-PIT'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
]

autodoc_default_options = {
    'members': True,
    'undoc-members': True,
}

html_theme = 'sphinx_rtd_theme'

