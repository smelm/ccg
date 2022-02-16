from .base import BinaryCombinator


class Substitution(BinaryCombinator):
    r"""
    Substitution (permutation) combinator.
    Implements rules of the form
    Y/Z (X\Y)/Z -> X/Z (<Sx)
    And other variations.
    """

    def can_combine(self, function, argument):
        if function.is_primitive() or argument.is_primitive():
            return False

        # These could potentially be moved to the predicates, as the
        # constraints may not be general to all languages.
        if function.res().is_primitive():
            return False
        if not function.arg().is_primitive():
            return False

        if not (function.dir().can_compose() and argument.dir().can_compose()):
            return False
        return (function.res().arg() == argument.res()) and (function.arg() == argument.arg())

    def combine(self, function, argument):
        if self.can_combine(function, argument):
            yield FunctionalCategory(function.res().res(), argument.arg(), argument.dir())

    def __str__(self):
        return "S"
