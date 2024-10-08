from __future__ import annotations
from typing import NamedTuple, TypeAlias, NoReturn,Any,Iterable,Generator
from collections import UserList, ChainMap,UserString,deque
from abc import ABC, abstractmethod
from abc import ABC, abstractmethod

class LocationInterface(ABC):
    @abstractmethod
    def location_message(self):
        """返回html格式的位置信息"""
        pass
    
class Location(NamedTuple):
    line: int
    col: int
    time: int

class Token(NamedTuple):
    value: str
    location: Location
    where: int #用于指示token在源代码中的位置

Symbol:TypeAlias=UserString

# self.data 存储数据
class Symbol_(UserString,LocationInterface):
    def __init__(self, token: Token):
        super().__init__(token.value)
        self.location = token.location

    def location_message(self):
        return f'Cell<input> In[{self.location.time}], line {self.location.line}, col {self.location.col}</input>\n'

# self.data 存储数据
class Compound(UserList):
    def __init__(self, value:list[Exp]):
        super().__init__(value)

    def __str__(self):
        return f"({' '.join(map(str, self.data))})"
    
    @classmethod
    def raise_error(cls,exp:Compound,message:str|None=None)->NoReturn:
        if message:
            raise LispSyntaxError(f'{cls.__name__} usagefault.\n'+message,exp)
        else:
            raise LispSyntaxError(f'{cls.__name__} usagefault.\n correct usage: {cls.__doc__}',exp)
        
    @classmethod
    def analysis(cls,exp:Compound)->Compound|None:
        return exp
    
    def evaluate(self,env:Environment,exp_queue:list[Exp])->Atom|Environment:
        now_exp = self.data
        if not now_exp:
            return None
        first = eval(now_exp[0],env)
        if not callable(first):
            raise LispTypeError('first element must be a procedure or operator',self)
        
        other = iter(eval(i,env)for i in now_exp[1:])       
        if isinstance(first, Procedure):
            # 过程调用
            if first.need_tail_optimization():
                try:
                    # 捕获过程中的错误
                    env_new,last_body=first(other)
                except Exception as e:
                    if isinstance(e, LispError):
                        # 传递错误，加入调用栈信息
                        raise e(self)
                    else:
                        raise LispProcError(str(e),self) from None
                # 尾递归优化
                exp_queue.insert(0,last_body)
                return env_new
            else:
                other = iter(eval(i,env)for i in now_exp[1:])            
                try:
                    # 捕获过程中的错误
                    return first.no_tail_call(other) 
                except Exception as e:
                    if isinstance(e, LispError):
                        # 传递错误，加入调用栈信息
                        raise e(self)
                    else:
                        raise LispError(str(e),self) from None
        else:
            other = iter(eval(i,env)for i in now_exp[1:])            
            try:
                # 捕获过程中的错误
                return first(other) 
            except Exception as e:
                if isinstance(e, LispError):
                    # 传递错误，加入调用栈信息
                    raise e(self)
                else:
                    raise LispError(str(e),self) from None



class Compound_(Compound,LocationInterface):
    def __init__(self, value: list[Exp] ,front: Location|None=None, end: Location|None=None):
        super().__init__(value)
        self.front = front
        self.end = end

    def location_message(self):
        return (f'Cell<input> In[{self.front.time}]</input>\n'
            f'From <input>line {self.front.line}, col {self.front.col}</input>\n'
            f'To <input>line {self.end.line}, col {self.end.col}</input>\n')
    

Number:TypeAlias=int|float
Atom:TypeAlias=Number|bool|Symbol|None
Exp:TypeAlias=Compound|Atom


class If(Compound):
    """(if <predicate> <consequent> <alternative>)"""
    def __init__(self,condition:Exp, consequence:Exp, alternative:Exp|None):
        self.condition = condition
        self.consequence = consequence
        self.alternative = alternative

    @classmethod
    def analysis(cls,exp:Compound) -> If|None:
        if len(exp) != 3 and len(exp) != 4:
            cls.raise_error(exp)

        condition = analyze(exp[1])
        consequence = analyze(exp[2])
        if len(exp) == 4:
            alternative = analyze(exp[3])
        else:
            alternative = None
        return If(condition, consequence, alternative)
        
    def evaluate(self,env:Environment,exp_queue:list[Exp]):
        if eval(self.condition,env):
            exp_queue.insert(0,self.consequence)
        else:
            exp_queue.insert(0,self.alternative)
        
    def __str__(self):
        return f"(if {self.condition} {self.consequence} {self.alternative})"
        
