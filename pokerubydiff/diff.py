import difflib
import re
import math

def prepare_lines(items):
    return [str(item) + '\n' for item in items]


def make_item(item):
    return (item.type(), item.address(), item.size(), str(item), item.label)


def tag_range(tag, it):
    for item in it:
        yield (tag, *make_item(item))


def diff_disassemblies(original, modified):
    a = list(original)
    b = list(modified)
    al = prepare_lines(a)
    bl = prepare_lines(b)

    cruncher = difflib.SequenceMatcher(None, al, bl)
    for tag, alo, ahi, blo, bhi in cruncher.get_opcodes():
        if tag == 'replace':
            # Print shorter block first
            if bhi - blo < ahi - alo:
                yield from tag_range('+', b[blo:bhi])
                yield from tag_range('-', a[alo:ahi])
            else:
                yield from tag_range('+', b[blo:bhi])
                yield from tag_range('-', a[alo:ahi])
        elif tag == 'delete':
            yield from tag_range('-', a[alo:ahi])
        elif tag == 'insert':
            yield from tag_range('+', b[blo:bhi])
        elif tag == 'equal':
            yield from tag_range(' ', a[alo:ahi])
        else:
            raise ValueError('Unkown tag %r' % (tag,))
