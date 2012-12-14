#!/usr/bin/python
# coding: utf-8
"""
Parser for Penn WSJ trees.  

It is basically a dumbed-down version of the S-expression parser provided as
an example of the pyparsing module.  This example is available at:
    http://pyparsing.wikispaces.com/file/view/sexpParser.py
"""
import collections
import decimal
import threading

import pyparsing

""" Nice idea, but doesn't work out as planned when moving pickled files
try:
    from gmpy import mpf as NUM
except ImportError:
    from decimal import Decimal as NUM
"""
from decimal import Decimal as NUM

ONE = NUM(1)
ZERO = NUM(0)

# Define punctuation literals
LPAR, RPAR, LBRK, RBRK, LBRC, RBRC = map(pyparsing.Suppress, "()[]{}")

# The symbols a token can contain
token = pyparsing.Word(pyparsing.alphanums + "-./_:;*+=!<>@&`',?%#$\\")

display = LBRK + token + RBRK
string_ = pyparsing.Optional(display) + token

sexp = pyparsing.Forward()
sexpList = pyparsing.Group(LPAR + pyparsing.ZeroOrMore(sexp) + RPAR)
sexp << (string_ | sexpList)

class TOTAL: 
    """Used as a symbolic value in the rule table of probabilistic grammars.
    """
    pass


class UNKNOWN:
    """Used as a symbolic value in the rule table of probabilistic grammars.

    Its main purpose is as a unique symbol correlating the probability for
    applying a rule to a unknown right hand side.
    """
    pass


def get_tree(text_tree):
    """Returns a nested list of strings representing the textual parse tree.

    The tokens are not interpreted.  For example, numerical-valued leaf nodes
    are still represented as strings in the tree.
    
    Args:
        text_tree: a string representation of a single parse tree. These are
            defined by the Penn WSJ database.  A sample input is:
                "(TOP (INTJ (UH damn) (. !)) )"
    
    Returns:
        The parse tree of the input, represented in a list datastructure.  For
        example:
            ['TOP', ['INTJ', ['UH, 'damn'], ['.', '!']]]
    """
    return sexp.parseString(text_tree, parseAll=True).asList()[0]


def parse_tree_file(tree_file):
    """Parse every line of the given file into a nested list of strings.

    This returns a generator of nested lists of strings.  Each element
    represents a single tree from the input file.

    Args:
        tree_file: a file where every line contains an s-expression,
            representing a parse tree.

    Returns: 
        A generator which contains a nested list representation of the
        tree/s-expression which is on each single line of the file.
    """
    for text_tree in tree_file:
        yield get_tree(text_tree)


def deduce_grammar(tree_collection):
    """Extracts the frequency of node transitions.
    
    Args:
        tree_collection: an iterable of syntax trees, such as those outputted
        by get_tree.

    Returns:
        A ``2D'' dictionary, where the first entry represents the starting node, and
        the second key refers to the set of child nodes.  The associated value
        is the frequency of this transition.

        Each starting node entry contains a special entry, which contains the
        total frequency of the starting node.
    """
    queue = list(tree_collection)

    terminal_symbols = []
    nonterminal_symbols = []
    rules = {} 
    start_symbol = queue[0][0]
    reverse_lookup = {}
    while queue:
        node = queue.pop()

        node_label = node[0]
        nonterminal_symbols.append(node_label)
        child_labels = []
        if isinstance(node[1], basestring):
            child_labels = (node[1],)
            terminal_symbols.append(node[1])
        else:
            for child in node[1:]:
                child_labels.append(child[0])
                queue.append(child)
            child_labels = tuple(child_labels)
        if node_label not in rules:
            rules[node_label] = {TOTAL: ZERO, UNKNOWN: ONE}
        if child_labels not in rules[node_label]:
            rules[node_label][child_labels] = ZERO
        rules[node_label][child_labels] += ONE
        rules[node_label][TOTAL] += ONE
    for node_label in rules:
        for child_labels in rules[node_label]:
            if child_labels is not TOTAL:
                rules[node_label][child_labels] /= rules[node_label][TOTAL]
                if child_labels not in reverse_lookup:
                    reverse_lookup[child_labels] = {}
                reverse_lookup[child_labels][node_label] = \
                    rules[node_label][child_labels]
    parts_of_speech = []
    for terminal in terminal_symbols:
        parts_of_speech.extend(reverse_lookup[terminal,].keys())
    parts_of_speech = set(parts_of_speech)
    for part_of_speech in parts_of_speech.copy():
        removed = False
        for child_labels in rules[part_of_speech]:
            if child_labels is TOTAL:
                del rules[part_of_speech][TOTAL]
            elif child_labels is UNKNOWN:
                rules[part_of_speech][UNKNOWN] = \
                    min(rules[part_of_speech].items(),
                        key=lambda item: item[1])
            elif len(child_labels) > 1:
                parts_of_speech.remove(part_of_speech)
                break
    grammar = {'terminals': set(terminal_symbols), 
        'nonterminals': set(nonterminal_symbols), 
        'rules': rules, 
        'start_symbol': start_symbol,
        'revrules': reverse_lookup,
        'pos': parts_of_speech}
    return grammar


chartItem = collections.namedtuple("chartItem", "prob split children")


starting = lambda word_inits: lambda token: max(map(token.startswith,
    word_inits))
ending = lambda word_ends: lambda token: max(map(token.endswith, word_ends))
contains = lambda substrs: lambda token: max(substr in token for substr in 
    substrs)