class Begin(Compound):
    """(begin <expression1> <expression2> ... <expressionN>)"""
    def __init__(self, expressions:list[Exp]):
        self.expressions = expressions

    @classmethod
    def analysis(cls, exp: Compound)->Begin|None:
        if len(exp) < 2:
            cls.raise_error(exp)

        expressions = [analyze(e) for e in exp[1:]]
        return Begin(expressions)

        
    def evaluate(self,env:Environment,exp_queue:list[Exp]):
        for exp in self.expressions[:-1]:
            eval(exp,env)
        # 最后一个表达式加入队列,以便优化尾递归
        exp_queue.insert(0,self.expressions[-1])

    def __str__(self):
        return f"(begin {' '.join(map(str, self.expressions))})"

class Cond(Compound):
    """(cond (<predicate1> <expression1>)
            (<predicate2> <expression2>)
            ...
            (else <expressionN>))"""
    def __init__(self, clauses: list[tuple[Exp, Exp]]):
        self.clauses = clauses

    @classmethod
    def analysis(cls, exp: Compound) -> Cond | None:
        if len(exp) < 2:
            cls.raise_error(exp)

        clauses = []
        for clause in exp[1:]:
            if isinstance(clause, Compound):
                # Check for 'else' clause
                if len(clause) == 2 and isinstance(clause[0], Symbol) and clause[0] == 'else':
                    if exp.index(clause) != len(exp) - 1:  # Ensure 'else' is the last clause
                        cls.raise_error(clause,"Else clause must be the last one.")
                    expression = analyze(clause[1])
                    clauses.append((None, expression))  # None signifies the 'else' clause
                    break  # Stop further clause processing after 'else'
                elif len(clause) == 2:
                    predicate = analyze(clause[0])
                    expression = analyze(clause[1])
                    clauses.append((predicate, expression)) #type:ignore
                else:
                    cls.raise_error(clause)
            else:
                cls.raise_error(clause)
        return Cond(clauses)#type:ignore

    def evaluate(self, env: Environment, exp_queue: list[Exp]):
        for predicate, expression in self.clauses:
            if predicate is None or eval(predicate, env):  # 'None' is for 'else' case
                return exp_queue.insert(0, expression)
        return None
        
    def __str__(self):
        result = '(cond '
        for i in self.clauses:
            result += f' ({i[0] or "else"} {i[1]})'  # Use 'else' for the 'None' predicate
        return result + ')'

    
class Lambda(Compound):
    """(lambda (parameter1 parameter2 ... parameterN) body)"""
    def __init__(self,parameters:list[Symbol], body:list[Exp]):
        self.parameters = parameters
        self.body = body

    @classmethod
    def analysis(cls, exp:Compound)->Lambda|None:
        if len(exp) < 3 or not isinstance(exp[1], Compound):
            cls.raise_error(exp)

        parameters = []
        for i in exp[1]:
            if isinstance(i, Symbol):
                parameters.append(i)
            else:
                cls.raise_error(i, 'parameter must be a symbol')     
        body = [analyze(i) for i in exp[2:]]
        if body==[]:
            cls.raise_error(exp,'function body is empty')
        return Lambda(parameters, body)
        
    def evaluate(self,env:Environment,exp_queue:list[Exp]):
        return Procedure(self.parameters, self.body, env)
    
    def __str__(self):
        return f"(lambda ({' '.join(map(str, self.parameters))}) {' '.join(map(str, self.body))})"

class Define(Compound):
    """(define variable-name value)
       (define (function-name parameter1 parameter2 ... parameterN) body)"""
    def __init__(self,name:Symbol,value:Exp):
        self.name = name
        self.value = value

    @classmethod
    def analysis(cls, exp: Compound)->Define|None:
        if isinstance(exp[1], Symbol):
            if len(exp) == 3:
                value = analyze(exp[2])
                return Define(exp[1], value)
            else:
                cls.raise_error(exp)
        else:
            name = exp[1][0]
            if not isinstance(name, Symbol):
                cls.raise_error(exp,'name must be a symbol')
            parameters = []
            for i in exp[1][1:]:
                if isinstance(i, Symbol):
                    parameters.append(i)
                else:
                    cls.raise_error(exp,'parameter must be a symbol')
            body = [analyze(i) for i in exp[2:]]
            if body==[]:
                cls.raise_error(exp,'function body is empty')
            return Define(name, Lambda(parameters, body))
    
    def evaluate(self, env: Environment, exp_queue: list[Exp]):
        env[str(self.name)] = eval(self.value, env)
        return None

    def __str__(self):
        if isinstance(self.value, Lambda):
            return f"(define ({self.name} {' '.join(map(str, self.value.parameters))}) {' '.join(map(str, self.value.body))})"
        else:
            return f"(define {self.name} {self.value})"
    
