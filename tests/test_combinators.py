from ccg.api import FunctionalCategory, PrimitiveCategory
from ccg.chart import Combinators
from ccg.lexicon_builder import Direction, unwrap_builder, LexiconBuilder

X, Y, Z = LexiconBuilder().primitive_categories("X", "Y", "Z")

FORWARD = Direction.LEFT.value
BACKWARD = Direction.RIGHT.value

forward_function = unwrap_builder(X << Y)


class TestForwardApplication:
    def setup(self):
        self.rule = Combinators.FORWARD_APPLICATION.value

    def test_combines_only_forwards(self):
        left = forward_function
        right = unwrap_builder(Y)

        assert self.rule.can_combine(left, right)
        assert str(next(self.rule.combine(left, right))) == "X"

        assert not self.rule.can_combine(right, left)

    def test_combines_higher_order_parameters(self):
        left = unwrap_builder(X << (Y << Z))
        right = unwrap_builder(Y << Z)

        assert self.rule.can_combine(left, right)
        assert str(next(self.rule.combine(left, right))) == "X"

        # TODO: this should work as well
        # Primitive Categories should be equal according to name not reference
        # assert rule.combine(left, right) == X


class TestBackwardApplication:
    def setup(self):
        self.rule = Combinators.BACKWARD_APPLICATION.value

    def test_combines_only_backwards(self):
        left = unwrap_builder(Y)
        right = unwrap_builder(Y >> X)

        assert self.rule.can_combine(left, right)
        assert str(next(self.rule.combine(left, right))) == "X"

        assert not self.rule.can_combine(right, left)

    def test_combines_higher_order_parameters(self):
        left = unwrap_builder(Y << Z)
        right = unwrap_builder((Y << Z) >> X)

        assert self.rule.can_combine(left, right)
        assert str(next(self.rule.combine(left, right))) == "X"
