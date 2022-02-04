from typing import List
from enum import Enum, auto

from thematic_relation import AGENT, STIMULUS

class Lexicon:

    def __init__(self):
        self.categories = []
        self.words = dict()
    

    def primitive_categories(self, *categories: List[str]):
        categories = [Category(name) for name in categories]
        self.categories += categories

        return categories

    def add(self, word, category):
        self.words[word] = category


class Category:
    def __init__(self, name, semantics=None):
        self.name = name
        self.semantics = semantics
    
    def __repr__(self) -> str:
        return f"Category({self.name}, {self.semantics})"

    def __rshift__(self, other):
        return FunctionalCategory(result=self, parameter=other, direction=Direction.RIGHT)

    def __lshift__(self, other):
        return FunctionalCategory(result=self, parameter=other, direction=Direction.LEFT)

    def __or__(self, other):
        return FunctionalCategory(result=self, parameter=other, direction=Direction.BOTH)


    def __call__(self, semantics):
        return Category(self.name, semantics)

    def __getitem__(self, restrictions):
        self.restrictions += restrictions
        return self


class Direction(Enum):
    LEFT = auto()
    RIGHT = auto()
    BOTH = auto()


class FunctionalCategory(Category):
    def __init__(self, result, parameter, direction: Direction) -> None:
        self.result = result
        self.parameter = parameter
        self.direction = direction

    def __repr__(self) -> str:
        direction = {Direction.LEFT: "l", Direction.RIGHT: "r", Direction.BOTH: "|"}[self.direction]
        return f"{self.parameter} -{direction}-> {self.result}"


    

lex = Lexicon()

S, NP, N, VP, V = lex.primitive_categories("S", "NP", "N", "VP", "V")

# lex.add("the", NP >> N)
# print(lex.words["the"])
# 
# print("the", NP >> N)
# print("hit", S << NP >> NP)
# print("foo", NP | NP)
# 
# print("apple", N("apple"))
# print("sleep", S({ "action": "sleep" }) << NP(AGENT))
print("read", S({ "action": "read" }) << NP(AGENT) >> NP(STIMULUS))