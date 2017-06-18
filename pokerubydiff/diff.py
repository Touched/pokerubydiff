import difflib
import re
import math

def tabs2spaces(line, spaces=8):
    """
    Converts tabs to spaces.
    """

    res = ''
    n = 0
    for c in line:
        if c == '\t':
            next_tab_stop = n + spaces - (n % spaces)
            distance_to_next = next_tab_stop - n
            res += ' ' * distance_to_next
            n = next_tab_stop
        else:
            res += c
            n += 1

    return res

def prepare_lines(items):
    return [str(item) + '\n' for item in items]


def tag_range(tag, it):
    for item in it:
        yield {
            'opcode': tag,
            'type': item.type(),
            'address': item.address(),
            'size': item.size(),
            'text': str(item),
            'label': item.label,
        }


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
                yield from tag_range('-', a[alo:ahi])
                yield from tag_range('+', b[blo:bhi])
        elif tag == 'delete':
            yield from tag_range('-', a[alo:ahi])
        elif tag == 'insert':
            yield from tag_range('+', b[blo:bhi])
        elif tag == 'equal':
            # FIXME: The opcodes are equal, but this is reporting the address as equal too.
            # Proper inline replacement must be done and reported to the diff client.
            # Inline diff mode should be disabled too since that makes no sense
            yield from tag_range(' ', a[alo:ahi])
        else:
            raise ValueError('Unkown tag %r' % (tag,))

    with open('diff.html', 'w') as html:
        alc = ['{:50}# {:08x}\n'.format(tabs2spaces(str(item)), item.address()) for item in a]
        blc = ['{:50}# {:08x}\n'.format(tabs2spaces(str(item)), item.address()) for item in b]

        htmldiff = difflib.HtmlDiff()
        html.write(htmldiff.make_file(alc, blc))
