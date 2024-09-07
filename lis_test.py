import ast
import math
from pytest import mark, fixture, raises
from analyze_eval import *
from interpreter import *

############################################################# tests for parse

@mark.parametrize( 'source, expected', [
    ('7', 7),
    ('x', 'x'),
    ('(sum 1 2 3)', ['sum', 1, 2, 3]),
    ('(+ (* 2 100) (* 1 10))', ['+', ['*', 2, 100], ['*', 1, 10]]),
    ('99 100', 99),  # parse stops at the first complete expression
    ('(a)(b)', ['a']),
    ('\'a', ['quote','a']),
    ('\'(a b)', ['quote',['a','b']]),
    ('\'(+ (* 2 100) (* 1 10))', ['quote',['+', ['*', 2, 100], ['*', 1, 10]]]),
])
def test_parse(source: str, expected) -> None:
    strgen = StrGen(source, 100)
    tokengen = TokenGen(strgen, 1)
    got=GenExp(tokengen)
    assert got == expected

#通过测试

# ########################################################## tests for evaluate

# Norvig's tests are not isolated: they assume the
# same environment from first to last test.
# Norvig_suite_global_env = standard_env()
# #quote 可能会对内部数字进行处理
@mark.parametrize( 'source, expected', [
    ("(quote (testing 1 (2.0) -3.14e159))", "(testing 1 (2.0) -3.14e+159)"),
    ("(+ 2 2)", "4"),
    ("(+ (* 2 100) (* 1 10))", "210"),
    ("(if (> 6 5) (+ 1 1) (+ 2 2))", "2"),
    ("(if (< 6 5) (+ 1 1) (+ 2 2))", "4"),
    ("(define x 3)", None),
    ("x", "3"),
    ("(+ x x)", "6"),
    ("((lambda (x) (+ x x)) 5)", "10"),
    ("(define twice (lambda (x) (* 2 x)))", None),
    ("(twice 5)", "10"),
    ("(define compose (lambda (f g) (lambda (x) (f (g x)))))", None),
    ("((compose list twice) 5)", "(10)"),
    ("(define repeat (lambda (f) (compose f f)))", None),
    ("((repeat twice) 5)", "20"),
    ("((repeat (repeat twice)) 5)", "80"),
    ("(define fact (lambda (n) (if (<= n 1) 1 (* n (fact (- n 1))))))", None),
    ("(fact 3)", "6"),
    ("(fact 50)", "30414093201713378043612608166064768844377641568960512000000000000"),
    ("(define abs (lambda (n) ((if (> n 0) + -) 0 n)))", None),
    ("(list (abs -3) (abs 0) (abs 3))", "(3 0 3)"),
    ("""(define combine (lambda (f)
            (lambda (x y)
                (if (= (length x) 1) (list (f (car x) (car y)))
                    (cons (f (car x) (car y))
                        ((combine f) (cdr x) (cdr y)))))))""", None),
    ("(define zip (combine list))", None),
    ("(zip (list 1 2 2) (list 4 5 6))", "((1 4) (2 5) (2 6))"),
])
def test_evaluate(source: str, expected: Exp | None) -> None:
    got = interpret(source, 1, 100, 1)[0]
    assert got == expected
# 通过测试


@fixture
def std_env() -> Environment:
    return standard_env()


# tests for each of the cases in evaluate

def test_evaluate_variable(std_env) -> None:
    std_env.update({'x': 10})
    source = 'x'
    expected = '10'
    got = interpret(source, 1, 100, 1,std_env)[0]
    assert got == expected

def test_evaluate_literal(std_env: Environment) -> None:
    source = '3.3'
    expected = '3.3'
    got = interpret(source, 1, 100, 1,std_env)[0]
    assert got == expected


def test_evaluate_quote(std_env: Environment) -> None:
    source = '(quote (1.1 is not 1))'
    expected = '(1.1 is not 1)'
    got = interpret(source, 1, 100, 1,std_env)[0]
    assert got == expected

