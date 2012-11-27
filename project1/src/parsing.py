"""
Parser for Penn WSJ trees.  

It is basically a dumbed-down version of the S-expression parser provided as
an example of the pyparsing module.  This example is available at:
    http://pyparsing.wikispaces.com/file/view/sexpParser.py
"""
import collections
import decimal

import pyparsing

try:
    from gmpy import mpf as NUM
except ImportError:
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
        if len(node) <= 1:
            terminal_symbols.append(node[0])
            continue

        node_label = node[0]
        nonterminal_symbols.append(node_label)
        child_labels = []
        if isinstance(node[1], basestring):
            child_labels = (node[1],)
        else:
            for child in node[1:]:
                child_labels.append(child[0])
                queue.append(child)
            child_labels = tuple(child_labels)
        if node_label not in rules:
            rules[node_label] = {TOTAL: ZERO}
        if child_labels not in rules[node_label]:
            rules[node_label][child_labels] = ZERO
        rules[node_label][child_labels] += ONE
        rules[node_label][TOTAL] += ONE
    for node_label in rules:
        for child_labels in rules[node_label]:
            if child_labels != TOTAL:
                rules[node_label][child_labels] /= rules[node_label][TOTAL]
                if child_labels not in reverse_lookup:
                    reverse_lookup[child_labels] = {}
                reverse_lookup[child_labels][node_label] = \
                    rules[node_label][child_labels]
    grammar = {'terminals': set(terminal_symbols), 
        'nonterminals': set(nonterminal_symbols), 
        'rules': rules, 
        'start_symbol': start_symbol,
        'revrules': reverse_lookup}
    return grammar


chartItem = collections.namedtuple("chartItem", "prob split is_unary")


def check_unaries(grammar, subchart):
    revrules = grammar['revrules']
    start_symbol = grammar['start_symbol']

    added = True
    while added:
        added = False
        tmp = subchart.copy()
        for target in tmp:
            if (target, ) in revrules:
                for root, prob in revrules[target, ].iteritems():
                    if root == start_symbol:
                        if target not in subchart[root]:# or not subchart[root][target]:
                            subchart[root][target] = chartItem(prob, 0, True)
                            added = True


def cky_parser(grammar, tokens):
    chart = collections.defaultdict(lambda: collections.defaultdict(dict))
    revrules = grammar['revrules']

    for index, token in enumerate(tokens):
        if (token, ) in revrules:
            for root, prob in revrules[token, ].iteritems():
                if token not in chart[index, index + 1][root]:
                    chart[index, index + 1][root][token] = \
                        chartItem(prob, 0, False)
        else:
            # handle unknown words
            pass
        check_unaries(grammar, chart[index, index + 1])
    nwords = len(tokens) + 1
    for span in range(2, nwords):
        for begin in range(nwords - span):
            end = begin+span
            for split in range(begin + 1, end):
                for B in chart[begin, split]:
                    for C in chart[split, end]:
                        if (B, C) in revrules:
                            for root, prob in revrules[B, C].iteritems():
                                if token not in chart[begin, end][root]:
                                    chart[begin, end][root][B, C] = \
                                        chartItem(prob, split, False)
                check_unaries(grammar, chart[begin, end])
    return chart
