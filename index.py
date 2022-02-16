from itertools import product
from queue import Queue
from typing import List
from ccg.combinator import BackwardApplication, BackwardBx, BackwardComposition, BackwardSx, BackwardT, ForwardApplication, ForwardComposition, ForwardSubstitution, ForwardT
from ccg.lexicon import Token
from ccg.lexicon_builder import LexiconBuilder

lb = LexiconBuilder()
S, NP, N = lb.primitive_categories("S", "NP", "N")

# lexicon = lb.entries({
#     "I": NP,
#     "book": N,
#     "the": NP << N,
#     "read": (NP >> S) << NP
# })

amb_lexicon = lb.entries({
    "I": NP,
    "love": [NP, (NP >> S) << NP],
    "sleep": [NP, NP >> S],
})

# parses = my_parse(lexicon, "I read the book".split(), ApplicationRuleSet)

###################### Combinators ##################################
ApplicationRuleSet = [
    ForwardApplication,
    BackwardApplication,
]
CompositionRuleSet = [
    ForwardComposition,
    BackwardComposition,
    BackwardBx,
]
SubstitutionRuleSet = [
    ForwardSubstitution,
    BackwardSx,
]
TypeRaiseRuleSet = [ForwardT, BackwardT]

# The standard English rule set.
DefaultRuleSet = (
    ApplicationRuleSet + CompositionRuleSet + SubstitutionRuleSet + TypeRaiseRuleSet
)
#######################################################


def pairwise_with_context(iterable):
    """
    Returns before, first, second, after
    Where first and second are consequtive pairs
    and before and after all elements preceding/folling the pair.
    """
    iterable = list(iterable)
    for i in range(len(iterable) - 1):
        yield iterable[:i], iterable[i], iterable[i + 1], iterable[i+2:]


def tok_to_str(t):
    return f"{str(t._token)}:{str(t.categ())}" 

def toks_to_str(ts):
    return list(map(tok_to_str, ts))

def my_parse(lexicon, tokens: List[str], rules=DefaultRuleSet):
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
            results.append(parse)

        for rule in rules:
            for before, a, b, after in pairwise_with_context(parse):
                if rule.can_combine(a.categ(), b.categ()):
                    combined_categories = list(rule.combine(a.categ(),b.categ()))
                    assert len(combined_categories) == 1, "TODO: what would it mean to return a longer list?"
                    combined_categories = combined_categories[0]
                    # TODO: handle semantics
                    combined_token = Token(f"{a._token} {b._token}", combined_categories)
                    q.put(before + [combined_token] + after)
    # Output the resulting parses
    return results



parses = my_parse(amb_lexicon, "I love sleep".split(), DefaultRuleSet)
for parse in parses:
    print(*toks_to_str(parse))