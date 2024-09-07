from prompt_toolkit.styles import Style
scheme_keywords = [
    'if', 'begin', 'cond', 'lambda', 'define', 'set!', 'quote',
    'car', 'cdr', 'list', 'and', 'or', 'return'
]
SPACENUM = 2
PARENTHESES_ADDED = False
SHELL_STYLE=Style.from_dict({'input': 'ansigreen', 'output': 'ansired'})
MAX_IN=100
EVAL_TIME=1
ERROR_STYLE=Style.from_dict({'input': 'ansigreen','keyword': 'ansiyellow','error': 'ansired',})