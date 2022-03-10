# Natural Language Toolkit: Combinatory Categorial Grammar
#
# Copyright (C) 2001-2021 NLTK Project
# Author: Graeme Gange <ggange@csse.unimelb.edu.au>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
The lexicon is constructed by calling
``lexicon.fromstring(<lexicon string>)``.

In order to construct a parser, you also need a rule set.
The standard English rules are provided in chart as
``chart.DefaultRuleSet``.

The parser can then be constructed by calling, for example:
``parser = chart.CCGChartParser(<lexicon>, <ruleset>)``

Parsing is then performed by running
``parser.parse(<sentence>.split())``.

While this returns a list of trees, the default representation
of the produced trees is not very enlightening, particularly
given that it uses the same tree class as the CFG parsers.
It is probably better to call:
``chart.printCCGDerivation(<parse tree extracted from list>)``
which should print a nice representation of the derivation.

This entire process is shown far more clearly in the demonstration:
python chart.py
"""

from collections import deque
from enum import Enum
import itertools
from queue import Queue
from typing import List

from ccg.combinator import *
from ccg.combinator import (
    BackwardApplication,
    BackwardBx,
    BackwardComposition,
    BackwardSx,
    BackwardT,
    ForwardApplication,
    ForwardComposition,
    ForwardSubstitution,
    ForwardT,
)
from ccg.combinator import (
    FunctionApplication,
    BackwardCombinator,
    Composition,
    Substitution,
)
from ccg.lexicon import CCGLexicon, Token, fromstring
from ccg.logic import *
from nltk.parse import ParserI
from nltk.parse.chart import AbstractChartRule, Chart, EdgeI
from nltk.sem.logic import *
from nltk.tree import Tree

from itertools import product
from more_itertools import pairwise


# Based on the EdgeI class from NLTK.
# A number of the properties of the EdgeI interface don't
# transfer well to CCGs, however.
class CCGEdge(EdgeI):
    def __init__(self, span, categ, rule):
        self._span = span
        self._categ = categ
        self._rule = rule
        self._comparison_key = (span, categ, rule)

    # Accessors
    def lhs(self):
        return self._categ

    def span(self):
        return self._span

    def start(self):
        return self._span[0]

    def end(self):
        return self._span[1]

    def length(self):
        return self._span[1] - self.span[0]

    def rhs(self):
        return ()

    def dot(self):
        return 0

    def is_complete(self):
        return True

    def is_incomplete(self):
        return False

    def nextsym(self):
        return None

    def categ(self):
        return self._categ

    def rule(self):
        return self._rule


class CCGLeafEdge(EdgeI):
    """
    Class representing leaf edges in a CCG derivation.
    """

    def __init__(self, pos, token, leaf):
        self._pos = pos
        self._token = token
        self._leaf = leaf
        self._comparison_key = (pos, token.categ(), leaf)

    # Accessors
    def lhs(self):
        return self._token.categ()

    def span(self):
        return (self._pos, self._pos + 1)

    def start(self):
        return self._pos

    def end(self):
        return self._pos + 1

    def length(self):
        return 1

    def rhs(self):
        return self._leaf

    def dot(self):
        return 0

    def is_complete(self):
        return True

    def is_incomplete(self):
        return False

    def nextsym(self):
        return None

    def token(self):
        return self._token

    def categ(self):
        return self._token.categ()

    def leaf(self):
        return self._leaf


class BinaryCombinatorRule(AbstractChartRule):
    """
    Class implementing application of a binary combinator to a chart.
    Takes the directed combinator to apply.
    """

    NUMEDGES = 2

    def __init__(self, combinator):
        self._combinator = combinator

    # Apply a combinator
    def apply(self, chart, grammar, left_edge, right_edge):
        # The left & right edges must be touching.
        if not (left_edge.end() == right_edge.start()):
            return

        # Check if the two edges are permitted to combine.
        # If so, generate the corresponding edge.
        if self._combinator.can_combine(left_edge.categ(), right_edge.categ()):
            for res in self._combinator.combine(left_edge.categ(), right_edge.categ()):
                new_edge = CCGEdge(
                    span=(left_edge.start(), right_edge.end()),
                    categ=res,
                    rule=self._combinator,
                )
                if chart.insert(new_edge, (left_edge, right_edge)):
                    yield new_edge

    # The representation of the combinator (for printing derivations)
    def __str__(self):
        return "%s" % self._combinator


# Type-raising must be handled slightly differently to the other rules, as the
# resulting rules only span a single edge, rather than both edges.


class ForwardTypeRaiseRule(AbstractChartRule):
    """
    Class for applying forward type raising
    """

    NUMEDGES = 2

    def __init__(self):
        self._combinator = ForwardT

    def apply(self, chart, grammar, left_edge, right_edge):
        if not (left_edge.end() == right_edge.start()):
            return

        for res in self._combinator.combine(left_edge.categ(), right_edge.categ()):
            new_edge = CCGEdge(span=left_edge.span(), categ=res, rule=self._combinator)
            if chart.insert(new_edge, (left_edge,)):
                yield new_edge

    def __str__(self):
        return "%s" % self._combinator


class BackwardTypeRaiseRule(AbstractChartRule):
    """
    Class for applying backward type raising.
    """

    NUMEDGES = 2

    def __init__(self):
        self._combinator = BackwardT

    def apply(self, chart, grammar, left_edge, right_edge):
        if not (left_edge.end() == right_edge.start()):
            return

        for res in self._combinator.combine(left_edge.categ(), right_edge.categ()):
            new_edge = CCGEdge(span=right_edge.span(), categ=res, rule=self._combinator)
            if chart.insert(new_edge, (right_edge,)):
                yield new_edge

    def __str__(self):
        return "%s" % self._combinator


# Common sets of combinators used for English derivations.
ApplicationRuleSet = [
    BinaryCombinatorRule(ForwardApplication),
    BinaryCombinatorRule(BackwardApplication),
]
CompositionRuleSet = [
    BinaryCombinatorRule(ForwardComposition),
    BinaryCombinatorRule(BackwardComposition),
    BinaryCombinatorRule(BackwardBx),
]
SubstitutionRuleSet = [
    BinaryCombinatorRule(ForwardSubstitution),
    BinaryCombinatorRule(BackwardSx),
]
TypeRaiseRuleSet = [ForwardTypeRaiseRule(), BackwardTypeRaiseRule()]

# The standard English rule set.
DefaultRuleSet = (
    ApplicationRuleSet + CompositionRuleSet + SubstitutionRuleSet + TypeRaiseRuleSet
)


# Implements the CYK algorithm
def chart_parse(lexicon, tokens: List[str], rules=DefaultRuleSet):
    tokens = list(tokens)
    chart = CCGChart(list(tokens))

    # Initialize leaf edges.
    for index in range(chart.num_leaves()):
        for token in lexicon.categories(chart.leaf(index)):
            new_edge = CCGLeafEdge(index, token, chart.leaf(index))
            chart.insert(new_edge, ())

    # Select a span for the new edges
    for span in range(2, chart.num_leaves() + 1):
        for start in range(0, chart.num_leaves() - span + 1):
            # Try all possible pairs of edges that could generate
            # an edge for that span
            for part in range(1, span):
                lstart = start
                mid = start + part
                rend = start + span

                for left in chart.select(span=(lstart, mid)):
                    for right in chart.select(span=(mid, rend)):
                        # Generate all possible combinations of the two edges
                        for rule in rules:
                            edges_added_by_rule = 0
                            for newedge in rule.apply(chart, lexicon, left, right):
                                edges_added_by_rule += 1

    # Output the resulting parses
    return chart.parses(lexicon.start())


class CCGChart(Chart):
    def __init__(self, tokens: List[str]):
        Chart.__init__(self, tokens)

    # Constructs the trees for a given parse. Unfortnunately, the parse trees need to be
    # constructed slightly differently to those in the default Chart class, so it has to
    # be reimplemented
    def _trees(self, edge, complete, memo, tree_class):
        assert complete, "CCGChart cannot build incomplete trees"

        if edge in memo:
            return memo[edge]

        if isinstance(edge, CCGLeafEdge):
            word = tree_class(edge.token(), [self._tokens[edge.start()]])
            leaf = tree_class((edge.token(), "Leaf"), [word])
            memo[edge] = [leaf]
            return [leaf]

        memo[edge] = []
        trees = []

        for cpl in self.child_pointer_lists(edge):
            child_choices = [self._trees(cp, complete, memo, tree_class) for cp in cpl]
            for children in itertools.product(*child_choices):
                lhs = (
                    Token(
                        self._tokens[edge.start() : edge.end()],
                        edge.lhs(),
                        compute_semantics(children, edge),
                    ),
                    str(edge.rule()),
                )
                trees.append(tree_class(lhs, children))

        memo[edge] = trees
        return trees


def compute_semantics(children, edge):
    if children[0].label()[0].semantics() is None:
        return None

    if len(children) == 2:
        if isinstance(edge.rule(), BackwardCombinator):
            children = [children[1], children[0]]

        combinator = edge.rule()._combinator
        function = children[0].label()[0].semantics()
        argument = children[1].label()[0].semantics()

        if isinstance(combinator, FunctionApplication):
            return compute_function_semantics(function, argument)
        elif isinstance(combinator, Composition):
            return compute_composition_semantics(function, argument)
        elif isinstance(combinator, Substitution):
            return compute_substitution_semantics(function, argument)
        else:
            raise AssertionError("Unsupported combinator '" + combinator + "'")
    else:
        return compute_type_raised_semantics(children[0].label()[0].semantics())


# --------
# Displaying derivations
# --------
def printCCGDerivation(tree):
    # Get the leaves and initial categories
    leafcats = tree.pos()
    leafstr = ""
    catstr = ""

    # Construct a string with both the leaf word and corresponding
    # category aligned.
    for (leaf, cat) in leafcats:
        str_cat = "%s" % cat
        nextlen = 2 + max(len(leaf), len(str_cat))
        lcatlen = (nextlen - len(str_cat)) // 2
        rcatlen = lcatlen + (nextlen - len(str_cat)) % 2
        catstr += " " * lcatlen + str_cat + " " * rcatlen
        lleaflen = (nextlen - len(leaf)) // 2
        rleaflen = lleaflen + (nextlen - len(leaf)) % 2
        leafstr += " " * lleaflen + leaf + " " * rleaflen
    print(leafstr.rstrip())
    print(catstr.rstrip())

    # Display the derivation steps
    printCCGTree(0, tree)


# Prints the sequence of derivation steps.
def printCCGTree(lwidth, tree):
    rwidth = lwidth

    # Is a leaf (word).
    # Increment the span by the space occupied by the leaf.
    if not isinstance(tree, Tree):
        return 2 + lwidth + len(tree)

    # Find the width of the current derivation step
    for child in tree:
        rwidth = max(rwidth, printCCGTree(rwidth, child))

    # Is a leaf node.
    # Don't print anything, but account for the space occupied.
    if not isinstance(tree.label(), tuple):
        return max(
            rwidth, 2 + lwidth + len("%s" % tree.label()), 2 + lwidth + len(tree[0])
        )

    (token, op) = tree.label()

    if op == "Leaf":
        return rwidth

    # Pad to the left with spaces, followed by a sequence of '-'
    # and the derivation rule.
    print(lwidth * " " + (rwidth - lwidth) * "-" + "%s" % op)
    # Print the resulting category on a new line.
    str_res = "%s" % (token.categ())
    if token.semantics() is not None:
        str_res += " {" + str(token.semantics()) + "}"
    respadlen = (rwidth - lwidth - len(str_res)) // 2 + lwidth
    print(respadlen * " " + str_res)
    return rwidth


###### My parsing algorithm ######
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


class MyCombinator:
    def __init__(self, combinator, predicate, suffix="", backward=False) -> None:
        self._combinator = combinator
        self.backward = backward
        self.predicate = predicate
        self._suffix = suffix

    def switch_args_if_backwards(self, left, right):
        if self.backward:
            return right, left
        else:
            return left, right

    def can_combine(self, left, right):

        return self._combinator.can_combine(
            *self.switch_args_if_backwards(left, right)
        ) and self.predicate(left, right)

    def combine(self, left, right):
        # this cannot be switched for backward

        if not self.can_combine(left, right):
            return []

        return list(
            self._combinator.combine(*self.switch_args_if_backwards(left, right))
        )

    def __str__(self):
        return f"{'<' if self.backward else '>'}{self._combinator}{self._suffix}"


class MyComposableCombinator(MyCombinator):
    def __init__(self, combinator, predicate_list, suffix="", backward=False) -> None:
        super().__init__(
            combinator, self.make_predicate(predicate_list), suffix, backward
        )

    def make_predicate(self, predicate_list):
        def pred(left, right):
            for p in predicate_list:
                if not p(left, right):
                    return False
            return True

        return pred


"""

           return not function.arg().can_unify(argument) is None

    def combine(self, function, argument):
        if not function.is_function():
            return

        subs = function.arg().can_unify(argument)
        if subs is None:
            return

        yield function.res().substitute(subs)

    def __str__(self):
        return ""