class Set(Compound):
    """(set! variable new-value)"""
    def __init__(self,variable:Symbol, value:Exp):
        self.variable = variable
        self.value = value

    @classmethod
    def analysis(cls, exp:Compound)->Set|None:
        if len(exp) != 3:
            cls.raise_error(exp)
        variable = exp[1]
        if not isinstance(variable, Symbol):
            cls.raise_error(exp,'variable must be a symbol')
        value = analyze(exp[2])
        return Set(variable, value)
        
    def evaluate(self, env: Environment, exp_queue: list[Exp]):
        try:
            env.change(self.variable, eval(self.value, env))
        except KeyError:
            raise LispNameError(f'undefined variable {self.variable}',self)

    def __str__(self):
        return f"(set! {self.variable} {self.value})"

class Quote(Compound):
    """(quote <expression>)"""
    def __init__(self,value:Exp):
        self.value = value

    @classmethod
    def analysis(cls, exp: Compound) -> Quote | None:
        if len(exp) != 2:
            cls.raise_error(exp)
        return Quote(exp[1])
    
    def evaluate(self, env: Environment, exp_queue: list[Exp]):
        return self.value
    
    def __str__(self):
        return f"(quote {self.value})"

class Return(Compound):
    """(return <expression>)"""
    def __init__(self,value:Exp):
        self.value = value

    @classmethod
    def analysis(cls, exp: Compound) -> Return | None:
        if len(exp) != 2:
            cls.raise_error(exp)
        return Return(exp[1])
    
    def evaluate(self, env: Environment, exp_queue: list[Exp]):
        return eval(self.value, env)
    
    def __str__(self):
        return f"(return {self.value})"

COMPOUND:dict[str,type[Compound]]= {'if': If, 'begin': Begin, 'cond': Cond, 'lambda': Lambda, 'define': Define, 'set!': Set, 'quote': Quote, 'return': Return}
def analyze(exp: Exp) -> Exp:
    if isinstance(exp, Compound):
        if isinstance(exp[0], Symbol) and exp[0] in COMPOUND:
            return COMPOUND[str(exp[0])].analysis(exp)
        if isinstance(exp, Compound_):
            return Compound_([analyze(i) for i in exp],exp.front,exp.end)
        else:
            return Compound([analyze(i) for i in exp])
    else:
        return exp


#####################################################################################################
#                                    Eval and Environment                                           #
#####################################################################################################
import operator as op
import math
class Environment(ChainMap):
    def change(self, key: Symbol, value: object) -> None:
        for map in self.maps:
            if key in map:
                map[key] = value
                return
        raise KeyError(key)


class Procedure:
    def __init__(
        self, parms: list[Symbol], body: list[Exp], env: Environment
    ):
        self.parms = parms
        self.body = body
        self.definition_env = env

    def application_env(self, args:list[Exp]) -> Environment:
        local_env = dict(zip(self.parms, args))
        return Environment(local_env, self.definition_env)

    def __call__(self, args: Generator[Exp,None,None]):
        args_list = list(args)
        if len(args_list) != len(self.parms):
            raise LispTypeError(f'error arguments number')
        
        env = self.application_env(args_list)# type:ignore
        for exp in self.body[:-1]:
            eval(exp, env)
        return (env, self.body[-1])
    
    def no_tail_call(self, args: Generator[Exp,None,None]):
        args_list = list(args)
        if len(args_list) != len(self.parms):
            raise LispTypeError(f'error arguments number')
        
        env = self.application_env(args_list)
        for exp in self.body:
            result=eval(exp, env)
        return result
    
    def need_tail_optimization(self):
        return not isinstance(self.body[-1], Return)
        
    
    def __str__(self) -> str:
        return f'<procedure>'

def all_float():
    while True:
        yield (float,int)

def one_list():
    yield Compound
    while True:
        yield object

def one_list_end():
    yield object
    yield Compound

def all_object():
    while True:
        yield object

def list_int_object():
    yield Compound
    yield int
    yield object

class Operator:
    def __init__(self,op,num:tuple[int|None,int|None],type_gen=all_object) -> None:
        self.op = op
        self.num = num
        self.type_gen = type_gen

    def __call__(self, args:Generator[Exp,None,None]) -> Any:
        args_list=list(args)
        length = len(args_list)
        if self.num[0] is not None and length < self.num[0]:
            raise LispTypeError(f'error arguments number')
        if self.num[1] is not None and length > self.num[1]:
            raise LispTypeError(f'error arguments number')
        return self.operate(args_list)# type:ignore
    
    def no_tail_call(self, args:Generator[Exp,None,None]) -> Any:
        return self(args)

    def __str__(self) -> str:
        return f'<operator:{self.op.__name__}>'

    def __repr__(self) -> str:
        return f'{self.__class__}:{self.op.__name__}'
    
