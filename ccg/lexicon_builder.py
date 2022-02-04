from argparse import ArgumentError
import enum
from nis import cat
from typing import Any, List

from ccg.api import Direction, FunctionalCategory, PrimitiveCategory
from ccg.lexicon import CCGLexicon, Token
from collections import defaultdict

# TODO: this type alias should be a base class somewhere
CategoryBuilder = Any

# TODO: function builder (nested)

class Direction(enum.Enum):
    LEFT = Direction("/", [])
    RIGHT = Direction("\\", [])


class PrimitiveCategoryBuilder:
    def __init__(self, category_name):
        self.category = PrimitiveCategory(category_name)

    def category_name(self):
        return self.category.categ()

    def function(self, argument: CategoryBuilder, direction: Direction):
        return FunctionalCategory(self.category, argument.category, direction)
    
    def __rshift__(self, other):
        return self.function(other, Direction.RIGHT.value)

    def __lshift__(self, other):
        return self.function(other, Direction.LEFT.value)

    def restrictions(self, *restrs):
        if not self.category._restrs:
            self.category._restrs = []
        self.category._restrs += restrs
        return self

    def __getitem__(self, restrs):
        self.restrictions(*restrs)
        return self


def primitive_categories(*names):
    return [PrimitiveCategoryBuilder(name) for name in names]

def unwrap_builder(cat):
    if isinstance(cat, PrimitiveCategoryBuilder):
        return cat.category
    else:
        return cat

class LexiconBuilder:
    def __init__(self):
        self.lexicon = CCGLexicon(None, [], dict(), defaultdict(list))
        self.start = None

    def primitive(self, primitive):   
        print("adding primitive", primitive) 
        if self.start is None:
            self.lexicon.start = primitive
            self.start
            self.lexicon._start = PrimitiveCategory(primitive)
        
        self.lexicon._primitives.append(primitive)
        return self


    def entry(self, ident, category, semantics=None):
        category = unwrap_builder(category)

        if isinstance(category, PrimitiveCategory) and category.categ() in self.lexicon._families.keys():
            category = self.lexicon._families[category.categ()][0]

        self.lexicon._entries[ident].append(Token(ident, category, semantics))

        return self


    def family(self, ident, category):
        category = unwrap_builder(category)

        self.lexicon._families[ident] = (category, None)
        return self


    def add_primitive_categories(self, *categories: List[PrimitiveCategoryBuilder]):
        categories = [c.category_name() for c in categories]
        self.lexicon._primitives.extend(categories)

        return self


    def add_start(self, category_builder: PrimitiveCategoryBuilder):
        """Add the start Symbol (Primitive Category)"""
        category = category_builder.category
        category_name = category_builder.category_name()

        if not self.start is None:
            raise SyntaxError(f"cannot set {category_name} as starting symbol since it is already defined as {self.lexicon.start()}")

        self.lexicon._start = category
        self.add_primitive_categories(category_builder)

        return self

    def make_lexicon(self):
        return self.lexicon