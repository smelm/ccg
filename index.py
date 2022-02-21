from enum import Enum
from itertools import product
from queue import Queue
from typing import List
from ccg import chart

from ccg.combinator.application import FunctionApplication
from ccg.combinator.base import BackwardCombinator, ForwardCombinator
from ccg.combinator.combinator import TypeRaise
from ccg.combinator.composition import Composition
from ccg.combinator.substitution import Substitution
from ccg.lexicon import Token, fromstring
from ccg.lexicon_builder import LexiconBuilder

from nltk.sem.logic import *

lb = LexiconBuilder()
S, NP, N = lb.primitive_categories("S", "NP", "N")

# lexicon = lb.entries({
#     "I": NP,
#     "book": N,
#     "the": NP << N,
#     "read": (NP >> S) << NP
# })

# ambigous_lexicon = lb.entries(
#     {
#         "I": NP,
#         "love": [NP, (NP >> S) << NP],
#         "sleep": [NP, NP >> S],
#     }
# )

ambigous_lexicon = fromstring(
    """
:- S,NP
I => NP { I }
love => NP { LOVE }
love => S\\NP/NP { \\t a. love(a, t)}
sleep => NP { SLEEP }
sleep => S\\NP { \\a. sleep(a) }
""",
    True,
)

# parses = my_parse(lexicon, "I read the book".split(), ApplicationRuleSet)

###################### Combinators ##################################
# Ensures the left functor takes an argument on the right
def forwardOnly(left, right):
    return left.dir().is_forward()


# Ensures the right functor takes an argument on the left
def backwardOnly(left, right):
    return right.dir().is_backward()


# Predicates for restricting application of straight composition.
def bothForward(left, right):
    return left.dir().is_forward() and right.dir().is_forward()


def bothBackward(left, right):
    return left.dir().is_backward() and right.dir().is_backward()


# Predicates for crossed composition
def crossedDirs(left, right):
    return left.dir().is_forward() and right.dir().is_backward()


def backwardBxConstraint(left, right):
    # The functors must be crossed inwards
    if not crossedDirs(left, right):
        return False
    # Permuting combinators must be allowed
    if not left.dir().can_cross() and right.dir().can_cross():
        return False
    # The resulting argument category is restricted to be primitive
    return left.arg().is_primitive()


# Predicate for forward substitution
def forwardSConstraint(left, right):
    if not bothForward(left, right):
        return False
    return left.res().dir().is_forward() and left.arg().is_primitive()


# Predicate for backward crossed substitution
def backwardSxConstraint(left, right):
    if not left.dir().can_cross() and right.dir().can_cross():
        return False
    if not bothForward(left, right):
        return False
    return right.res().dir().is_backward() and right.arg().is_primitive()


# Retrieves the left-most functional category.
# ie, (N\N)/(S/NP) => N\N
def innermostFunction(categ):
    while categ.res().is_function():
        categ = categ.res()
    return categ


# Predicates for type-raising
# The direction of the innermost category must be towards
# the primary functor.
# The restriction that the variable must be primitive is not
# common to all versions of CCGs; some authors have other restrictions.
def forwardTConstraint(left, right):
    arg = innermostFunction(right)
    return arg.dir().is_backward() and arg.res().is_primitive()


def backwardTConstraint(left, right):
    arg = innermostFunction(left)
    return arg.dir().is_forward() and arg.res().is_primitive()


class Combinators(Enum):
    FORWARD_APPLICATION = ForwardCombinator(FunctionApplication(), forwardOnly)
    BACKWARD_APPLICATION = BackwardCombinator(FunctionApplication(), backwardOnly)
    FORWARD_COMPOSITION = ForwardCombinator(Composition(), forwardOnly)
    BACKWARD_COMPOSITION = BackwardCombinator(Composition(), backwardOnly)
    BACKWARD_BX = BackwardCombinator(Composition(), backwardBxConstraint, suffix="x")
    FORWARD_SUBSTITUTION = ForwardCombinator(Substitution(), forwardSConstraint)
    BACKWARD_SX = BackwardCombinator(Substitution(), backwardSxConstraint, "x")
    FORWARD_TYPE_RAISE = ForwardCombinator(TypeRaise(), forwardTConstraint)
    BACKWARD_TYPE_RAISE = BackwardCombinator(TypeRaise(), backwardTConstraint)


RuleSet = [c.value for c in Combinators]
#######################################################


