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
    opening ol or ul node
    closing ol or ul node
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

def list_tag (tag):
    if tag == 'ol':
        return tag
    if tag == 'ul':
        return tag
    return None

def dumpelem(msg, html):
    # print(msg)
    # raw = etree.tostring(html) # , encoding='utf-8'), doctype='<!DOCTYPE html>')
    # print(raw)
    pass

# We have two ol lists to join.
def join2 (parent, i1, i2):
    list1 = parent[i1]
    list2 = parent[i2]

    dumpelem('LIST 1', list1)

    # Drop value attribute from first list item in second list.
    liv = list2[0]
    liv.attrib.pop('value')

    # Everything between lists becomes a child of last list item
    last = list1[-1]
    for i in range(i1+1, i2):
        last.append(parent[i1+1])

    # Items in second list become children of first list
    for e in list2:
        list1.append(e)

    dumpelem('LIST 2', list1)

    # Drop second list
    if list2 in parent:
        parent.remove(list2)
    dumpelem('Parent', parent)

# Need to adjust this for ul case - then we don't have value node.
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

    if list_tag(html.tag) != None:
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
def join_trailing(html, contlist, immedlist):
    p = html.getparent()
    base = p.index(html)
    s = base
    last = html[-1]
    # print('START append ', last.get('class', 'X'))
    # raw = etree.tostring(last) # , encoding='utf-8', doctype='<!DOCTYPE html>')
    # print(raw)
    while True:
        s = s + 1
        if s >= len(p):
            return False
        nd = p[s]
        if nd.tag == 'ol':
            return False
        if nd.tag == 'ul':
            return False
        cl = nd.get('class', '')
        if cl in immedlist and (s == (base+1)):
            last.append(p[base+1])
            return True
        if cl in contlist:
            for ind in range(base+1, s+1):
                last.append(p[base+1])
            return True

def join_trailing_items(html, contlist, immedlist, depth):
    # If this node contains a list, we may merge following elements into it,
    # thus messing up the iteration over the list.
    # To handle this we iterate backwards, by index.
    tag = list_tag(html.tag)
    if tag == None:
        for i in xrange(len(html) - 1, -1, -1):
            join_trailing_items(html[i], contlist, immedlist, depth+1)
    else:
        while join_trailing(html, contlist, immedlist):
            pass

def cleanup_lists (html, styles):
    # import pydevd;pydevd.settrace()
    print('CLEANUP:')
    # raw = etree.tostring(html) # , encoding='utf-8', doctype='<!DOCTYPE html>')
    # print(raw)
    # raw = etree.tostring(html, xml_declaration=True) # , encoding='utf-8', doctype='<!DOCTYPE html>')
    # print(raw)
    # raw = etree.tostring(html, xml_declaration=True, pretty_print=True) # , encoding='utf-8', doctype='<!DOCTYPE html>')
    # print(raw)

    # Find list related blocks.
    # This is ListNumber and ListNumber..., since calibre maps 
    # sublists to non-li elements
    contlist = styles.stylemap.get('ListNumber...', [])
    contlist.extend(styles.stylemap.get('ListNumber', []))
    contlist.extend(styles.stylemap.get('ListNumber2...', []))
    contlist.extend(styles.stylemap.get('ListBullet', []))
    contlist.extend(styles.stylemap.get('>ListBullet...', []))

    # Some styles we want to append if they come immediately after
    immedlist = styles.stylemap.get('Code', [])

    # First look for joinable lists, then look for trailing units.
    join_doc_lists(html)
    join_trailing_items(html, contlist, immedlist, 0)

    return
