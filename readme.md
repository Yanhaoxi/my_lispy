## 前言
在看完《流畅的python》lispy(一个python写的lisp语言解释器)后，对lisp语言突然饶有兴趣，让我想到了之前那时觉得并不好看的《计算机程序的构造和解释》，于是捡着感兴趣的部分（前四章）了解了下lisp语言设计思想，自己写了一个lisp解释器（虽然一开始以为是一个轻松的工作但是还是踩了不少坑重构了好几次）

# 程序语言的构造与解释
## 程序语言的构造
### EXP
**Exp:TypeAlias=Compound|Atom**
### Atom 原子表达式
#### 符号（Symbol）：
可以作为一个程序对象的别名  
（解释器内的实现：Symbol:TypeAlias=UserString）

#### 数字（Number）：
可以以整数，浮点数，分数的形式输入，这些都可以被解析  
(解释器内的实现：Number:TypeAlias=int|float)

#### 布尔值（Boolean）
```#t```为真，```#f```为假  
0的值与 #f 相等，但是指向的对象不一致  
有：
```
In [1]:(eq? #f 0)
Out[1]:False

In [2]:(equal? #f 0)
Out[2]:True
```
（解释器中为bool类型）

### Compound 列表
用于存储和操作多个元素。列表由一对圆括号括起来，内部的元素用空格分隔，例如：`(1 2 3)`。  
（解释器中由 class Compound(UserList): 实现）
#### 提供的操作接口
- **list** 函数用于返回元素列表。```(list 1 2 3)->(1 2 3)```
- **car** 函数用于返回列表的第一个元素。```(car (1 2 3))->1```
- **cdr** 函数用于返回列表除第一个元素之外的部分，即列表的“尾部”。```(cdr (1 2 3)->(2 3))```
- **set-cdr!** 用于修改列表的 cdr 部分
- **set-car!** 用于修改列表的 car 部分
- **append** 将一个元素放于列表尾端
- **cons** 将一个元素放于列表的尾端
- **empty?** 判断该列表是否具有元素

**注**：本项目没有提供cons生成元组的功能（因为个人觉得list能做到cons所能做到的并且保持高效率，所以该项目不提供该数据结构），本项目中cons传递的参数是一个程序元素和一个列表，并将该元素至于列表首端

#### 列表与表达式
该语言中，表达式也是列表，解释器接受列表并进行运算求值，改变环境，生成对象

### 过程（Procedure）：
接受参数返回结果的函数 **（本项目的实际实现中是将参数作为迭代器进行传递的，这样可以把参数是否直接计算的逻辑延迟到实际执行中，如and,or的最短计算原则依赖此原则实现）**  
（解释器中，用户定义的类型为procedure，内置的过程类型为operator,但是由callable可以作统一判断）
#### 基本过程
语言内置的、无法再进一步分解的最基本的函数，由于基本为一句话函数，所以均**没有尾递归优化**。   
在解释器中对于基本过程主要由两部分构成:
- 具有**operate**方法的Mixin类
- 传入的用于参数检测的生成器函数  
举一个具体的内置基本过程实现的例子：
```python
'+': S_OP(op.add,(2,None),all_float)
# 第一个参数提供了将要被应用的函数
# 第二个参数是参数数量的限制（None是指无上限or下限）
# 第三个参数是用来进行参数检测的生成器函数

class S_OP(Operator,Sequential_Mixin):
    pass

class Operator:
    def __init__(self,op,num:tuple[int|None,int|None],type_gen=all_object) -> None:
        self.op = op
        self.num = num
        self.type_gen = type_gen

    def __call__(self, args:Generator[Exp,None,None]):
        # 进行参数数量的检查
        return self.operate(args_list)

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
```
**注**：and,or由于无需计算所有参数，以及map函数较为复杂（因为为了运行效率和更好的报错信息，map作用的函数是关闭尾递归优化的）他们是直接单独实现的，但是都是operate的子类

在源码的standard_env里记录了所有的内置函数（可见analyze_eval.py文件）

#### 复合过程
由基本过程或其他复合过程通过组合而构成的新的过程（用户定义的都为复合过程）  
**注**：所有的复合过程都是开启了尾递归优化的，但是这使得报错call-stack信息让人摸不着头脑，所以本项目提供了**return**作为关键词，当他位于过程体的最后一句时会关闭尾递归优化

**示例**：   
可以看到在过程 C 没有显式的关闭尾递归优化后，调用帧信息少了一层  
![示例图片1](./png/屏幕截图%202024-09-07%20193941.png)
在关闭c的尾递归优化后  
![示例图片2](./png/屏幕截图%202024-09-07%20194121.png)

### 5. **关键字**
#### 控制流相关
##### if
(if \<predicate\> \<consequent\>\<alternative\>)   
在本解释器中仅仅会去计算符合条件的部分。

##### begin
(begin \<expression1\> \<expression2\> ... \<expressionN\>)  
顺序地执行多个表达式，并返回最后一个表达式的结果。

