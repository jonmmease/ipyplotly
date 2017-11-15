ipyplotly
===============================

pythonic plotly API for use in Jupyteer

Installation
------------

Conda for dependencies and then pip

    $ conda install "pandas>=0.20" "numpy>=1.13" "pillow>=4.2" "notebook>=5" "plotly>=2.1" cairo>=1.14" 
    $ conda install -c conda-forge "cairosvg>=2.0.0rc6" "ipywidgets>=7.0"


jupyter nbextension enable --py --sys-prefix widgetsnbextension
jupyter nbextension enable --py --sys-prefix ipyplotly

To install use pip:

    $ pip install ipyplotly
    $ jupyter nbextension enable --py --sys-prefix ipyplotly


For a development installation (requires npm),

    $ git clone https://github.com/jmmease/ipyplotly.git
    $ cd ipyplotly
    $ pip install -e .
    $ jupyter nbextension install --py --symlink --sys-prefix ipyplotly
    $ jupyter nbextension enable --py --sys-prefix ipyplotly