is_in = lambda tokens: lambda token: token in tokens
of_length = lambda length: lambda token: len(token) == length


def is_number(token):
    try: 
        for subtoken in token.split(':'):
            float(token)
    except:
        return False
    return True


pos_guesses = {
    is_number: ["CD"], # floating point number
    is_in([u"€", u"¤", u"¢", u"£", u"₤"]): ["$"], # monetary symbols
    ending(["able"]): ["JJ"], # adjective
    ending(["ed"]): ["VBG", "VBN"], # past participle, past tense
    ending(["y"]): ["RB"], # adverb
    ending(["ier"]): ["RBR"], # comparative adverb
    ending(["iest"]): ["RBS"], # superlative adverb
    ending(["ion"]): ["NN", "NNP"], # nouns, proper nouns
    ending(["er"]): ["JJR", "NN"], # comparative adjective, noun
    ending(["ist"]): ["JJS", "NN", "NNP"], 
        # superlative adjective, (proper) noun
    ending(["ing"]): ["VBG", "NN", "NNP", "JJ"], 
        # present participle, noun, proper noun, adjective
    ending(["s"]): ["NNS", "NNPS", "VBZ"], 
        # plural (proper) noun, 2nd person verb
    of_length(1): ["SYM"], # letters as symbols and punctuation marks
    starting(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")): ["NNP", "NNPS"], 
        # proper noun
    contains(["-"]): ["NNP", "JJ", "VB"], # just a guess...
    (lambda x: True): ["NNP", "NNPS"], # If nothing else matches, it's probably a name
}


def rulebased_postag(token):
    for rule, postags in pos_guesses.items():
        if rule(token):
            return postags
    raise RuntimeError("Unknown token: %s" % token)

def check_unaries(grammar, chart, begin, end):
    revrules = grammar['revrules']
    start_symbol = grammar['start_symbol']

    added = True
    while added:
        added = False
        for B in chart[begin, end].keys():
            if (B, ) in revrules:
                for A, p_AB in revrules[B, ].iteritems():
                    prob = p_AB * chart[begin, end][B].prob
                    if prob > chart[begin, end][A].prob:
                        chart[begin, end][A] = chartItem(prob, end, [B])
                        added = True


def cky_parser(grammar, tokens):
    chart = collections.defaultdict(lambda: collections.defaultdict(lambda:
        chartItem(-1, 0, [':('])))
    rules = grammar['rules']
    revrules = grammar['revrules']

    for index, token in enumerate(tokens):
        if (token, ) in revrules:
            for root, prob in revrules[token, ].iteritems():
                if chart[index, index + 1][root].prob < prob:
                    chart[index, index + 1][root] = \
                        chartItem(prob, index + 1, [token])
        else:
            # handle unknown words
            print "Unknown word:", token
            possible_tags = rulebased_postag(token)
            for tag in possible_tags:
                prob = rules[tag][UNKNOWN]
                chart[index, index + 1][tag] = \
                    chartItem(prob, index + 1, [token])
        check_unaries(grammar, chart, index, index + 1)
    nwords = len(tokens) + 1
    for span in range(2, nwords):
        for begin in range(nwords - span):
            end = begin + span
            for split in range(begin + 1, end):
                for B in chart[begin, split]:
                    for C in chart[split, end]:
                        if (B, C) in revrules:
                            p_B = chart[begin, split][B].prob
                            p_C = chart[split, end][C].prob
                            for root, prob in revrules[B, C].items():
                                p_ = p_B * p_C * prob
                                p_root = chart[begin, end][root].prob
                                if p_root < p_:
                                    chart[begin, end][root] = \
                                        chartItem(p_, split, [B, C])
                check_unaries(grammar, chart, begin, end)
    return chart


def viterbi(chart, root, begin, end):
    if root in chart[begin, end]:
        tree = [root]
        next_node, data = max(chart[begin, end].items(), key=lambda item: item[1].prob)
        #print "%s: %s, %s" % (begin, next_node, data)
        if len(data.children) == 1:
            if data.children[0] == root:
                tree.append(data.children[0])
            else:
                tree.append(viterbi(chart, data.children[0], begin, end))
        else:
            tree.append(viterbi(chart, 
                                  data.children[0], 
                                  begin, 
                                  data.split))
            tree.append(viterbi(chart, 
                                  data.children[1], 
                                  data.split,
                                  end))
        return tree
    return root


def debinarize_tree(tree):
    return tree


def tree_to_string(tree):
    if isinstance(tree, basestring):
        return str(tree)
    return "(" + " ".join([tree_to_string(node) for node in tree]) + ")"


def test(tokens):
    import cPickle
    print "Loading pcfg"
    g = cPickle.load(file('pcfg.pkl'))
    if tokens == 1:
        tokens = "New York is new ."
    elif tokens == 2:
        tokens = "I walk bdsadasdasdasravely"
    elif tokens == 3:
        tokens = "Now is the time"
    tokens = tokens.split(" ")
    print "Parsing '%s'" % " ".join(tokens)
    chart = cky_parser(g, tokens)
    print "Chart size:", len(chart)
    #chartprint(chart)
    print "Viterbi-time!"
    print tree_to_string(debinarize_tree(
        viterbi(chart, g['start_symbol'], 0, len(tokens))))
    return chart

def chartprint(chart):
    i = 0
    for key, innerdict in chart.items():
        for innerkey, value in innerdict.items():
            i += 1
            print "%s, %s -> %s" % (key, innerkey, " ".join(value.children))
    print "Total size: %d" % i
