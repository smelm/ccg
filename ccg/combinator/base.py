from abc import ABCMeta, abstractmethod


class BinaryCombinator(metaclass=ABCMeta):
    """
    Abstract class for representing a binary combinator.
    Merely defines functions for checking if the function and argument
    are able to be combined, and what the resulting category is.

    Note that as no assumptions are made as to direction, the unrestricted
    combinators can perform all backward, forward and crossed variations
    of the combinators; these restrictions must be added in the rule
    class.
    """

    @abstractmethod
    def can_combine(self, function, argument):
        pass

    @abstractmethod
    def combine(self, function, argument):
        pass


class ForwardCombinator(BinaryCombinator):
    """
    Class representing combinators where the primary functor is on the left.

    Takes an undirected combinator, and a predicate which adds constraints
    restricting the cases in which it may apply.
    """

    def __init__(self, combinator, predicate, suffix=""):
        self._combinator = combinator
        self._predicate = predicate
        self._suffix = suffix

    def can_combine(self, left, right):
        return self._combinator.can_combine(left, right) and self._predicate(
            left, right
        )

    def combine(self, left, right):
        yield from self._combinator.combine(left, right)

    def __str__(self):
        return f">{self._combinator}{self._suffix}"


class BackwardCombinator(BinaryCombinator):
    """
    The backward equivalent of the ForwardCombinator class.
    """

    def __init__(self, combinator, predicate, suffix=""):
        self._combinator = combinator
        self._predicate = predicate
        self._suffix = suffix

    def can_combine(self, left, right):
        return self._combinator.can_combine(right, left) and self._predicate(
            left, right
        )

    def combine(self, left, right):
        yield from self._combinator.combine(right, left)

    def __str__(self):
        return f"<{self._combinator}{self._suffix}"
