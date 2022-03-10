# Natural Language Toolkit: Combinatory Categorial Grammar
#
# Copyright (C) 2001-2021 NLTK Project
# Author: Graeme Gange <ggange@csse.unimelb.edu.au>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""
CCG Lexicons
"""

from __future__ import annotations
import re
from collections import defaultdict
from typing import Dict, List, Set

from ccg.api import CCGVar, Direction, FunctionalCategory, PrimitiveCategory
from nltk.internals import deprecated
from nltk.sem.logic import Expression


# ------------
# Regular expressions used for parsing components of the lexicon
# ------------

# Parses a primitive category and subscripts
PRIM_RE = re.compile(r"""([A-Za-z]+)(\[[A-Za-z,]+\])?""")

# Separates the next primitive category from the remainder of the
# string
NEXTPRIM_RE = re.compile(r"""([A-Za-z]+(?:\[[A-Za-z,]+\])?)(.*)""")

# Separates the next application operator from the remainder
APP_RE = re.compile(r"""([\\/])([.,]?)([.,]?)(.*)""")

# Parses the definition of the right-hand side (rhs) of either a word or a family
LEX_RE = re.compile(r"""([\S_]+)\s*(::|[-=]+>)\s*(.+)""", re.UNICODE)

# Parses the right hand side that contains category and maybe semantic predicate
RHS_RE = re.compile(r"""([^{}]*[^ {}])\s*(\{[^}]+\})?""", re.UNICODE)

# Parses the semantic predicate
SEMANTICS_RE = re.compile(r"""\{([^}]+)\}""", re.UNICODE)

# Strips comments from a line
COMMENTS_RE = re.compile("""([^#]*)(?:#.*)?""")


class Token:
    """
    Class representing a token.

    token => category {semantics}
    e.g. eat => S\\var[pl]/var {\\x y.eat(x,y)}
    """

    def __init__(self, token: str, category: str, semantics: Expression = None):
        self._token = token
        self._category = category
        self._semantics = semantics

    def categ(self) -> str:
        return self._category

    def semantics(self) -> Expression:
        return self._semantics

    def __str__(self) -> str:
        if self._semantics is not None:
            return f"{str(self._category)} {{{str(self._semantics)}}}"
        else:
            return str(self._category)


# TODO: why is start a string but primitives a List of PrimitiveCategory?
class CCGLexicon:
    """
    Class representing a lexicon for CCG grammars.

    * `primitives`: The list of primitive categories for the lexicon
    * `families`: Families of categories
    * `entries`: A mapping of words to possible categories
    """

    def __init__(
        self,
        start: str,
        primitives: List[str],
        families: Set[any],
        entries: Dict[str, any],
    ):
        self._start = PrimitiveCategory(start)
        self._primitives = primitives
        self._families = families
        self._entries = entries

    def categories(self, word: str) -> any:
        """Returns all the possible categories for a word"""
        return self._entries[word]

    def start(self) -> str:
        """Return the target category for the parser"""
        return self._start

    def __str__(self):
        return "\n".join(
            [
                f"{ident} => {' | '.join(map(str, categories))}"
                for ident, categories in sorted(self._entries.items())
            ]
        )


# -----------
# Parsing lexicons
# -----------


def matchBrackets(string: str):
    """
    Separate the contents matching the first set of brackets from the rest of
    the input.
    """
    rest = string[1:]
    inside = "("

    while rest != "" and not rest.startswith(")"):
        if rest.startswith("("):
            (part, rest) = matchBrackets(rest)
            inside = inside + part
        else:
            inside = inside + rest[0]
            rest = rest[1:]
    if rest.startswith(")"):
        return (inside + ")", rest[1:])
    raise AssertionError("Unmatched bracket in string '" + string + "'")


def nextCategory(string: str):
    """
    Separate the string for the next portion of the category from the rest
    of the string
    """
    if string.startswith("("):
        return matchBrackets(string)
    return NEXTPRIM_RE.match(string).groups()


def parseApplication(app: str):
    """
    Parse an application operator
    """
    return Direction(app[0], app[1:])


def parseSubscripts(subscr: str):
    """
    Parse the subscripts for a primitive category
    """
    if subscr:
        return subscr[1:-1].split(",")
    return []


def parsePrimitiveCategory(chunks, primitives, families, var):
    """
    Parse a primitive category

    If the primitive is the special category 'var', replace it with the
    correct `CCGVar`.
    """
    if chunks[0] == "var":
        if chunks[1] is None:
            if var is None:
                var = CCGVar()
            return (var, var)

    catstr = chunks[0]
    if catstr in families:
        (cat, cvar) = families[catstr]
        if var is None:
            var = cvar
        else:
            cat = cat.substitute([(cvar, var)])
        return (cat, var)

    if catstr in primitives:
        subscrs = parseSubscripts(chunks[1])
        return (PrimitiveCategory(catstr, subscrs), var)
    raise AssertionError(
        "String '" + catstr + "' is neither a family nor primitive category."
    )


def augParseCategory(line, primitives, families, var=None):
    """
    Parse a string representing a category, and returns a tuple with
    (possibly) the CCG variable for the category
    """
    (cat_string, rest) = nextCategory(line)

    # if cat string is surounded with parenthesis
    # remove them and try again
    if cat_string.startswith("("):
        (res, var) = augParseCategory(cat_string[1:-1], primitives, families, var)
    else:
        (res, var) = parsePrimitiveCategory(
            PRIM_RE.match(cat_string).groups(), primitives, families, var
        )

    while rest != "":
        app = APP_RE.match(rest).groups()
        direction = parseApplication(app[0:3])
        rest = app[3]

        (cat_string, rest) = nextCategory(rest)
        if cat_string.startswith("("):
            (arg, var) = augParseCategory(cat_string[1:-1], primitives, families, var)
        else:
            (arg, var) = parsePrimitiveCategory(
                PRIM_RE.match(cat_string).groups(), primitives, families, var
            )
        res = FunctionalCategory(res, arg, direction)

    return (res, var)


def fromstring(lex_str: str, include_semantics: bool = False):
    """
    Convert string representation into a lexicon for CCGs.
    """
    # TODO: having to reset is not good, fix that!
    CCGVar.reset_id()
    primitives = []
    families = {}
    entries = defaultdict(list)
    for line in lex_str.splitlines():
        # Strip comments and leading/trailing whitespace.
        line = COMMENTS_RE.match(line).groups()[0].strip()
        if line == "":
            continue

        if line.startswith(":-"):
            # A line of primitive categories.
            # The first one is the target category
            # ie, :- S, N, NP, VP
            primitives = primitives + [
                prim.strip() for prim in line[2:].strip().split(",")
            ]
        else:
            # Either a family definition, or a word definition
            (ident, sep, rhs) = LEX_RE.match(line).groups()
            (catstr, semantics_str) = RHS_RE.match(rhs).groups()
            (cat, var) = augParseCategory(catstr, primitives, families)

            if sep == "::":
                # Family definition
                # ie, Det :: NP/N
                families[ident] = (cat, var)
            else:
                semantics = None
                if include_semantics is True:
                    if semantics_str is None:
                        raise AssertionError(
                            line
                            + " must contain semantics because include_semantics is set to True"
                        )
                    else:
                        semantics = Expression.fromstring(
                            SEMANTICS_RE.match(semantics_str).groups()[0]
                        )
                # Word definition
                # ie, which => (N\N)/(S/NP)
                entries[ident].append(Token(ident, cat, semantics))
    return CCGLexicon(primitives[0], primitives, families, entries)
