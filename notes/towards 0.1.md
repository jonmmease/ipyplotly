# Towards an initial release of ipyplotly 0.1

Some notes on the things that should happen in preparation for a public 0.1 release 


## Features

### Misc
- Append valid type description to property doc strings (e.g. valid colors, min/max, etc.). This is what you get when
 you call fig.layout.xaxis.range? from the notebook

- Restrict button/slider methods to restyle / relayout  / update

- Add index option to `fig.add_trace` methods (default to append to end)

- HTML export without plotly.py (Shouldn't be a runtime dependency)

- Jupyterlab support (with mirror cells)

### Plotly.update support
- Add update() method and js event handling (for use with buttons/sliders)

- Add `with fig.batch_update():` context manager construct: Intercept trace/layout property assignments and execute 
single `update` command on exit. 

### Basic animation support
- Add fig.animate(state, animationOpts) method
    - Support animating to a new single state with easing, apply updates to python model and js model explicitly, notify views with `Plotly.animate()` command.
    - Don't support animating to frames or sequences of states

- Add `with fig.batch_animate(animationOpts):` context manager. Intercept trace/layout property assignments and 
execute single `animate` command on exit.

- Frames are not supported: Keeping multiple views in sync that can each animate individually sounds awful 
(infeasible?). With this
 library you accomplish this using individual animate commands from the python side. Driven by ipywidgets. 

### Binary protocol
- Support typed 1d arrays in model. 1d numpy arrays of primitives on Python side to/from typed arrays on JS side.  
Views convert them 
into untyped arrays during clone process in render() and during the create_delta methods
- Add custom ipywidget serializer to each of the dict properties
- Brushing callback returns typed selection array.
- Optional, all data_array / arrayOk properties accept standard lists or numpy arrays


## Testing

### Python Unit testing
 - Base Validators
 - Dictionary manipulation
 - Base Datatypes
    - Generate expected plotly commands
    - Respond appropriately to incoming messages
    - Orphan data handling 
    
 - Codegen classes. Import everything, construct all Datatypes. Inspect docstrings.
 - Plotly examples. Implement as Figure constructor and iteratively. Compare to_dict() data with plotly.py result.
 - on_change events triggered by restyle and property assignment 
 - png export image comparison regression tests (inherantly tests html export as well)

### Javascript
 - Refactor out widget independent javascript functions
 - Unit test widget independent object code (merging, cloning, etc.) without the notebook

### Integration
 - Execute code (Either entire file or cell by cell)
 - Notebook tests with selenium
    - Test default properties that flow back from JS side (xaxis.range, removing autorange, marker color, etc)
    - on_change events triggered by plot interaction (Click zoom to change tool, pan to change x/y range)
    - Test selection, hover, click, etc.
    - Maybe have assert logic statements in cells at the botton of notebook in rawnbconvert type cells. After running 
    full notebook these cells are converted to code an executed one at a time as individual test cases. Or this logic
     happens over jupyter_client inside pytest test functions. 
    
 - Implementation notes:
   - Launch jupyter notebook in a setup fixture 
   - Copy fresh version of notebook
   - Use selenium to open notebook and start kernel
   - Execute %connect_info in first cell. Use selenium to get the resulting text
   - Use jupyter_client to connect to same kernel over zmq.
   
   - pytest the state of the Python Figure object over the jupyter_client interface as cells are executed with selenium
   - Get full data from plotly figure over selenium by executing `document.getElementsByClassName('js-plotly-plot')[0]._fullData`
     per view.
   - Data from Javascript model by running ipywidgets.embed.embed_data() over jupyter_client
   - Data from python model by running fig._data over jupyter client
   - Write helpers to check equality of all three in one step
   
### CI
 - Travis, AppVeyor, Readthedocs,
 - pip, conda channel

## Documentation

readthedocs website 
  
  - Examples with published notebooks using nbsphinx.  Notebooks available as examples for download as well. 
Widgets displayed inline notebooks.

  - Full api documented from codegen source
  
  - Conversion of plotly.py notebook examples, well organized. 
  
  - Goals / Feature overview: Beautiful wrapper to a great plotting library.
  
  - Comparisons to Bokeh, bqPlot, ...
  
  - Comparison for MATLAB users
  
  - Integration examples: plotly.py, cufflinks, dash, plotly matlab, matplotlib,


## Promotion
Talk and 0.1 announcement at PlotCon 2018 and JupyterCon 2018


## Plotly issues
Issues to raise with the core Plotly project at some point

 - Background image flicker on change
 - Zoom window slowdown 
 - update/animate events
 - scattergl zoom relayout
 - parcoords restyle constraintrange