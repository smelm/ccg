from nltk.ccg.api import PrimitiveCategory
from nltk.ccg.lexicon import CCGLexicon, Token
from collections import defaultdict

class LexiconBuilder:
    def __init__(self):
        self.lexicon = CCGLexicon(None, [], dict(), defaultdict(list))
        self.start = None

    def primitive(self, primitive):
        s = self.lexicon._start
        
        if self.start is None:
            self.start = primitive
            self.lexicon._start = PrimitiveCategory(primitive)
        
        self.lexicon._primitives.append(primitive)
        return self


    def entry(self, ident, category, semantics=None):
        self.lexicon._entries[ident].append(Token(ident, category, semantics))

        return self


    def family(self, ident, category):
        self.lexicon._families[ident] = (category, None)
        return self


other_tiny = LexiconBuilder() \
                .primitive("S") \
                .primitive("NP") \
                .primitive("N") \
                .family("Det", "NP/N") \
                .family("Pro", "NP") \
                .family("IntransVsg", "S\\NP[sg]") \
                .family("IntransVpl", "S\\NP[pl]") \
                .family("TransVsg", "S\\NP[sg]/NP") \
                .family("TransVpl", "S\\NP[pl]/NP") \
                .entry("the", "NP[sg]/N[sg]") \
                .entry("the", "NP[pl]/N[pl]") \
                .entry("I", "Pro") \
                .entry("me", "Pro") \
                .entry("we", "Pro") \
                .entry("us", "Pro") \
                .entry("book", "N[sg]") \
                .entry("books", "N[pl]") \
                .entry("peach", "N[sg]") \
                .entry("peaches", "N[pl]") \
                .entry("policeman", "N[sg]") \
                .entry("policemen", "N[pl]") \
                .entry("boy", "N[sg]") \
                .entry("boys", "N[pl]") \
                .entry("sleep", "IntransVsg") \
                .entry("sleep", "IntransVpl") \
                .entry("eat", "IntransVpl") \
                .entry("eat", "TransVpl") \
                .entry("eats", "IntransVsg") \
                .entry("eats", "TransVsg") \
                .entry("see", "TransVpl") \
                .entry("sees", "TransVsg") \
                .lexicon