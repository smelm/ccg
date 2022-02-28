from ccg.api import FunctionalCategory, PrimitiveCategory
from ccg.chart import Combinators
from ccg.lexicon_builder import Direction, unwrap_builder, LexiconBuilder

import itertools

X, Y, Z = LexiconBuilder().primitive_categories("X", "Y", "Z")

FORWARD = Direction.LEFT.value
BACKWARD = Direction.RIGHT.value

CAT = dict()

CAT["X/Y"] = unwrap_builder(X << Y)
CAT["Y/Z"] = unwrap_builder(Y << Z)
CAT["X/Z"] = unwrap_builder(X << Z)
CAT["X/(Y/Z)"] = unwrap_builder(X << (Y << Z))
CAT["X\\Y"] = unwrap_builder(Y >> X)
CAT["X\\(Y/Z)"] = unwrap_builder((Y << Z) >> X)
CAT["(Y\\X)/Z"] = unwrap_builder((X >> Y) << Z)
CAT["(X/Y)\\(X/Y)"] = unwrap_builder((X << Y) >> (X << Y))

CAT["X"] = unwrap_builder(X)
CAT["Y"] = unwrap_builder(Y)
CAT["Z"] = unwrap_builder(Z)


class TestCombinators:
    def test_forward_application(self):
        combines_only(
            Combinators.FORWARD_APPLICATION.value,
            [
                (CAT["X/Y"], CAT["Y"], CAT["X"]),
                (CAT["Y/Z"], CAT["Z"], CAT["Y"]),
                (CAT["X/(Y/Z)"], CAT["Y/Z"], CAT["X"]),
                (CAT["X/Z"], CAT["Z"], CAT["X"]),
                (CAT["(Y\\X)/Z"], CAT["Z"], unwrap_builder(X >> Y)),
            ],
        )

    def test_backward_application(self):
        combines_only(
            Combinators.BACKWARD_APPLICATION.value,
            [
                (CAT["Y"], CAT["X\\Y"], CAT["X"]),
                (CAT["Y/Z"], CAT["X\\(Y/Z)"], CAT["X"]),
                (CAT["X/Y"], CAT["(X/Y)\\(X/Y)"], CAT["X/Y"]),
            ],
        )

    def test_forward_composition(self):
        combines_only(
            Combinators.FORWARD_COMPOSITION.value,
            [
                (CAT["X/Y"], CAT["Y/Z"], CAT["X/Z"]),
            ],
        )

    def test_backward_composition(self):
        combines_only(
            Combinators.BACKWARD_COMPOSITION.value,
            [(CAT["Y/Z"], CAT["X\\Y"], CAT["X/Z"]), (CAT["(X/Y)\\(X/Y)"], CAT["(X/Y)\\(X/Y)"], CAT["(X/Y)\\(X/Y)"])],
        )

    def test_forward_type_raising(self):
        combines_only(
            Combinators.FORWARD_TYPE_RAISE.value, [(CAT["X"], CAT["(Y\\X)/Z"], unwrap_builder(Y << (X >> Y)))]
        )

    def test_backward_type_raising(self):
        combines_only(
            Combinators.BACKWARD_TYPE_RAISE.value, [(CAT["(X/Y)\\(X/Y)"], CAT["Y"], unwrap_builder((X << Y) >> X))]
        )


def get_expected_result(left, right, expected_combinations):
    results = [res for l, r, res in expected_combinations if l == left and r == right]

    assert len(results) < 2

    if len(results) == 0:
        return False

    return results[0]


def combines_only(rule, expected_combinations):
    # all left right combinations
    all_combinations = list(itertools.product(CAT.values(), CAT.values()))
    # in both permutations
    all_combinations = itertools.chain(all_combinations, [(r, l) for l, r in all_combinations])

    for left, right in all_combinations:
        if expected_result := get_expected_result(left, right, expected_combinations):
            if not rule.can_combine(left, right):
                print(left, right)
            assert rule.can_combine(left, right), f"cannot combine {left}, {right}"

            actual_result = next(rule.combine(left, right))
            assert (
                actual_result == expected_result
            ), f"incorrect result for combining {left} and {right}: {actual_result} != {expected_result}"
        else:
            assert not rule.can_combine(left, right), f"did not expect to be able to combine {left} {right}"
