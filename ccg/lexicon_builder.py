from ccg.api import PrimitiveCategory
from ccg.lexicon import CCGLexicon, Token
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
        if isinstance(category, PrimitiveCategory) and category.categ() in self.lexicon._families.keys():
            category = self.lexicon._families[category.categ()][0]

        self.lexicon._entries[ident].append(Token(ident, category, semantics))

        return self


    def family(self, ident, category):
        self.lexicon._families[ident] = (category, None)
        return self