class Sequential_Mixin():
    """
    (+ 1 2 3)=> result=1+2,result=result+3
    最少一个参数
    """
    def operate(self, args):
        type_gen = self.type_gen()
        result = args[0]
        if not isinstance(result, next(type_gen)):
            raise LispTypeError(f'error type')
        for arg in args[1:]:
            if not isinstance(arg, next(type_gen)):
                raise LispTypeError(f'error type')
            result = self.op(result, arg)
        return result

class Comparative_mixin():
    """(> 1 2 3)=> and( 1>2, 1>3 )"""
    def operate(self, args):
        type_gen = self.type_gen()
        first = args[0]
        if not isinstance(first, next(type_gen)):
            raise LispTypeError(f'error type')
        for arg in args[1:]:
            if not isinstance(arg, next(type_gen)):
                raise LispTypeError(f'error type')
            if not self.op(first, arg):
                return False
        return True

class List_mixin():
    """(list 1 2 3)=> list(1,2,3)"""
    def operate(self, args):
        type_gen = self.type_gen()
        for arg in args:
            if not isinstance(arg, next(type_gen)):
                raise LispTypeError(f'error type')
        return self.op(args)
    
class One_mixin():
    """(abs 1)=> abs(1)"""
    def operate(self, args):
        type_gen = self.type_gen()
        result = None
        for arg in args:
            if not isinstance(arg, next(type_gen)):
                raise LispTypeError(f'error type')
            result = self.op(arg)
        return result
    
class And_OP(Operator):
    def __init__(self):
        pass
    
    def __call__(self, args:Generator[Exp,None,None]) -> Any:
        return all( arg for arg in args)

    def __str__(self) -> str:
        return f'<operator:and>'
    
    def __repr__(self) -> str:
        return str(self)

class Or_OP(Operator):
    def __init__(self):
        pass

    def __call__(self, args:Generator[Exp,None,None]) -> Any:
        return any(arg for arg in args)
    
    def __str__(self) -> str:
        return f'<operator:and>'
    
    def __repr__(self) -> str:
        return str(self)

class Map_OP(Operator):
    def __init__(self):
        pass

    def __call__(self, args:Generator[Exp,None,None]) -> Any:
        args_list= list(args)
        if not callable(args_list[0]):
            raise LispTypeError(f'first element must be a procedure or operator')
        for arg in args_list[1:]:
            if not isinstance(arg, Compound):
                raise LispTypeError(f'map function must be operate on the list')
        # 函数作用在参数迭代器上
        func=args_list[0]
        if isinstance(func, Procedure):
            return Compound(map(func.no_tail_call,(iter(i) for i in zip(*args_list[1:]))))
        else:
            return Compound(map(args_list[0],(iter(i) for i in zip(*args_list[1:]))))
    
    def __str__(self) -> str:
        return f'<operator:map>'
    
    def __repr__(self) -> str:
        return str(self)

class Func():
    @staticmethod
    def set_ref(arg:list):
        arg[0][arg[1]]=arg[2]

class S_OP(Operator,Sequential_Mixin):
    pass

class C_OP(Operator,Comparative_mixin):
    pass

class L_OP(Operator,List_mixin):
    pass

class O_OP(Operator,One_mixin):
    pass


