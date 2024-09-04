from typing import Generator, Union, TypeAlias
from analyze_eval import * 
from fractions import Fraction

def interpret(
    source: str, time: int, max_in: int = 100, eval_time: int|float  = 1
) -> tuple[str|None, str, set[str]]:
    """
    解释器入口:time为当前shell输入次数,max_in为最大输入长度,eval_time为最大运行次数
    返回值为:结果,剩余输入,当前环境
    """
    strgen = StrGen(source, max_in)
    tokengen = TokenGen(strgen, time)
    try:
        i=0
        while i<eval_time:
            try:
                exp=GenExp(tokengen)
            except EndOfSource:
                # 表达式全部运行结束
                break
            result=eval(analyze(exp))
            i+=1
        
        left=find_left(tokengen,source)
        if result is not None:
            return str(result),left,set(run_env.keys())
        else:
            return None,left,set(run_env.keys())

    except InterpretError as result:
        result.display()
        if isinstance(result,ExpError):
            return None,'',set(run_env.keys())
        else:
            left=find_left(tokengen,source)
            return None,left,set(run_env.keys())

def find_left(tokengen:Generator[Token,None,None],source:str)->str:
    try:    
        where=next(tokengen).where
        return source[where:]
    except StopIteration:
        return ''


def StrGen(source: str, max_in: int) -> Generator[str, None, None]:
    """将源字符串转换为最大长度为max_in的字符串生成器"""
    start = 0
    while start < len(source):
        yield source[start : start + max_in]
        start += max_in


def TokenGen(
    strgen: Generator[str, None, None], time: int
) -> Generator[Token, None, None]:
    """读取字符串生成器，生成Token"""
    col, line = -1, 1
    pending = ""
    finished = []
    where = -1
    for string in strgen:
        for i in string:
            where+=1
            if i == "\n":
                line += 1
                col = -1
            else:
                col += 1
            # 分割符
            if i in {"(", ")", " ", "\n", "'"}:
                if pending:
                    finished.append(
                        Token(pending, Location(line, col - len(pending), time),where-len(pending))
                    )
                    pending = ""

                if i in {"(", ")", "'"}:
                    finished.append(Token(i, Location(line, col, time),where))

            else:
                pending += i

        yield from finished

        finished = []
    if pending:
        yield Token(pending, Location(line, col - len(pending)+1, time),where-len(pending)+1)


def prase_atom(token:Token)->Atom:                 
    try:
        return int(token.value)
    except ValueError:
            try:
                return float(token.value)
            except ValueError:
                try:
                    return float(Fraction(token.value))
                except ValueError:
                    if token.value in {"#t", "#f"}:
                        return (token.value == "#t")
                    else:
                        return Symbol_(token)
                    
def GenExp(tokengen: Generator[Token, None, None],slot:Token|None=None) -> Exp:
    stack: list[Token] = []  # 事实上空间只需要一个Token
    result = None
    # 递归解析,生成一个Exp
    while True:
        try:
            # 从预留槽或token流中取出token
            if slot is not None:
                token=slot
                slot=None
            else:
                token= next(tokengen)
        # 若token生成器结束
        except StopIteration:
            # 若还有左括号未匹配
            if stack:
                raise UnmatchedLeftParenthesis(stack[-1])
            # 括号匹配完毕，正常结束
            else:
                raise EndOfSource()
        # 开始建立Exp
        if token.value == "(":
            # 如果result为None,说明这是第一层括号
            if result is None:
                stack.append(token)
                result=Compound_([],token.location,None)# type:ignore
            else:
            # 如果result不为None,说明这是嵌套括号
            # 将当前token放入预留槽,并递归解析
                result.append(GenExp(tokengen,token))

        elif token.value == ")":
            try:
                # 将result的end位置定义为右括号的位置
                stack.pop()
                result.end=token.location #type:ignore
            # 若没有左括号匹配,说明有右括号多余
            except IndexError:
                raise UnmatchedRightParenthesis(token)

        elif token.value == "'":
            try:
                # 为了支持'(a b c)这种语法糖 将该表达式的前后位置定义为'与最后一个token的位置
                next_token=next(tokengen)
                next_exp=GenExp(tokengen,next_token)
                new_token=Token('quote',token.location,token.where)
                if isinstance(next_exp,Compound_):
                    result=Compound_([Symbol_(new_token),next_exp],token.location,next_exp.end)
                else:
                    result=Compound_([Symbol_(new_token),next_exp],token.location,next_token.location)
                
            except StopIteration:
                raise UnmatchedQuote(token)

        else:
            # 对原子表达式解析  
            if result is None:
                result=prase_atom(token) # type:ignore

            else:
                result.append(prase_atom(token))  # type:ignore

        if not stack:
            break

    return result  # type:ignore