forwardOnly
"""


def first(*predicate_list):
    return [lambda left, right: p(left) for p in predicate_list]


def second(*predicate_list):
    return [lambda left, right: p(right) for p in predicate_list]


def is_function(cat):
    return cat.is_function()


def is_forward(cat):
    return cat.dir().is_forward()


def can_be_applied(function, arg):
    return function.arg().can_unify(arg) is not None


class Combinators(Enum):
    FORWARD_APPLICATION = MyComposableCombinator(
        FunctionApplication(), first(is_function, is_forward) + [can_be_applied]
    )
    BACKWARD_APPLICATION = MyCombinator(
        FunctionApplication(), backwardOnly, backward=True
    )
    FORWARD_COMPOSITION = MyCombinator(Composition(), forwardOnly)
    BACKWARD_COMPOSITION = MyCombinator(Composition(), backwardOnly, backward=True)
    BACKWARD_BX = MyCombinator(
        Composition(), backwardBxConstraint, backward=True, suffix="x"
    )
    FORWARD_SUBSTITUTION = MyCombinator(Substitution(), forwardSConstraint)
    BACKWARD_SX = MyCombinator(
        Substitution(), backwardSxConstraint, backward=True, suffix="x"
    )
    FORWARD_TYPE_RAISE = MyCombinator(TypeRaise(), forwardTConstraint)
    BACKWARD_TYPE_RAISE = MyCombinator(TypeRaise(), backwardTConstraint, backward=True)


RuleSet = [c.value for c in Combinators]
#######################################################


def my_compute_type_raised_semantics(core, b, rule):
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

    result = LambdaExpression(var, core)
    return result


def my_compute_function_semantics(function: Token, argument: Token, rule):
    return ApplicationExpression(function, argument).simplify()


def my_compute_composition_semantics(function, argument, rule):
    assert isinstance(argument, LambdaExpression), (
        "`" + str(argument) + "` must be a lambda expression"
    )
    return LambdaExpression(
        argument.variable, ApplicationExpression(function, argument.term).simplify()
    )


def my_compute_substitution_semantics(function, argument, rule):
    assert isinstance(function, LambdaExpression) and isinstance(
        function.term, LambdaExpression
    ), ("`" + str(function) + "` must be a lambda expression with 2 arguments")
    assert isinstance(argument, LambdaExpression), (
        "`" + str(argument) + "` must be a lambda expression"
    )

    new_argument = ApplicationExpression(
        argument, VariableExpression(function.variable)
    ).simplify()
    new_term = ApplicationExpression(function.term, new_argument).simplify()

    return LambdaExpression(function.variable, new_term)


def my_compute_semantics(a, b, rule):
    if rule.value.backward:
        b, a = a, b

    combinator = rule.value._combinator
    a = a.semantics()
    b = b.semantics()

    if isinstance(combinator, FunctionApplication):
        return my_compute_function_semantics(a, b, rule)
    elif isinstance(combinator, Composition):
        return my_compute_composition_semantics(a, b, rule)
    elif isinstance(combinator, Substitution):
        return my_compute_substitution_semantics(a, b, rule)
    elif isinstance(combinator, TypeRaise):
        return my_compute_type_raised_semantics(a, b, rule)
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


class Parse:
    def __init__(self, tokens, parent_parse=None, rule=None):
        self.tokens = list(tokens)
        self.history = [(self, rule)]

        if parent_parse:
            self.history = parent_parse.history + self.history

    def is_final(self):
        return len(self.tokens) == 1

    def get_final(self):
        assert self.is_final()
        return self.tokens[0]

    def pairwise_with_context(self):
        return pairwise_with_context(self.tokens)

    def semantics(self):
        if not self.is_final():
            return None
        else:
            return self.get_final().semantics()

    def print(self):
        def printable_tokens(tokens):
            return [
                f"{str(t._token)}:{str(t.categ())}[{t.semantics() if t.semantics() else ''}]"
                for t in tokens
            ]

        print("Parse: ", *toks_to_str(self.tokens), self.semantics())
        print("history:")
        for p, r in self.history:
            print(4 * " ", *printable_tokens(p.tokens), r)


def my_parse(lexicon, tokens: List[str], rules):
    categories = [lexicon.categories(token) for token in tokens]

    # since any token can have multiple categories we try each combination
    parses = list(map(Parse, product(*categories, repeat=1)))
    q = Queue()

    for parse in parses:
        q.put(parse)

    results = []
    while not q.empty():
        parse = q.get()

        if parse.is_final():
            results.append(parse)

        for rule_type in Combinators:
            rule = rule_type.value

            for before, a, b, after in parse.pairwise_with_context():
                if rule.can_combine(a.categ(), b.categ()):
                    category = list(rule.combine(a.categ(), b.categ()))
                    assert (
                        len(category) == 1
                    ), "TODO: what would it mean to return a longer list?"

                    token = f"{a._token} {b._token}"
                    category = category[0]
                    semantics = my_compute_semantics(a, b, rule_type)

                    # this is terrible but needs to be done
                    # type raise needs two arguments to compute but
                    # only one of the categories changes
                    if rule_type == Combinators.FORWARD_TYPE_RAISE:
                        q.put(
                            Parse(
                                before + [Token(token, category, semantics), b] + after
                            ),
                            parse,
                            rule,
                        )
                    elif rule_type == Combinators.BACKWARD_TYPE_RAISE:
                        q.put(
                            Parse(
                                before + [a, Token(token, category, semantics)] + after
                            ),
                            parse,
                            rule,
                        )
                    else:
                        q.put(
                            Parse(
                                before + [Token(token, category, semantics)] + after,
                                parse,
                                rule,
                            )
                        )

    return results
