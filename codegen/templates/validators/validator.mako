<%
from codegen import to_pascal_case
%>

class ${to_pascal_case(name)}Validator(bv.${to_pascal_case(base)}Validator):
    def __init__(self):
        super().__init__(name='${name}',
                         parent_name='${to_pascal_case(parent_name)}',
% for k, v in params.items():
                         ${k}${default_val(v)}${paren_or_comma(loop.last)}
% endfor

<%def name="default_val(v)">\
    %if v != ():
=${repr(v)}\
    %endif
</%def>

<%def name="paren_or_comma(is_last)">\
    %if is_last:
)\
    %else:
,\
    %endif
</%def>