def compute_type_raised_semantics(a, b, rule):
    core = a
    parent = None
    while isinstance(core, LambdaExpression):
        parent = core
        core = core.term

    var = Variable("F")
    while var in core.free():
        var = unique_variable(pattern=var)
    core = ApplicationExpression(FunctionVariableExpression(var), core)

    if parent is not None:
        parent.term = core
    else:
        a = core

    return LambdaExpression(var, a)


def compute_function_semantics(function: Token, argument: Token, rule):
    return ApplicationExpression(function, argument).simplify()


def compute_composition_semantics(function, argument, rule):
    assert isinstance(argument, LambdaExpression), "`" + str(argument) + "` must be a lambda expression"
    return LambdaExpression(argument.variable, ApplicationExpression(function, argument.term).simplify())


def compute_substitution_semantics(function, argument, rule):
    assert isinstance(function, LambdaExpression) and isinstance(function.term, LambdaExpression), (
        "`" + str(function) + "` must be a lambda expression with 2 arguments"
    )
    assert isinstance(argument, LambdaExpression), "`" + str(argument) + "` must be a lambda expression"

    new_argument = ApplicationExpression(argument, VariableExpression(function.variable)).simplify()
    new_term = ApplicationExpression(function.term, new_argument).simplify()

    return LambdaExpression(function.variable, new_term)


def compute_semantics(a, b, rule):
    print(a, b, rule)

    if isinstance(rule.value, BackwardCombinator):
        b, a = a, b

    combinator = rule.value._combinator
    a = a.semantics()
    b = b.semantics()

    if isinstance(combinator, FunctionApplication):
        return compute_function_semantics(a, b, rule)
    elif isinstance(combinator, Composition):
        return compute_composition_semantics(a, b, rule)
    elif isinstance(combinator, Substitution):
        return compute_substitution_semantics(a, b, rule)
    elif isinstance(combinator, TypeRaise):
        return compute_type_raised_semantics(a, b, rule)
    else:
        raise AssertionError("Unsupported combinator '" + combinator + "'")


def pairwise_with_context(iterable):
    """
    Returns before, first, second, after
    Where first and second are consequtive pairs
    and before and after all elements preceding/folling the pair.
    """
    iterable = list(iterable)
    for i in range(len(iterable) - 1):
        yield iterable[:i], iterable[i], iterable[i + 1], iterable[i + 2 :]


def tok_to_str(t):
    return f"{str(t._token)}:{str(t.categ())}"


def toks_to_str(ts):
    return list(map(tok_to_str, ts))


def my_parse(lexicon, tokens: List[str], rules):
    categories = [lexicon.categories(token) for token in tokens]

    # since any token can have multiple categories we try each combination
    parses = list(product(*categories, repeat=1))
    q = Queue()

    for parse in parses:
        q.put(parse)

    results = []
    while not q.empty():
        parse = q.get()

        if len(parse) == 1:
            results.append(parse[0])

        for rule_type in Combinators:
            rule = rule_type.value

            for before, a, b, after in pairwise_with_context(parse):
                if rule.can_combine(a.categ(), b.categ()):
                    category = list(rule.combine(a.categ(), b.categ()))
                    assert len(category) == 1, "TODO: what would it mean to return a longer list?"

                    token = f"{a._token} {b._token}"
                    category = category[0]
                    semantics = compute_semantics(a, b, rule_type)

                    q.put(before + [Token(token, category, semantics)] + after)
    return results


parses = my_parse(ambigous_lexicon, "I love sleep".split(" "), RuleSet)
for parse in parses:
    print(tok_to_str(parse))
    print(parse.semantics())
    print(5 * "\n")


"""
   I                 love                sleep
 NP {I}  ((S\\NP)/NP) {\\t a.love(a,t)}  NP {SLEEP}
        ------------------------------------------>
                (S\\NP) {\\a.love(a,SLEEP)}
--------------------------------------------------<
                S {love(I,SLEEP)}



   I                 love                sleep
 NP {I}  ((S\\NP)/NP) {\\t a.love(a,t)}  NP {SLEEP}
-------->T
(S/(S\\NP)) {\\F.F(I)}
        ------------------------------------------>
                (S\\NP) {\\a.love(a,SLEEP)}
-------------------------------------------------->
                S {love(I,SLEEP)}




   I                 love                sleep
 NP {I}  ((S\\NP)/NP) {\\t a.love(a,t)}  NP {SLEEP}
-------->T
(S/(S\\NP)) {\\F.F(I)}
-------------------------------------->B
        (S/NP) {\\t.love(I,t)}
-------------------------------------------------->
                S {love(I,SLEEP)}


"""
