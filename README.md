ipyplotly
===============================

pythonic plotly API for use in Jupyteer

Installation
------------

To install use pip:

    $ pip install ipyplotly
    $ jupyter nbextension enable --py --sys-prefix ipyplotly


For a development installation (requires npm),

    $ git clone https://github.com/jmmease/ipyplotly.git
    $ cd ipyplotly
    $ pip install -e .
    $ jupyter nbextension install --py --symlink --sys-prefix ipyplotly
    $ jupyter nbextension enable --py --sys-prefix ipyplotly
