WIP
===
Not ready for general use.

ipyplotly
=========

A pythonic plotly API and ipywidget for use in the Jupyter Notebook

Installation
------------

For a development installation (requires npm),

    $ git clone https://github.com/jmmease/ipyplotly.git
    $ cd ipyplotly
    $ pip install -e .
    $ pip install yapf
    $ python setup.py codegen
    $ jupyter nbextension enable --py widgetsnbextension
    $ jupyter nbextension install --py --symlink --sys-prefix ipyplotly
    $ jupyter nbextension enable --py --sys-prefix ipyplotly

Python Versions
---------------
 - Usage requires Python >= 3.5
 - Development requires Python >= 3.6
