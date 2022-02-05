from operator import itemgetter
from re import L
from typing import Tuple
import pytest
from nltk.sem.logic import ConstantExpression, IndividualVariableExpression, LambdaExpression, Variable, ApplicationExpression

import ccg.lexicon as lex
from ccg.lexicon_builder import LexiconBuilder
from ccg.api import CCGVar, Direction, FunctionalCategory, PrimitiveCategory


# import for them to show up in coverage
from ccg.chart import CCGChartParser, DefaultRuleSet, printCCGDerivation, printCCGTree
import ccg.logic


# TODO: test var category

grammar = """
    :- S,NP,N
    Det :: NP/N
    Pro :: NP
    IntransV :: S\\NP

    the => NP[sg]/N[sg]
    the => NP[pl]/N[pl]

    I => Pro

    book => N[sg]
    books => N[pl,other]

    and => var\\.,var/.,var

    read => S\\NP/NP
"""

lexicon = lex.fromstring(grammar)

grammar_with_semantics = "\n".join([
        ":- S,N,NP",
        "book => N {book}",
        "the => NP/N {\\x.x}",
        "read => S/NP {\\x.read(x)}"
    ])

lexicon_with_semantics = lex.fromstring(grammar_with_semantics, include_semantics=True)


class TestLexiconParsing:
    def test_can_declare_primitives(self):
        assert lexicon._primitives == ["S", "NP", "N"]


    def test_first_primitive_is_start(self):
        assert lexicon.start().categ() == "S"


    def test_primitive_category_family(self):
        (cat, _) = lexicon._families["Pro"]
        assert isinstance(cat, PrimitiveCategory)
        assert cat.categ() == "NP"



    def test_forward_function_category_family(self):
        (cat, _) = lexicon._families["Det"]
        assert isinstance(cat, FunctionalCategory)
        assert cat.dir().is_forward() and not cat.dir().is_backward()
        assert cat.arg().categ() == "N"
        assert cat.res().categ() == "NP"


    def test_backward_function_category_family(self):
        (cat, _) = lexicon._families["IntransV"]
        assert isinstance(cat, FunctionalCategory)
        assert cat.dir().is_backward() and not cat.dir().is_forward()
        assert cat.arg().categ() == "NP"
        assert cat.res().categ() == "S"


    def test_one_restriction(self):
        cat = lexicon.categories("book")[0].categ()
        assert isinstance(cat, PrimitiveCategory)
        assert cat.categ() == "N"
        assert cat.restrs() == ["sg"]


    def test_multiple_restriction(self):
        cat = lexicon.categories("books")[0].categ()
        assert isinstance(cat, PrimitiveCategory)
        assert cat.categ() == "N"
        assert cat.restrs() == ["pl", "other"]


    def test_str_formatting_of_lexicon(self):
        assert str(lexicon) == "\n".join([
            "I => NP",
            "and => ((_var0\\.,_var0)/.,_var0)",
            "book => N['sg']",
            "books => N['pl','other']",
            "read => ((S\\NP)/NP)",
            "the => (NP['sg']/N['sg']) | (NP['pl']/N['pl'])"
        ])

    def test_semantics_are_parsed(self):
        [book], [the] = itemgetter("book", "the")(lexicon_with_semantics._entries)

        assert isinstance(book, lex.Token)
        assert book.semantics() == ConstantExpression(Variable("book"))

        assert isinstance(the, lex.Token)
        assert the.semantics() == LambdaExpression(Variable("x"), IndividualVariableExpression(Variable("x")))


    def test_semantics_are_printed_right(self):
        assert str(lexicon_with_semantics) == "\n".join([
            "book => N {book}",
            "read => (S/NP) {\\x.read(x)}",
            "the => (NP/N) {\\x.x}"])


    def test_must_include_semantics_if_option_is_set(self):
        with pytest.raises(AssertionError):
            lex.fromstring(grammar, include_semantics=True)


    def test_cannot_used_undeclared_primitives_or_families(self):
        with pytest.raises(AssertionError):
            lex.fromstring("book => N")

    def test_match_brackets(self):
        assert lex.matchBrackets("(foo)") == ("(foo)", "")
        assert lex.matchBrackets("(foo)(bar)(baz)") == ("(foo)", "(bar)(baz)")
        assert lex.matchBrackets("((foo))") == ("((foo))", "")
        assert lex.matchBrackets("((foo)(bar))") == ("((foo)(bar))", "")

        with pytest.raises(AssertionError):
            lex.matchBrackets("(foo")

    def test_var_keyword_is_parsed_as_variable(self):
        assert isinstance(lexicon._entries["and"][0].categ().arg(), CCGVar)

