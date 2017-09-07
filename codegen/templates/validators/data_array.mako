class ${name.title().replace('_', '')}Validator(bv.NumberValidator):
    def __init__(self):
        super().__init__(name='${name}',
                         parent_name='${parent_name}')