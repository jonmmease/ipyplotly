class ${name.title().replace('_', '')}Validator(bv.NumberValidator):
    def __init__(self):
        super().__init__(name='${name}',
                         parent_name='${parent_name}',
                         default=${default},
                         min_val=${min_val},
                         max_val=${max_val},
                         array_ok=${array_ok})