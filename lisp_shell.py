from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.document import Document
from prompt_toolkit.styles import Style
from interpreter import interpret
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.clipboard import ClipboardData

# 定义 Scheme 关键字
scheme_keywords = [
    'if', 'begin', 'cond', 'lambda', 'define', 'set!', 'quote',
    'car', 'cdr', 'list', 'and', 'or'
]
SPACENUM = 2

class DynamicKeywordCompleter(Completer):
    def __init__(self, keywords):
        self.keywords = keywords
        self.additional_keywords = set()

    def update_keywords(self, new_keywords):
        self.additional_keywords.update(new_keywords)

    def get_completions(self, document, complete_event):
        word_before_cursor = document.get_word_before_cursor()
        if not word_before_cursor:
            return  # 如果没有输入内容，不生成补全建议
        for keyword in sorted(self.keywords | self.additional_keywords):
            if keyword.startswith(word_before_cursor):
                yield Completion(keyword, start_position=-len(word_before_cursor))

# 创建关键字补全器
keyword_completer = DynamicKeywordCompleter(set(scheme_keywords))

# 创建键绑定
bindings = KeyBindings()
parentheses_added = False

@bindings.add('(')
def _(event):
    """在输入左括号时，自动补全右括号并将光标置于两者之间。"""
    if parentheses_added:
        event.current_buffer.insert_text('()')
        event.current_buffer.cursor_left()
    else:
        event.current_buffer.insert_text('(')
    


# 检查括号是否平衡
def check_parentheses_balance(text):
    stack = []
    for char in text:
        if char == '(':
            stack.append(char)
        elif char == ')':
            if not stack:
                return False
            stack.pop()
    return len(stack) == 0

@bindings.add('enter')
def _(event):
    document = event.current_buffer.document
    buffer = event.current_buffer
    if buffer.complete_state:
        # 在补全状态下按下回车键时，完成补全并终止输入。
        current_completion = buffer.complete_state.current_completion
        if current_completion:
            buffer.apply_completion(current_completion)
    else:
        # 在非末尾输入换行或括号不均衡时不终止输入。
        balance = check_parentheses_balance(event.current_buffer.document.text)
        if balance and document.is_cursor_at_the_end:
            event.current_buffer.validate_and_handle()
        # 保持缩进等级，但在新表达式时不缩进
        else:
            last_line = document.text_before_cursor.splitlines()[-1]
            indent_level = len(last_line) - len(last_line.lstrip())
            if ')' in document.text_after_cursor:
                buffer.insert_text('\n' + ' ' * indent_level)
            else:
                buffer.insert_text('\n')

@bindings.add('c-i')
def _(event):
    """按下 Tab 键时提供补全选项，并以多列形式显示。"""
    buffer = event.current_buffer
    document = buffer.document
    # 调用补全器获取补全选项
    completions = list(buffer.completer.get_completions(document, event))
    
    if completions:
        # 如果有补全选项，则显示或切换选择
        if buffer.complete_state:
            buffer.complete_next()
        else:
            buffer.start_completion(select_first=False)


def get_space_by_cursor(document:Document):
    before_cursor=document.current_line_before_cursor
    if before_cursor.isspace():
        # 获取当前行的缩进
        return len(document.current_line)-len(document.current_line.lstrip())
    elif before_cursor == '':
        return 0
    else:
        return None
    
@bindings.add('space')
def _(event):
    buffer = event.current_buffer
    document = buffer.document
    # 如果当前行为空或者只包含空白字符，则对齐到 SPACENUM 的倍数
    if  (current_indent:=get_space_by_cursor(document)) is not None:
        extra_spaces = SPACENUM - (current_indent % SPACENUM)
        buffer.cursor_position -= len(document.current_line_before_cursor)
        buffer.cursor_position += current_indent
        buffer.insert_text(' ' * extra_spaces)
    else:
        buffer.insert_text(' ')

# backspace删除行首空格
@bindings.add('c-h')
def _(event):
    buffer = event.current_buffer
    document = buffer.document

    if current_indent:=get_space_by_cursor(document):
        previous_indent = current_indent-1
        # 找到上面小于当前缩进的行
        for i in document.text_before_cursor.splitlines()[-2::-1]:
            previous_indent = len(i)-len(i.lstrip())
            if previous_indent < current_indent:
                break
        spaces_to_remove = current_indent - previous_indent
        # 将光标移动到行首非空白字符后删除
        buffer.cursor_position -= len(document.current_line_before_cursor)
        buffer.cursor_position += current_indent
        
        buffer.delete_before_cursor(spaces_to_remove)
    else:
        buffer.delete_before_cursor(1)

def interactive_shell():
    input_counter = 1
    style = Style.from_dict({
        'input': 'ansigreen',
        'output': 'ansired',
    })

    session = PromptSession(
        history=InMemoryHistory(),
        auto_suggest=AutoSuggestFromHistory(),
        completer=keyword_completer,
        key_bindings=bindings,
        multiline=True,
        style=style
    )
    left = ''
    while True:
        try:
            text = session.prompt(HTML(f'<input>In [{input_counter}]:</input>'),default=left.strip())
            if text.lower() in ('exit', 'quit'):
                print("再见!")
                break
            else:
                if text.strip() != '':
                    result, left, env_variable = interpret(text + ' ',input_counter)  # 需要加一个空白字符，将最后一个字符串解析出来
                    if isinstance(result, str):
                        print_formatted_text(HTML(f'<output>Out[{input_counter}]:</output>'), style=style,end='')
                        print(f'{result}\n')
                    #根据环境 更新关键字补全器
                    keyword_completer.update_keywords(env_variable)
                    input_counter += 1
                continue

        except KeyboardInterrupt:
            continue

        except EOFError:
            confirm = input("Do you really want to exit ([y]/n)? ")
            if confirm.lower() in ['y', 'yes', '']:
                break
            else:
                continue

if __name__ == '__main__':
    interactive_shell()
