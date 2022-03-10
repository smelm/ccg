# Natural Language Toolkit: Combinatory Categorial Grammar
#
# Copyright (C) 2001-2021 NLTK Project
# Author: Graeme Gange <ggange@csse.unimelb.edu.au>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""
CCG Combinators
"""

from abc import ABCMeta, abstractmethod

from ccg.api import FunctionalCategory
from .base import BackwardCombinator, BinaryCombinator, ForwardCombinator
from .application import FunctionApplication
from .composition import Composition
from .substitution import Substitution


# Predicates for function application.

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


class TypeRaise(BinaryCombinator):
    """
    Undirected combinator for type raising.
    """

    def can_combine(self, function, arg):
        # The argument must be a function.
        # The restriction that arg.res() must be a function
        # merely reduces redundant type-raising; if arg.res() is
        # primitive, we have:
        # X Y\X =>(<T) Y/(Y\X) Y\X =>(>) Y
        # which is equivalent to
        # X Y\X =>(<) Y
        if not (arg.is_function() and arg.res().is_function()):
            return False

        arg = innermostFunction(arg)

        # left, arg_categ are undefined!
        subs = function.can_unify(arg.arg())
        if subs is not None:
            return True
        return False

    def combine(self, function, arg):
        if not (
            function.is_primitive() and arg.is_function() and arg.res().is_function()
        ):
            return

        # Type-raising matches only the innermost application.
        arg = innermostFunction(arg)

        subs = function.can_unify(arg.arg())
        if subs is not None:
            xcat = arg.res().substitute(subs)
            yield FunctionalCategory(
                xcat, FunctionalCategory(xcat, function, arg.dir()), -(arg.dir())
            )

    def __str__(self):
        return "T"


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


# Application combinator instances
ForwardApplication = ForwardCombinator(FunctionApplication(), forwardOnly)
BackwardApplication = BackwardCombinator(FunctionApplication(), backwardOnly)

# Instances of substitution combinators
ForwardSubstitution = ForwardCombinator(Substitution(), forwardSConstraint)
BackwardSx = BackwardCombinator(Substitution(), backwardSxConstraint, "x")

# Straight composition combinators
ForwardComposition = ForwardCombinator(Composition(), forwardOnly)
BackwardComposition = BackwardCombinator(Composition(), backwardOnly)

# Backward crossed composition
BackwardBx = BackwardCombinator(Composition(), backwardBxConstraint, suffix="x")

# Instances of type-raising combinators
ForwardT = ForwardCombinator(TypeRaise(), forwardTConstraint)
BackwardT = BackwardCombinator(TypeRaise(), backwardTConstraint)