def test_evaluate_define_set(std_env: Environment) -> None:
    source = '(define a 1) (set! a 2) a'
    expected = '2'
    got = interpret(source, 1, 100, 3, std_env)[0]
    assert got == expected

    source = '(define (f) (set! a 3)) (f) a'
    expected = '3'
    got = interpret(source, 1, 100, 3, std_env)[0]
    assert got == expected

    source = '(define (g) (define a 3) (set! a 4) a) (g)'
    expected = '4'
    got = interpret(source, 1, 100, 2, std_env)[0]
    assert got == expected

    source = 'a'
    expected = '3'
    got = interpret(source, 1, 100, 1, std_env)[0]
    assert got == expected

def test_set_ref(std_env:Environment):
    source = '(define a \'(1 2 3)) (set-ref! a 0 2) a'
    expected = '(2 2 3)'
    got = interpret(source, 1, 100, 3, std_env)[0]
    assert got == expected

def test_evaluate_if_true(std_env: Environment) -> None:
    source = '(if 1 10 no-such-thing)'
    expected = '10'
    got = interpret(source, 1, 100, 1,std_env)[0]
    assert got == expected


def test_evaluate_if_false(std_env: Environment) -> None:
    source = '(if 0 no-such-thing 20)'
    expected = '20'
    got = interpret(source, 1, 100, 1,std_env)[0]
    assert got == expected


def test_define(std_env: Environment) -> None:
    source = '(define answer (* 6 7))'
    got = interpret(source, 1, 100, 1,std_env)[0]
    assert got is None
    assert std_env['answer'] == 42


def test_lambda(std_env: Environment) -> None:
    source = '(lambda (a b) (if (>= a b) a b))'
    a=StrGen(source, 100)
    b=TokenGen(a, 1)
    c=GenExp(b)
    func=eval(analyze(c),std_env)
    assert func.parms == ['a', 'b'] #type: ignore
    assert len(func.body) == 1 #type: ignore
    assert str(func.body[0]) == '(if (>= a b) a b)' #type: ignore
    assert func.definition_env is std_env #type: ignore
    assert func(iter([1,2]))[0]['a']==1 #type: ignore
    assert func(iter([1,2]))[0]['b']==2 #type: ignore
    assert func(iter([1,2]))[0] is not std_env #type: ignore


def test_lambda_with_multi_expression_body(std_env: Environment) -> None:
    source = """
        ((lambda (m n)
            (define (mod m n)
                (- m (* n (quotient m n))))
            (define (gcd m n)
                (if (= n 0)
                    m
                    (gcd n (mod m n))))
            (gcd m n)
        )18 45)
    """
    got = interpret(source, 1, 100, 1,std_env)[0]
    assert got == '9'


def test_lambda_with_no_body(std_env: Environment) -> None:
    source = '(lambda (a))'
    with raises(LispSyntaxError) as excinfo:
        a=StrGen(source, 100)
        b=TokenGen(a, 1)
        c=GenExp(b)
        eval(analyze(c),std_env)
    assert 'LispSyntaxError' in str(excinfo)


def test_begin(std_env: Environment) -> None:
    source = """
        (begin
            (define x (* 2 3))
            (* x 7)
        )
        """
    got = interpret(source, 1, 100, 1,std_env)[0]
    assert got == '42'


def test_call_builtin_car(std_env: Environment) -> None:
    source = '(car (quote (11 22 33)))'
    got = interpret(source, 1, 100, 1,std_env)[0]
    assert got == '11'


def test_call_builtin_append(std_env: Environment) -> None:
    source = '(append (quote (a b)) (quote (c d)))'
    got = interpret(source, 1, 100, 1,std_env)[0]
    assert got == '(a b c d)'


def test_call_builtin_map(std_env: Environment) -> None:
    source = '(map (lambda (x) (* x 2)) (quote (1 2 3)))'
    got = interpret(source, 1, 100, 1,std_env)[0]
    assert got == '(2 4 6)'

def test_call_builtin_map_2(std_env: Environment) -> None:
    source = '(map (lambda (x y) (+ x y)) \'(1 2 3) \'(4 5 6))'
    got = interpret(source, 1, 100, 1,std_env)[0]
    assert got == '(5 7 9)'


