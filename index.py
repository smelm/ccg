from ccg.lexicon_builder import unwrap_builder, LexiconBuilder
from ccg.chart import Combinators

lb = LexiconBuilder()
S, NP, PP = lb.primitive_categories("S", "NP", "PP")

foo = unwrap_builder(S << NP)
bar = unwrap_builder(S << PP)

print(list(Combinators.FORWARD_APPLICATION.value.combine(foo, unwrap_builder(NP))))
