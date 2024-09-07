## 前言
在看完《流畅的python》lispy(一个python写的lisp语言解释器)后，对lisp语言突然饶有兴趣，让我想到了之前那时觉得并不好看的《计算机程序的构造和解释》，于是捡着感兴趣的部分（前四章）了解了下lisp语言设计思想，自己写了一个lisp解释器（虽然一开始以为是一个轻松的工作但是还是才了不少坑重构了好几次）

# 程序语言的构造与解释
## 程序语言的构造
### EXP
**Exp:TypeAlias=Compound|Atom**
### Atom 原子表达式
#### 符号（Symbol）：
可以作为一个程序对象的别名  
（解释器中：Symbol:TypeAlias=UserString）

#### 数字（Number）：
可以以整数，浮点数，分数的形式输入，这些都可以被解析  
(解释器中：Number:TypeAlias=int|float)

#### 布尔值（Boolean）
```#t```为真，```#f```为假  
0的值与 #f 相等，但是指向的对象不一致  
即：
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
语言内置的、无法再进一步分解的最基本的函数。  
**注**：由于基本为一句话函数，所以均没有尾递归优化。
##### 算术运算 **(具有参数检查在接受非Number对象时会报错)**
- +: 加法运算符。接受两个或多个数值参数，返回它们的和。
- -: 减法运算符。接受两个或多个数值参数，返回它们的差。
示例: (- 10 3 2) 返回 5。
- *: 乘法运算符。接受两个或多个数值参数，返回它们的积。
- /: 除法运算符。接受两个或多个数值参数，返回它们的商。
- quotient: 整数除法运算符。接受两个或多个数值参数，返回它们的整数商。

##### 比较运算 **(具有参数检查在接受非Number对象时会报错)**
- \>: 大于运算符。接受两个或多个数值参数，如果第一个参数大于后面的所有参数，则返回 True，否则返回 False。
- <: 小于运算符。接受两个或多个数值参数，如果第一个参数小于后面的所有参数，则返回 True，否则返回 False。
- \>=: 大于等于运算符。接受两个或多个数值参数，如果第一个参数大于等于后面的所有参数，则返回 True，否则返回 False。
- <=: 小于等于运算符。接受两个或多个数值参数，如果第一个参数小于等于后面的所有参数，则返回 True，否则返回 False。
- =: 等于运算符。接受两个或多个数值参数，如果所有参数相等，则返回 True，否则返回 False。

##### 其他数值运算 **(具有参数检查在接受非Number对象时会报错)**
- abs: 绝对值函数。接受一个数值参数，返回其绝对值。
- max: 最大值函数。接受一个或多个数值参数，返回其中的最大值。
- min: 最小值函数。接受一个或多个数值参数，返回其中的最小值。

##### 逻辑运算 **（接受任何参数）**
- and: 逻辑与运算符。接受零个或多个参数，如果所有参数都为 True，则返回 True，否则返回 False。
- or: 逻辑或运算符。接受零个或多个参数，如果至少有一个参数为 True，则返回 True，否则返回 False。
- not: 逻辑非运算符。接受一个参数，如果参数为 False，则返回 True，否则返回 False。

##### 检测 **（接受任何参数）**
- eq?: 对象相等检测函数。接受两个或多个参数，如果所有参数是同一个对象，则返回 True，否则返回 False。
- equal?: 值相等检测函数。接受两个或多个参数，如果所有参数的值相等，则返回 True，否则返回 False。
- number?: 数值检测函数。接受一个参数，如果参数是数值类型，则返回 True，否则返回 False。
- procedure?: 过程检测函数。接受一个参数，如果参数是可调用的过程，则返回 True，否则返回 False。
**虽然在实际实现中，内置函数与用户定义函数不是一个类型但是该操作符是基于callable定义的**
- symbol?: 符号检测函数。接受一个参数，如果参数是符号类型，则返回 True，否则返回 False。

##### 高阶函数 **(具有参数检查，接受一个函数和若干列表作为参数)**
- map: 映射函数。接受一个函数和一个或多个列表参数，返回一个新列表，其中每个元素是函数作用在对应列表元素上的结果。  
**注**：为了效率，在实现中被映射函数的尾递归会被关闭
示例: (map + '(1 2 3) '(4 5 6)) 返回 (5 7 9)。

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
**注**：analyze是一个递归解析的过程，他会依次解析到Atom为止，唯一的例外是Quote类，对于（quote exp）的exp将不被继续解析下去，这与quote作用的表达式维持字面含义是保持一致的（这也与(quote exp)作为eval参数时须经anlyze保持一致）
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