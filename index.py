from enum import Enum
from itertools import product
from queue import Queue
from typing import List
from ccg import chart

from ccg.combinator.application import FunctionApplication
from ccg.combinator.base import BackwardCombinator, ForwardCombinator
from ccg.combinator.combinator import TypeRaise
from ccg.combinator.composition import Composition
from ccg.combinator.substitution import Substitution
from ccg.lexicon import Token, fromstring
from ccg.lexicon_builder import LexiconBuilder

from nltk.sem.logic import *

lb = LexiconBuilder()
S, NP, N = lb.primitive_categories("S", "NP", "N")

# lexicon = lb.entries({
#     "I": NP,
#     "book": N,
#     "the": NP << N,
#     "read": (NP >> S) << NP
# })


"""
   I                 love                sleep
 NP {I}  ((S\\NP)/NP) {\\t a.love(a,t)}  NP {SLEEP}
        ------------------------------------------>
                (S\\NP) {\\a.love(a,SLEEP)}
--------------------------------------------------<
                S {love(I,SLEEP)}



   I                 love                sleep
 NP {I}  ((S\\NP)/NP) {\\t a.love(a,t)}  NP {SLEEP}
-------->T
(S/(S\\NP)) {\\F.F(I)}
        ------------------------------------------>
                (S\\NP) {\\a.love(a,SLEEP)}
-------------------------------------------------->
                S {love(I,SLEEP)}




   I                 love                sleep
 NP {I}  ((S\\NP)/NP) {\\t a.love(a,t)}  NP {SLEEP}
-------->T
(S/(S\\NP)) {\\F.F(I)}
-------------------------------------->B
        (S/NP) {\\t.love(I,t)}
-------------------------------------------------->
                S {love(I,SLEEP)}


"""
