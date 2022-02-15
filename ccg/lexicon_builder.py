import enum
from typing import Any, Dict, List

from ccg.api import Direction, FunctionalCategory, PrimitiveCategory
from ccg.lexicon import CCGLexicon, Token
from collections import defaultdict

# TODO: this type alias should be a base class somewhere

CategoryBuilder = Any

# TODO: function builder (nested)

class Direction(enum.Enum):
    LEFT = Direction("/", [])
    RIGHT = Direction("\\", [])

class Builder:
    def function(self, argument: CategoryBuilder, direction: Direction):
        return FunctionBuilder(self.category, argument.category, direction)
    
    def __rshift__(self, other):
        return self.function(other, Direction.RIGHT.value)

    def __lshift__(self, other):
        return self.function(other, Direction.LEFT.value)


class PrimitiveCategoryBuilder(Builder):
    def __init__(self, category_name, restrictions=None):
        self.category = PrimitiveCategory(category_name, restrictions)

    def category_name(self):
        return self.category.categ()


    def restrictions(self, *restrictions):
        return PrimitiveCategoryBuilder(self.category_name(), self.category.restrs() + list(restrictions))


    def __getitem__(self, restrs):
        return self.restrictions(restrs)
        


class FunctionBuilder(Builder):
    def __init__(self, return_category, argument_category, direction):
        self.category = FunctionalCategory(return_category, argument_category, direction)


class FamilyBuilder(Builder):
    def __init__(self, name, category):
        self.name = name
        self.category = unwrap_builder(category)


def unwrap_builder(cat):
    if isinstance(cat, PrimitiveCategoryBuilder):
        return cat.category
    elif isinstance(cat, FamilyBuilder):
        return cat.category
    elif isinstance(cat, FunctionBuilder):
        return cat.category
    else:
        return cat


class LexiconBuilder:
    def __init__(self):
        self.lexicon = CCGLexicon(None, [], dict(), defaultdict(list))
        self.start = None

    def _resolve_family(self, category):
        if isinstance(category, PrimitiveCategory) and category.categ() in self.lexicon._families.keys():
            return self.lexicon._families[category.categ()][0]
        else:
            return category

    def entry(self, ident, categories, semantics=None):
        # category can either be a single category or a list
        # For example:
        #     the :: NP["sg"]/N["sg"]
        #     the :: NP["pl"]/N["pl"]
        # would be passed in as a list
        
        if not isinstance(categories, List):
            categories = [categories]

        for category in categories:
            category = unwrap_builder(category)
            category = self._resolve_family(category)
        
            self.lexicon._entries[ident].append(Token(ident, category, semantics))
    

    def entries(self, entries):
        for ident, category in entries.items():
            self.entry(ident, category)
        
        return self.lexicon


    def entries_with_semantic(self, entries: Dict):
        for ident, (category, semantics) in entries.items():
            self.entry(ident, category, semantics)

        return self.lexicon


    def family(self, ident, category):
        category = unwrap_builder(category)

        self.lexicon._families[ident] = (category, None)


    def families(self, families: Dict[str, CategoryBuilder]):
        family_builders = []
        for identifier, category in families.items():
            family_builders.append(FamilyBuilder(identifier, category))
            self.family(identifier, unwrap_builder(category))

        return family_builders


    def primitive_categories(self, *names):
        primitive_builders = [PrimitiveCategoryBuilder(name) for name in names]
        categories = [c.category_name() for c in primitive_builders]
        self.lexicon._primitives.extend(categories)
        self.lexicon._start = primitive_builders[0].category

        return primitive_builders
