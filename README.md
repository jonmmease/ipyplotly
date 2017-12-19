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
    $ python setup.py codegen
    $ pip install -e .
    $ jupyter nbextension install --py --symlink --sys-prefix ipyplotly
    $ jupyter nbextension enable --py --sys-prefix ipyplotly