lb = LexiconBuilder()
S, NP, N = lb.primitive_categories("S", "NP", "N")
Det, Pro, IntransV = lb.families({
                            "Det": NP << N,
                            "Pro": NP,
                            "IntransV": S >> NP
                    })

lexicon_from_builder = lb.entries({
                            "the": NP["sg"] << N["sg"],
                            "the": NP["pl"] << N["pl"],
                            "I": Pro,
                            "book": N["sg"],
                            "books": N["pl", "other"],
                            "read": S >> Pro << NP   
                        })

lb = LexiconBuilder()
S, NP, N = lb.primitive_categories("S", "NP", "N")

lexicon_from_builder_with_semantics = lb.entries_with_semantic({
                                        "book": (PrimitiveCategory("N"), ConstantExpression(Variable("book"))),
                                        "the": (NP << N, LambdaExpression(Variable("x"), IndividualVariableExpression(Variable("x")))),
                                        "read": (S << NP,
                                                    LambdaExpression(
                                                        Variable("x"), 
                                                        ApplicationExpression(
                                                            ConstantExpression(Variable("read")), 
                                                            IndividualVariableExpression(Variable("x")))))
                                    })

class TestLexiconBuilder:
    def test_can_declare_primities(self):
        assert lexicon_from_builder._primitives == lexicon._primitives
        assert category_equals(lexicon_from_builder._start.categ(), lexicon._start.categ())

    def test_can_declare_entries(self):
        for ident in ["the", "book", "books"]:
            assert category_equals(lexicon_from_builder._entries[ident][0], lexicon._entries[ident][0])


    def test_families_are_resolved_for_entries(self):
        assert lexicon._entries["I"][0].categ().categ() == "NP"
        assert lexicon_from_builder._entries["I"][0].categ().categ() == "NP"


    def test_can_declare_families(self):
        assert lexicon_from_builder._families.keys() == lexicon._families.keys()

        for ident in lexicon_from_builder._families:
            assert category_equals(lexicon_from_builder._families[ident][0], 
                                    lexicon._families[ident][0])


    def test_can_declare_entries_with_semantics(self):
        for ident in lexicon_with_semantics._entries.keys():
            assert category_equals(lexicon_with_semantics._entries[ident][0], 
                                    lexicon_from_builder_with_semantics._entries[ident][0])

    def test_can_declare_families_with_semantics(self):
        assert lexicon_from_builder_with_semantics._families.keys() == lexicon_with_semantics._families.keys()

        for ident in lexicon_with_semantics._families.keys():
            assert category_equals(lexicon_from_builder_with_semantics._families[ident],
                                        lexicon_with_semantics._families[ident])

    def test_can_declare_multi_argument_functions(self):
        read = lexicon_from_builder._entries["read"][0].categ()
        assert category_equals(read, FunctionalCategory(
                                        FunctionalCategory(
                                            PrimitiveCategory("S"),
                                            PrimitiveCategory("NP"),
                                            Direction("\\", [])), 
                                        PrimitiveCategory("NP"), 
                                        Direction("/", [])))