##### cond
(cond (\<predicate1\> \<expression1\>)  
      (\<predicate2\> \<expression2\>)  
      ...  
      (else \<expressionN\>))  
它会依次检查每个 <predicate>，并执行第一个为真的条件对应的 <expression>。都不满足返回else的内容，没有else即为None。

#### 抽象相关
**注**：这里的变量（name parameter）都应该是symbol
##### lambda
用于创建匿名过程，返回body块中的最后一条语句的值  
(lambda (parameter1 parameter2 ... parameterN)  
   body)

##### define 
在当前环境中给变量或过程绑定上别名
- 定义变量 (define variable-name value)
- 定义函数 (define (function-name parameter1 parameter2 ... parameterN) body)  
  可以看作是 （define function-name (lambda (parameter1 parameter2 ... parameterN) body)）

#### 赋值相关
##### set!
用于改变数据的状态  
(set! variable new-value)  
**注**：不同于define在当前栈帧（环境）如果没有找到Symbol的话会直接创建并赋值，set!会沿着函数的调用栈前向搜索（例如函数体中的set!在该函数体内未找到对应的Symbol则会在函数定义的环境继续寻找，可以类比python的nolocal）直到找到对应Symbol，如果没有则会报错。
##### set-ref!
简单的用于修改列表某项值的函数  
(set-car! list index new-value)

#### 元编程相关
##### quote or '
修饰表达式，使得计算后是表达式本身
比如：（+ 1 2）的含义是3，'(+ 1 2)等价于(quote(+ 1 2))含义是一个列表其中元素分别是 +、1、2  
**注**：一个小的点是'exp实际上是（quote exp）的语法糖，但是由于事实上这个表达式是后面生成的导致不能直接使用左右括号的位置作为该表达式的起始，在实现中我们将```'```与exp末尾的位置作为该表达式的起始位置。

#### 尾递归优化相关
##### return
(return \<expression\>)   
由于用户定义的函数是默认开启尾递归优化的（在本项目中的实现方式是把函数体最后一句重新放回待计算表达式流中，同时更改计算环境为函数体所在环境），return关键字将阻止尾递归优化，使得其恢复正常调用模式。（具体效果可见[示例](#复合过程)）

## 程序语言的解释
### shell
提供类似ipython的交互式输入求值循环  
由于并非本项目核心这里一笔带过，唯一需要提的是该lisp-shell默认一次仅计算一个表达式，剩余的表达式会返回在一下次输出（配置文件在lisp_shell_config.py），shell提供了一些基本的括号平衡检测、关键词补写（根据但当时环境）等功能，由于并非该项目核心，具体实现可见lisp_shell.py

### interpreter
```python
def interpret(source:str,max_in:int=MIX_IN,eval_time:int=EVAL_TIME)->tuple[str,str,set[str]]:
    ...
```
**输入值**
- source:输入来源
- max_in:每次处理source的字符量  
**注**：这是由于本身该shell并不会一次执行完所有的表达式，所以无需一次性读入大量字符
- eval_time:执行次数达eval_time则返回  
**注**：将eval_time扩展为正无穷即可实现对文本的处理，但是本项目未实现，有兴趣可以自己实现接口  
**返回值**
- result:返回结果
- left:未处理字符串
- env_variable:当前环境下所有的键值用于增强该shell的自补全功能

**流程图**
![示例图片3](./png/屏幕截图%202024-09-07%20224434.png)

#### StrGen
将source源转换为迭代器，每次迭代产生MAX_IN个字符

#### TokenGen
```python
class Location(NamedTuple):
    line: int
    col: int
    time: int #标识是第几次交互

class Token(NamedTuple):
    value: str
    location: Location
    where: int #用于指示token在源代码中的位置，用于eval结束后未执行表达式位置的确定
```
字符流在一定规则下形成token，并且同时记录着位置信息

#### GenExp
token被组织成表达式Exp，产生Number、Compound、bool、Symbol类型。
同时为了记录位置信息，该项目在表达式和符号的基础上更进一步地设计了能够承载位置信息的Compoud_,Symbol_类（注意对于数字和bool类型在这里丢弃了位置信息这是出于，单一的数字和布尔值是不会出错的，我们只需要记录他们上层表达式的位置信息并抛出错误即可）：
```python
class LocationInterface(ABC):
    @abstractmethod
    def location_message(self):
        """返回html格式的位置信息"""
        pass

class Compound_(Compound,LocationInterface):
    def __init__(self, value: list[Exp] ,front: Location|None=None, end: Location|None=None):
        super().__init__(value)
        self.front = front
        self.end = end

    def location_message(self):
        return (f'Cell<input> In[{self.front.time}]</input>\n'
            f'From <input>line {self.front.line}, col {self.front.col}</input>\n'
            f'To <input>line {self.end.line}, col {self.end.col}</input>\n')

