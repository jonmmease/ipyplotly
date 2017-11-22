# Overview
I had the opportunity to show Chris from Plotly by ipyplotly 
library and he was super excited and thought it was amazing.  He is really 
interested in folding this functionality into plotly.py and he could assign 
someone to work with me on this.

Ideally, the code gen objects would be backwards compatible with the existing 
graph_objs objects.

## Making compatible with graph_objs
To accomplish this:
 - My CompoundDatatype need to implement the dict magic methods that are in 
 use in plotly.    
 - I would add a ListDatatype that would replace my use of tuples for 
 sequence types. This would be for lists of CompoundDatatypes, not for use in
 _data.  It would be a list subclass and implement validated item 
 assignment, append, and extend methods. These would notify parent object.  
 Mutation operations that don't map well to plotly would result in resetting
 the whole sequence (del, insert, update)

- Figure also needs to implement dict magic methods for `['data']` and 
`['layout']` properties


I like all of these changes, whether or not ipyplotly ends up in plotly.py

## Add error better error messages for non-existant properties. 
When compound object receives unsupported property in constructor or on 
property assignment I should display the docstring property information. 

## Breaking changes
I'm not a fan of graph_objs as the package and the current predefined types 
are all direclty under gothe graph_objs package. I like my layout of 
    - datatypes
        - Figure/Layout
        - trace
            - area
            - scatter
        - layout
            -

## Graph obj summary
I think I could make my objects duck-type compatible with graph_objs. But I 
would want to keep my package structure.  I could test this by making sure 
dash can use my objects directly in place of graph_objs.


## Support frames + cycling through animations
My figure would need to support frames since the current figure does, but 
frames are hard in my use case because I need to keep all of the properties 
synced up on the Python side. Even so, I think this might be possible. 

Sketch: Each JS view gets its own uid an construction time. I listen for 
animation events on JS side, and send then to Python with view uid. These get 
sent back to JS side as animate commands with originating figure uid. 
Originating view ignores the command, other views apply the animation command 
immediately.

I think that actually might be enough to get animation working and in sync. 


## Features to incorporate
 - save to standalone html
 - get_figure from plotly url
 - publish figure to plotly acount
 
 
## What it could replace
 - plotly.graph_objs
 - offline iplot/plot
 - online iplot (becomes get_figure and widget plot)
 - iplot (plotly.offline and online)


## Other stuff
 - grid/dashboard/presentation_objs
 - plotly.plotly credentials and endpoint interfaces
 - creating and writing to streams


# My TODO
 1) Submit IP disclosure and public release request this week
 2) Write list subclass for compound sequences
 3) Add extra dict interface methods 
 4) Add frames support
 5) Continued testing


I'll get 2-4 and some of 5 done by the time 1 is finished. Then I'll reach 
out the Chris again, with code to share, and try to meet with the Plotly team
 to hash out a plan for bringing this together with plotly.py.  Maybe I'll 
 even meet up with them in Montreal.