def standard_env() -> Environment:
    env = Environment()
    # env.update(vars(math))   # sin, cos, sqrt, pi, ...
    env.update({
            '+': S_OP(op.add,(2,None),all_float),
            '-': S_OP(op.sub,(2,None),all_float),
            '*': S_OP(op.mul,(2,None),all_float),
            '/': S_OP(op.truediv,(2,None),all_float),
            'quotient': S_OP(op.floordiv,(2,None),all_float),
            '>': C_OP(op.gt,(2,None),all_float),
            '<': C_OP(op.lt,(2,None),all_float),
            '>=': C_OP(op.ge,(2,None),all_float),
            '<=': C_OP(op.le,(2,None),all_float),
            '=': C_OP(op.eq,(2,None),all_float),
            'abs': O_OP(abs,(1,1),all_float),
            'append': S_OP(op.add,(2,None),one_list),
            'car': O_OP(lambda x: x[0],(1,1),one_list),
            'cdr': O_OP(lambda x: Compound(x[1:]),(1,1),one_list),
            'eq?': C_OP(op.is_,(2,None)),
            'equal?': C_OP(op.eq,(2,None)),
            'length': O_OP(len,(1,1),one_list),
            'list': L_OP(Compound,(0,None)),
            'list?': C_OP(lambda x: isinstance(x, Compound),(1,None)),
            'max': L_OP(max,(1,None),all_float),
            'min': L_OP(min,(1,None),all_float),
            'not': O_OP(lambda x: not x,(1,1)),
            'empty?': O_OP(lambda x: x == [],(1,1),one_list),
            'number?': C_OP(lambda x: isinstance(x, (int, float)),(1,None)),
            'procedure?': C_OP(callable,(1,None)),
            'symbol?': C_OP(lambda x: isinstance(x, Symbol),(1,None)),
            'cons': S_OP(lambda x,y: Compound([x]+y),(2,2),one_list_end),
            'map': Map_OP(),
            'and': And_OP(),
            'or': Or_OP(),
            'set-ref!': L_OP(Func.set_ref,(3,3),list_int_object),
    })
    return env

run_env:Environment=standard_env()

def eval(exp: Exp,env=run_env) -> Atom:
    # 用于优化尾递归
    result=None
    exp_queue=[exp]
    while exp_queue:
        exp=exp_queue.pop(0)
        if isinstance(exp, Compound):
            result= exp.evaluate(env,exp_queue)
            # 尾递归优化，传递的是新的环境
            if isinstance(result, Environment):
                env=result
        else:
            if isinstance(exp, Symbol):
                try:
                    result= env[exp]
                except KeyError:
                    raise LispNameError(f'undefined variable {exp}',exp)
            else:
                result= exp #type:ignore
    return result #type:ignore
    
#####################################################################################################
#                                             Error                                                 #
#####################################################################################################

from prompt_toolkit import HTML
from prompt_toolkit.shortcuts import print_formatted_text
from lisp_shell_config import ERROR_STYLE
# 定义样式
style = ERROR_STYLE


class InterpretError(Exception):
    """Generic interpreter exception."""
    def display(self):
        if isinstance(self.output, str):
            print_formatted_text(HTML(self.output), style=style)
        if isinstance(self.output, deque):
            traceback_info=(f"<error>---------------------------------------------------------------------------</error>\n"
                            f"<error>{self.__class__.__name__}</error>                                 Traceback (most recent call last)\n")
            print_formatted_text(HTML(traceback_info), style=style)
            for i in self.output:
                print_formatted_text(HTML(i), style=style)

        

    
class ExpError(InterpretError):
    """Appear when generating expression"""
    def __init__(self, message,token:Token):
        self.message=message
        self.location=token.location
        self.output=(
            f'Cell<input> In[{self.location.time}], line {self.location.line}, col {self.location.col}</input>\n'
            f'  <keyword>{token.value}</keyword>\n'
            f'<error>{self.__class__.__name__}:</error>{self.message}\n'
        )

class EndOfSource(Exception):
    pass

class UnmatchedLeftParenthesis(ExpError):
    """Appear when there is an unmatched left parenthesis"""
    def __init__(self, token:Token):
        super().__init__('Unmatched left parenthesis',token)

class UnmatchedRightParenthesis(ExpError):
    """Appear when there is an unmatched right parenthesis"""
    def __init__(self, token:Token):
        super().__init__('Unmatched right parenthesis',token)

class UnmatchedQuote(ExpError):
    """Appear when there is nothing after quote"""
    def __init__(self, token:Token):
        super().__init__('Nothing after quote',token)

class LispError(InterpretError):
    """An generic error after Exp generation."""

    def __init__(self, message: str='', exp: Exp=None):
        self.message = message
        self.output:deque[str] = deque()
        now=''
        if isinstance(exp,LocationInterface):
            now=exp.location_message()
        now += (f"  <keyword>{str(exp)}</keyword>\n"
                f"<error>{self.__class__.__name__}:</error>{self.message}\n")
        self.output.appendleft(now)

    def __call__(self, exp: Exp):
        """add call stack information"""
        now=''
        if isinstance(exp,LocationInterface):
            now = exp.location_message()
        now+=f"  <keyword>{str(exp)}</keyword>\n"
        self.output.appendleft(now)
        return self


class LispSyntaxError(LispError):
    """Appear when there is a syntax error"""
    pass

class LispTypeError(LispError):
    """Appear when there is a type error or a number of arguments error"""
    pass

class LispProcError(LispError):
    """Appear when eval a procedure"""
    pass

class LispNameError(LispError):
    """Appear when can't find that name in the environment"""
    pass