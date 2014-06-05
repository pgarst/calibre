#!/usr/bin/env python
# vim:fileencoding=utf-8

from lxml import html
from lxml import etree
import sys;sys.path.append(r'/home/peterg/tools/eclipse/plugins/org.python.pydev_3.3.3.201401272249/pysrc')

"""
The goal is to use Calibre to convert a docx manuscript to an epub format ebook.
There are several critical shortcomings to the calibre output, both
structurally and stylistically.
The plan is to add steps to fix the structural issues, and supply a css file to
fix the style issues.
This file contains material to clean up lists, which have a number of problems
in the base version.
When a list has paragraphs between the list items, word sets it up as
multiple lists, with a value attribute on the first item of subsequent
lists to resynchronize. In the epub for this leads to formatting errors on
the intermediate paragraphs, and epubcheck complaints because of the value
attribute, and because epubcheck is full of crap.
The goal is to make the intermediate paragraphs (or end paragraphs) child nodes
of the li nodes, and to merge ol units into a single list with no value
attributes.

Do we want to adjust this at the xml level or the html level?
html level, although we have to map the styles there.

The algorithm here does not work in general, but should work for our
material. We have these significant elements:
    opening ol node
    closing ol node
    li node, no value attribute
    li node with a value attribute
    other list related node - i.e. ListNumber... etc.
    other node

The algorithm is:

    If we find li with value, find previous li, in a previous ol block.
    Drop old close and open, drop value attribute, and make all other
    nodes between the li nodes children of the previous li node.

    If we find other list related node immediate outside of ol block,
    then make it and intervening nodes a child of the last li element.
"""

# We have two ol lists to join.
def join2 (parent, i1, i2):
    # print('JOIN', i1, '  ', i2)
    list1 = parent[i1]
    list2 = parent[i2]

    # Drop value attribute from first list item in second list.
    liv = list2[0]
    liv.attrib.pop('value')

    # Everything between lists becomes a child of last list item
    last = list1[-1]
    for i in range(i1+1, i2):
        last.append(parent[i])

    # Items in second list become children of first list
    for e in list2:
        list1.append(e)

    # Drop second list
    if list2 in parent:
        parent.remove(list2)

def join_doc_list(node):
    li = node[0]
    val = li.get('value', 0)
    if val == 0:
        return
    p = node.getparent()
    i2 = p.index(node)
    for i1 in range(i2-1,0,-1):
        # print('Try index ', i1)
        prev = p[i1]
        if prev.tag == 'ol':
            join2(p, i1, i2)
            return

def join_doc_lists(html):
    # print('TRY ', html.tag)
    if html.tag == 'ol':
        join_doc_list(html)
    else:
        for el in html:
            join_doc_lists(el)

# We may have a list with some list continuation items after the last item.
# If so, we want to make them children of the last list item.
# This gets complicated because there may be other paragraphs, like code,
# which are not always list continuation things but which may be if they 
# are followed by other list continuations.
# To simplify indexing, just make one addition, if possible,
# and then return true.
def join_trailing(html, contlist):
    p = html.getparent()
    base = p.index(html)
    s = base
    last = html[-1]
    while True:
        s = s + 1
        if s >= len(p):
            return False
        nd = p[s]
        if nd.tag == 'ol':
            return False
        cl = nd.get('class', '')
        if cl in contlist:
            for ind in range(base+1, s+1):
                last.append(p[base+1])
            return True

def join_trailing_items(html, contlist):
    if html.tag == 'ol':
        while join_trailing(html, contlist):
            pass
    else:
        for e in html:
            join_trailing_items(e, contlist)

def cleanup_lists (html, styles):
    # import pydevd;pydevd.settrace()
    # raw = etree.tostring(html, encoding='utf-8', doctype='<!DOCTYPE html>')
    # print(raw)

    # Find list related blocks.
    # This is ListNumber and ListNumber..., since calibre maps 
    # sublists to non-li elements
    contlist = styles.stylemap.get('ListNumber...', [])
    contlist.extend(styles.stylemap.get('ListNumber', []))
    contlist.extend(styles.stylemap.get('ListNumber2...', []))
    contlist.extend(styles.stylemap.get('ListBullet', []))
    contlist.extend(styles.stylemap.get('>ListBullet...', []))

    # First look for joinable lists, then look for trailing units.
    join_doc_lists(html)
    join_trailing_items(html, contlist)

    return
