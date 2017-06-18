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
            # The opcodes are equal, but they might have been
            # displaced by earlier sections of code. This means the
            # addresses are not necessarily equal (as addresses are
            # not factored into the diff), and this should be reported
            # as a replacement.
            for left, right in zip(tag_range(' ', a[alo:ahi]),
                                   tag_range(' ', b[blo:bhi])):
                if left['address'] == right['address']:
                    yield left
                else:
                    changes = {
                        'address': True,
                    }

                    # Labels will sometimes skew the output when they
                    # are displayed on their own lines, so ensure that
                    # both sets of changes report a label.
                    has_label = bool(left['label'] or right['label'])
                    fake_label = ('' if has_label else None)

                    yield {
                        **left,
                        'opcode': '<',
                        'changes': changes,
                        'label': left['label'] or fake_label
                    }

                    yield {
                        **right,
                        'opcode': '>',
                        'changes': changes,
                        'label': right['label'] or fake_label
                    }
        else:
            raise ValueError('Unkown tag %r' % (tag,))

    with open('diff.html', 'w') as html:
        alc = ['{:50}# {:08x}\n'.format(tabs2spaces(str(item)),
                                        item.address()) for item in a]
        blc = ['{:50}# {:08x}\n'.format(tabs2spaces(str(item)),
                                        item.address()) for item in b]

        htmldiff = difflib.HtmlDiff()
        html.write(htmldiff.make_file(alc, blc))
