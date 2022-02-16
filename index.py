from ccg.lexicon_builder import LexiconBuilder
from ccg.chart import ApplicationRuleSet, chart_parse, my_parse, printCCGDerivation

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

parses = my_parse(amb_lexicon, "I love sleep".split(), ApplicationRuleSet)
#for parse in parses:
 #   printCCGDerivation(parse)