from ccg.api import FunctionalCategory, PrimitiveCategory
from ccg.chart import Combinators
from ccg.lexicon_builder import Direction, unwrap_builder, LexiconBuilder

X, Y, Z = LexiconBuilder().primitive_categories("X", "Y", "Z")

FORWARD = Direction.LEFT.value
BACKWARD = Direction.RIGHT.value

# double __ mean parenthesis
# direction indicated through alphabetical order

function_X_Y = unwrap_builder(X << Y)
function_Y_Z = unwrap_builder(Y << Z)
function_X__Y_Z = unwrap_builder(X << (Y << Z))
function_Y_X = unwrap_builder(Y >> X)
function__Y_Z__X = unwrap_builder((Y << Z) >> X)

X = unwrap_builder(X)
Y = unwrap_builder(Y)
Z = unwrap_builder(Z)


class TestForwardApplication:
    def setup(self):
        self.rule = Combinators.FORWARD_APPLICATION.value

    def test_combines_only_forwards(self):
        left = function_X_Y
        right = unwrap_builder(Y)

        assert self.rule.can_combine(left, right)
        assert next(self.rule.combine(left, right)) == X

        assert not self.rule.can_combine(right, left)

    def test_combines_higher_order_parameters(self):
        left = function_X__Y_Z
        right = function_Y_Z

        assert self.rule.can_combine(left, right)
        assert next(self.rule.combine(left, right)) == X

        # TODO: this should work as well
        # Primitive Categories should be equal according to name not reference
        # assert rule.combine(left, right) == X


class TestBackwardApplication:
    def setup(self):
        self.rule = Combinators.BACKWARD_APPLICATION.value

    def test_combines_only_backwards(self):
        left = unwrap_builder(Y)
        right = function_Y_X

        assert self.rule.can_combine(left, right)
        assert next(self.rule.combine(left, right)) == X

        assert not self.rule.can_combine(right, left)

    def test_combines_higher_order_parameters(self):
        left = function_Y_Z
        right = function__Y_Z__X

        assert self.rule.can_combine(left, right)
        assert next(self.rule.combine(left, right)) == X


# class ForwardComposition:

#     def setup(self):
#         self.rule = Combinators.FORWARD_COMPOSITION.value

#     def test_combines_only_forward