def test_define_procedure(std_env: Environment) -> None:
    source = '(max 1 2 3)'
    got = interpret(source, 1, 100, 1,std_env)[0]
    assert got == '3'
    source = '(max 3 2 1 0)'
    got = interpret(source, 1, 100, 1,std_env)[0]
    assert got == '3'
    source = '(define (max a b) (if (>= a b) a b))'
    got = interpret(source, 1, 100, 1,std_env)[0]
    assert got is None
    max_fn = std_env['max']
    assert max_fn.parms == ['a', 'b']
    assert len(max_fn.body) == 1
    assert str(max_fn.body[0]) == '(if (>= a b) a b)'
    assert max_fn.definition_env is std_env
    assert max_fn(iter([1, 2]))[0]['a'] == 1



def test_call_user_procedure(std_env: Environment) -> None:
    source = """
        (begin
            (define max (lambda (a b) (if (>= a b) a b)))
            (max 22 11)
        )
        """
    got = interpret(source, 1, 100, 1,std_env)[0]
    assert got == '22'


def test_cond(std_env: Environment) -> None:
    source = """
        (cond ((> x 0) x)
              ((= x 0) 0)
              ((< x 0) (- 0 x)))
        """
    std_env['x'] = -2
    got = interpret(source, 1, 100, 1,std_env)[0]
    assert got == '2'


def test_cond_else(std_env: Environment) -> None:
    source = """
       (cond ((> x 0) x)
             ((< x 0) (- 0 x))
             (else 0))
        """
    std_env['x'] = 0
    got = interpret(source, 1, 100, 1,std_env)[0]
    assert got == '0'


def test_cond_no_match(std_env: Environment) -> None:
    source = """
       (cond ((> x 0) x)
             ((< x 0) (- 0 x)))
        """
    std_env['x'] = 0
    got = interpret(source, 1, 100, 1,std_env)[0]
    assert got is None


@mark.parametrize('source, expected', [
    ('(or)', 'False'),
    ('(or 0)', 'False'),
    ('(or 1)', 'True'),
    ('(or 0 2)', 'True'),
    ('(or 0 3 (crash))', 'True'),
])
def test_or(source: str, expected: Exp) -> None:
    got = interpret(source, 1, 100, 1)[0]
    assert got == expected


@mark.parametrize('source, expected', [
    ('(and)', 'True'),
    ('(and 0)', 'False'),
    ('(and 1)', 'True'),
    ('(and 0 (crash))', 'False'),
    ('(and 1 2 3)', 'True'),
])
def test_and(source: str, expected) -> None:
    got = interpret(source, 1, 100, 1)[0]
    assert got == expected

# ############### tail-call optimization (TCO)

def test_simple_user_procedure_call(std_env: Environment) -> None:
    source = """
        (begin
            (define (answer) 42)
            (answer)
        )
        """
    got = interpret(source, 1, 100, 1,std_env)[0]
    assert got == '42'



def test_tail_call_countdown(std_env: Environment) -> None:
    countdown_scm = """
        (define (countdown n)
            (if (= n 0)
                0
                (countdown (- n 1))))
    """
    got = interpret(countdown_scm, 1, 100, 1,std_env)[0]
    # maximum without TCO: n=316
    n = 100_000  # 100_000 may take 1.85s to run
    source = f'(countdown {n})'
    got = interpret(source, 1, 100, 1,std_env)[0]
    assert got == '0'


def test_tail_call_sum_integers(std_env: Environment) -> None:
    sum_ints_scm = """
        (define (sum n acc)
        (if (= n 0)
            acc
            (sum (- n 1) (+ n acc))))
    """
    got = interpret(sum_ints_scm, 1, 100, 1,std_env)[0]
    # maximum without TCO: n=316
    n = 1_000_000  # may take 24.21 to run
    source = f'(sum {n} 0)'
    got = interpret(source, 1, 100, 1,std_env)[0]
    assert got == str(sum(range(1, n + 1)))


def test_tail_call_factorial(std_env: Environment) -> None:
    factorial_scm = """
        (define (factorial-iter n product)
            (if (= n 1)
                product
                (factorial-iter (- n 1) (* n product))))
    """
    got = interpret(factorial_scm, 1, 100, 1,std_env)[0]
    # maximum without TCO: n=317
    n = 10_00
    source = f'(factorial-iter {n} 1)'
    got = interpret(source, 1, 100, 1,std_env)[0]
    assert got == str(math.prod(range(2, n + 1)))