class TestChart:

    def setup_method(self):
        self.parser = CCGChartParser(lexicon, DefaultRuleSet)
        self.parser_with_semantics = CCGChartParser(lexicon_with_semantics, DefaultRuleSet)

    def test_can_parse_sentences(self, capsys):
        parses = self.parser.parse("I read the book".split(" "))

        parses = list(parses)

        expected_ouputs = map("\n".join, [
            [
                "I      read             the           book",
                " NP  ((S\\NP)/NP)  (NP['sg']/N['sg'])  N['sg']",
                "                 ----------------------------->",
                "                           NP['sg']",
                "    ------------------------------------------>",
                "                      (S\\NP)",
                "----------------------------------------------<",
                "                      S"
            ],
            [
                "I      read             the           book",
                " NP  ((S\\NP)/NP)  (NP['sg']/N['sg'])  N['sg']",
                "    --------------------------------->B",
                "            ((S\\NP)/N['sg'])",
                "    ------------------------------------------>",
                "                      (S\\NP)",
                "----------------------------------------------<",
                "                      S"
            ],
            [
                "I      read             the           book",
                " NP  ((S\\NP)/NP)  (NP['sg']/N['sg'])  N['sg']",
                "---->T",
                "(S/(S\\NP))",
                "                 ----------------------------->",
                "                           NP['sg']",
                "    ------------------------------------------>",
                "                      (S\\NP)",
                "---------------------------------------------->",
                "                      S"
            ],
            [
                "I      read             the           book",
                " NP  ((S\\NP)/NP)  (NP['sg']/N['sg'])  N['sg']",
                "---->T",
                "(S/(S\\NP))",
                "    --------------------------------->B",
                "            ((S\\NP)/N['sg'])",
                "    ------------------------------------------>",
                "                      (S\\NP)",
                "---------------------------------------------->",
                "                      S"
            ],
            [
                "I      read             the           book",
                " NP  ((S\\NP)/NP)  (NP['sg']/N['sg'])  N['sg']",
                "---->T",
                "(S/(S\\NP))",
                "----------------->B",
                "     (S/NP)",
                "                 ----------------------------->",
                "                           NP['sg']",
                "---------------------------------------------->",
                "                      S"
            ],
            [
                "I      read             the           book",
                " NP  ((S\\NP)/NP)  (NP['sg']/N['sg'])  N['sg']",
                "---->T",
                "(S/(S\\NP))",
                "    --------------------------------->B",
                "            ((S\\NP)/N['sg'])",
                "------------------------------------->B",
                "             (S/N['sg'])",
                "---------------------------------------------->",
                "                      S",
            ],
            [
                "I      read             the           book",
                " NP  ((S\\NP)/NP)  (NP['sg']/N['sg'])  N['sg']",
                "---->T",
                "(S/(S\\NP))",
                "----------------->B",
                "     (S/NP)",
                "------------------------------------->B",
                "             (S/N['sg'])",
                "---------------------------------------------->",
                "                      S"
            ],
        ])

        for parse, expected in zip(parses, expected_ouputs):
            printCCGDerivation(parse)

            captured = capsys.readouterr().out.strip()

            assert captured == expected


    def test_can_parse_sentence_with_semantics(self, capsys):
        parses = self.parser_with_semantics.parse(["read", "the", "book"])

        expected_outputs = map("\n".join, [
            [
                "read               the         book",
                " (S/NP) {\\x.read(x)}  (NP/N) {\\x.x}  N {book}",
                "                     ------------------------->",
                "                             NP {book}",
                "---------------------------------------------->",
                "                S {read(book)}"
            ],
            [
                "read               the         book",
                " (S/NP) {\\x.read(x)}  (NP/N) {\\x.x}  N {book}",
                "------------------------------------>B",
                "         (S/N) {\\x.read(x)}",
                "---------------------------------------------->",
                "                S {read(book)}"
            ]
        ])

        for parse, expected in zip(parses, expected_outputs):
            printCCGDerivation(parse)
            captured = capsys.readouterr().out.strip()

            assert captured == expected

    def test_var_can_match_NP(self, capsys):
        printCCGDerivation(next(self.parser.parse(["I", "read", "the", "book", "and", "the", "book"])))
        expected = "\n".join([
            "I      read             the           book               and                    the           book",
            " NP  ((S\\NP)/NP)  (NP['sg']/N['sg'])  N['sg']  ((_var0\\.,_var0)/.,_var0)  (NP['sg']/N['sg'])  N['sg']",
            "                 ----------------------------->",
            "                           NP['sg']",
            "                                                                         ----------------------------->",
            "                                                                                   NP['sg']",
            "                                              -------------------------------------------------------->",
            "                                                               (NP['sg']\\.,NP['sg'])",
            "                 -------------------------------------------------------------------------------------<",
            "                                                       NP['sg']",
            "    -------------------------------------------------------------------------------------------------->",
            "                                                  (S\\NP)",
            "------------------------------------------------------------------------------------------------------<",
            "                                                  S"
        ])

        assert expected == capsys.readouterr().out.strip()

    
    def test_var_can_match_N(self, capsys):
        printCCGDerivation(next(self.parser.parse(["I", "read", "the", "book", "and", "book"])))
        expected = "\n".join([
            "I      read             the           book               and              book",
            " NP  ((S\\NP)/NP)  (NP['sg']/N['sg'])  N['sg']  ((_var0\\.,_var0)/.,_var0)  N['sg']",
            "                                              ------------------------------------>",
            "                                                      (N['sg']\\.,N['sg'])",
            "                                     ---------------------------------------------<",
            "                                                        N['sg']",
            "                 ----------------------------------------------------------------->",
            "                                             NP['sg']",
            "    ------------------------------------------------------------------------------>",
            "                                        (S\\NP)",
            "----------------------------------------------------------------------------------<",
            "                                        S"
        ])

        assert expected == capsys.readouterr().out.strip()

    def test_var_can_match_S(self, capsys):
        printCCGDerivation(next(self.parser.parse(["I", "read", "the", "book", "and", "I", "read", "the", "book"])))
        expected = "\n".join([
            "I      read             the           book               and             I      read             the           book",
            " NP  ((S\\NP)/NP)  (NP['sg']/N['sg'])  N['sg']  ((_var0\\.,_var0)/.,_var0)  NP  ((S\\NP)/NP)  (NP['sg']/N['sg'])  N['sg']",
            "                 ----------------------------->",
            "                           NP['sg']",
            "    ------------------------------------------>",
            "                      (S\\NP)",
            "----------------------------------------------<",
            "                      S",
            "                                                                                          ----------------------------->",
            "                                                                                                    NP['sg']",
            "                                                                             ------------------------------------------>",
            "                                                                                               (S\\NP)",
            "                                                                         ----------------------------------------------<",
            "                                                                                               S",
            "                                              ------------------------------------------------------------------------->",
            "                                                                               (S\\.,S)",
            "-----------------------------------------------------------------------------------------------------------------------<",
            "                                                           S",
        ])

        assert expected == capsys.readouterr().out.strip()


    def test_semantics_are_parsed_correctly(self):
        parse = next(self.parser_with_semantics.parse(["read", "the", "book"]))

        semantic = parse.label()[0].semantics()
        assert str(semantic) == "read(book)"
        assert isinstance(semantic, ApplicationExpression)
        

# TODO: for now this is for testing, should be moved into __eq__ eventually
def category_equals(a, b):
    def both_are_instance(a, b, typ):
        return isinstance(a, typ) and isinstance(b, typ)
    
    if both_are_instance(a, b, lex.Token):
        return (a._token == b._token 
                    and category_equals(a._category, b._category) 
                    and category_equals(a._semantics, b._semantics))
    elif both_are_instance(a, b, PrimitiveCategory):
        return a.categ() == b.categ()
    elif both_are_instance(a, b, FunctionalCategory):
        return (a.dir().dir() == b.dir().dir()
                    and category_equals(a.res(), b.res())
                    and category_equals(a.arg(), b.arg())
        )
    elif both_are_instance(a, b, ConstantExpression):
        return a.variable == b.variable
    elif both_are_instance(a, b, LambdaExpression):
        return (a.variable == b.variable 
                and category_equals(a.term, b.term))
    elif both_are_instance(a, b, IndividualVariableExpression):
        return a.variable == b.variable
    elif both_are_instance(a, b, ApplicationExpression):
        return category_equals(a.function, b.function) and category_equals(a.argument, b.argument)
    elif a is None and b is None:
        return True
    return a == b