class Symbol_(UserString,LocationInterface):
    def __init__(self, token: Token):
        super().__init__(token.value)
        self.location = token.location

    def location_message(self):
        return f'Cell<input> In[{self.location.time}], line {self.location.line}, col {self.location.col}</input>\n'
```
LocationInterface接口是为了在后续报错设计中是否引入位置信息时可以使用isinstance来判断  
**注**：由于lisp极易元编程的原因，很有可能将要的执行的表达式本身并不在输入里而是在运行中生成的，生成的表达式时不具有位置信息的。  
> 这里是自己踩坑最严重的地方，一开始保留了除去左右括号的token位置信息。这导致，当一个表达式出错的时候很难把具体的错误位置throw出来，因为已经不知道左右括号的位置了。然后进行了第一次重构，决定保留表达式信息而没有留下单个token的信息，但是这导致当变量不在环境中的报错将不可避免地把位置信息扩展到整个表达式。然后进行了第二次重构，有了以上这个版本。然后经过精心设计可以把报错的范围精准限定在错误处，并且通过层层传递留下call-stack的信息

#### analyze
**注**：这是与lispy差异最严重的地方之一，为了更加高效的运行效率，我们将运行与解析表达式分离，这样做的好处是显而易见的，比如在执行过程时不需要对函数体进行不断地解析再执行，仅需解析一次即可。同时对于内置函数eval的参数（类型是Compoud）也是从这里开始传入需要运行的内容（~~虽然eval内置函数还没实现，未来有空再来~~）  

analyze逻辑并不复杂，该项目将解析的复杂度转移到了每一个句式类（所有的句式类都是Compoud的子类）上，一方面这是为了避免整个analyze过于臃肿，同时也有利于模块化设计，当需要加入语法糖或者是实现新的句式的时候，只需要自己实现一个句式类即可。每个句式类的analysis函数会将传入的exp进行解析，如果不符合一句式将会抛出LispSyntaxError。

```python
# COMPOUND 是一个以关键字为key，句式类为value的字典
def analyze(exp: Exp) -> Exp:
    if isinstance(exp, Compound):
        if isinstance(exp[0], Symbol) and exp[0] in COMPOUND:
            return COMPOUND[str(exp[0])].analysis(exp)
        if isinstance(exp, Compound_):#解析时位置信息仍保留
            return Compound_([analyze(i) for i in exp],exp.front,exp.end)
        else:
            return Compound([analyze(i) for i in exp])
    else:
        return exp
```
**注**：analyze是一个递归解析的过程，他会依次解析到Atom为止，唯一的例外是Quote类，对于（quote exp）的exp将不被继续解析下去，这与quote作用的表达式维持字面含义是保持一致的（同时这与(quote exp)作为eval参数时须经anlyze保持一致）
```python
class Quote(Compound):
@classmethod
    def analysis(cls, exp: Compound) -> Quote | None:
        if len(exp) != 2:
            cls.raise_error(exp)
        return Quote(exp[1])
```
**注**：对于形成句式后，最外一层的信息将被丢弃，因为除了LispSyntaxError，错误仅可能发生在句式的每一部分，因此这些句式类都是没有以及不用实现LocationInterface接口的

### eval
该解释器的核心模块
#### 流程图
![eval流程](./png/屏幕截图%202024-09-09%20193118.png)
其中句式类（如：Quote,If等他们都是继承了Compound的子类并且重写了evaluate方法逻辑较为简单，可以自行源码查看）  
由于图比较复杂，以下是一些文字注解：  
- 首先调用eval函数（传入exp,env作为参数）
- exp被传入exp_queue，env作为environmet
- 如果exp_queue为空则直接返回结果，不为空则pop出一个exp
    - exp为numbol/bool，则直接计算出值给result
    - exp为symbol时则在Environment中查找，若是没有找到则抛出LispnameError
    - exp为Compound时则将exp_queue、exp、Environment作为参数传递给Compound的evaluate函数调用，如果返回的是一个环境则更改环境，若不是则将值给result

- 对于Compound.evaluate，exp被分为first与other，其中first为Procedure类的实例，具有函数体与函数参数。
- 通过procedure的body最后一句是不是Return句式类来判断是否需要尾递归优化，如果需要则调用```procedure.__call__```，如果不需要则调用```procedure.no_tail_call```，并以other作为参数
- 将other映射到Producer类的arg上形成New_Env，并与之前的Environment形成链式结构（chainmap）作为Func_Environment
    - ```procedure.__call__```，以Func_Environment作为环境，依次执行函数体最后返回结果
    - ```procedure.no_tail_call```，以Func_Environment作为环境，依次执行函数体，并将最后一句函数体返回到传进来的exp_queue中，返回Environment作为result
- 其中对于以上两个过程抛出的error，如果是LispError则当前的exp信息加入形成call-stack形式的报错信息，如果不是LispError，则将其包装成LispError作为第一层报错使之更加模块化

## test模块
大部分沿用了lispy的检查（更改了一些接口），加入了一些对于该项目才有的特性的test样例

