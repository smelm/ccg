from ccg.api import FunctionalCategory, PrimitiveCategory
from ccg.chart import Combinators
from ccg.lexicon_builder import Direction, unwrap_builder, LexiconBuilder

import itertools

X, Y, Z = LexiconBuilder().primitive_categories("X", "Y", "Z")

FORWARD = Direction.LEFT.value
BACKWARD = Direction.RIGHT.value

# double __ mean parenthesis
# direction indicated through alphabetical order

CATEGORIES = dict()

CATEGORIES["X/Y"] = unwrap_builder(X << Y)
CATEGORIES["Y/Z"] = unwrap_builder(Y << Z)
CATEGORIES["X/Z"] = unwrap_builder(X << Z)
CATEGORIES["X/(Y/Z)"] = unwrap_builder(X << (Y << Z))
CATEGORIES["X\\Y"] = unwrap_builder(Y >> X)
CATEGORIES["X\\(Y/Z)"] = unwrap_builder((Y << Z) >> X)
# CATEGORIES["X/(Y\\Z)"] = unwrap_builder(X << (Z >> Y))

X = unwrap_builder(X)
Y = unwrap_builder(Y)
Z = unwrap_builder(Z)

CATEGORIES["X"] = X
CATEGORIES["Y"] = Y
CATEGORIES["Z"] = Z


def get_expected_result(left, right, expected_combinations):
    results = [res for l, r, res in expected_combinations if l == left and r == right]

    assert len(results) < 2

    if len(results) == 0:
        return False

    return results[0]


def combines_only(rule, expected_combinations):
    # all left right combinations
    all_combinations = list(itertools.product(CATEGORIES.values(), CATEGORIES.values()))
    # in both permutations
    all_combinations = itertools.chain(all_combinations, [(r, l) for l, r in all_combinations])

    for left, right in all_combinations:
        if expected_result := get_expected_result(left, right, expected_combinations):
            if not rule.can_combine(left, right):
                print(left, right)
            assert rule.can_combine(left, right), f"cannot combine {left}, {right}"
            assert (
                next(rule.combine(left, right)) == expected_result
            ), f"incorrect result for combining {left} and {right} != {expected_result}"
        else:
            assert not rule.can_combine(left, right), f"did not expect to be able to combine {left} {right}"


class TestCombinators:
    def test_forward_application(self):
        combines_only(
            Combinators.FORWARD_APPLICATION.value,
            [
                (CATEGORIES["X/Y"], Y, X),
                (CATEGORIES["Y/Z"], Z, Y),
                (CATEGORIES["X/(Y/Z)"], CATEGORIES["Y/Z"], X),
                (CATEGORIES["X/Z"], Z, X),
            ],
        )

    def test_backward_application(self):
        combines_only(
            Combinators.BACKWARD_APPLICATION.value,
            [(Y, CATEGORIES["X\\Y"], X), (CATEGORIES["Y/Z"], CATEGORIES["X\\(Y/Z)"], X)],
        )

    def test_forward_composition(self):
        combines_only(
            Combinators.FORWARD_COMPOSITION.value, [(CATEGORIES["X/Y"], CATEGORIES["Y/Z"], CATEGORIES["X/Z"])]
        )

    def test_backward_composition(self):
        combines_only(
            Combinators.BACKWARD_COMPOSITION.value, [(CATEGORIES["Y/Z"], CATEGORIES["X\\Y"], CATEGORIES["X/Z"])]
        )

    def test_forward_type_raising(self):
        combines_only(Combinators.FORWARD_TYPE_RAISE.value, [])

    def test_forward_type_raising(self):
        combines_only(Combinators.BACKWARD_TYPE_RAISE.value, [])
