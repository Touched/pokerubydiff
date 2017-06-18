import difflib
import re
import math

class DisasmDiff:
    """
    Build objects describing the differences between two disassemblies.
    This is a clone of the parts of difflib that weren't adequately able
    to diff non-text and provide the result as meta data rather than text.
    """
    def __init__(self):
        self.charjunk = None

    def _tabs2spaces(self, line, spaces=8):
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

    def _prepare_lines(self, items):
        return [str(item) + '\n' for item in items]

    def _tag_item(self, tag, item):
        return {
            'opcode': tag,
            'type': item.type(),
            'address': item.address(),
            'size': item.size(),
            'text': str(item),
            'label': item.label,
        }

    def _tag_range(self, tag, it):
        for item in it:
            yield self._tag_item(tag, item)

    def diff(self, original, modified):
        a = list(original)
        b = list(modified)
        al = self._prepare_lines(a)
        bl = self._prepare_lines(b)

        cruncher = difflib.SequenceMatcher(None, al, bl)
        for tag, alo, ahi, blo, bhi in cruncher.get_opcodes():
            if tag == 'replace':
                yield from self._fancy_replace(a, alo, ahi, b, blo, bhi)
            elif tag == 'delete':
                yield from self._tag_range('-', a[alo:ahi])
            elif tag == 'insert':
                yield from self._tag_range('+', b[blo:bhi])
            elif tag == 'equal':
                # The opcodes are equal, but they might have been
                # displaced by earlier sections of code. This means the
                # addresses are not necessarily equal (as addresses are
                # not factored into the diff), and this should be reported
                # as a replacement.
                for left, right in zip(self._tag_range(' ', a[alo:ahi]),
                                       self._tag_range(' ', b[blo:bhi])):
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

        # TODO: Only debug
        with open('diff.html', 'w') as html:
            alc = ['{:50}# {:08x}\n'.format(self._tabs2spaces(str(item)),
                                            item.address()) for item in a]
            blc = ['{:50}# {:08x}\n'.format(self._tabs2spaces(str(item)),
                                            item.address()) for item in b]

            htmldiff = difflib.HtmlDiff()
            html.write(htmldiff.make_file(alc, blc))

    def _plain_replace(self, a, alo, ahi, b, blo, bhi):
        assert alo < ahi and blo < bhi
        # dump the shorter block first -- reduces the burden on short-term
        # memory if the blocks are of very different sizes
        if bhi - blo < ahi - alo:
            yield from self._tag_range('+', b[blo:bhi])
            yield from self._tag_range('-', a[alo:ahi])
        else:
            yield from self._tag_range('-', a[alo:ahi])
            yield from self._tag_range('+', b[blo:bhi])

    def _fancy_replace(self, a, alo, ahi, b, blo, bhi):
        r"""
        When replacing one block of lines with another, search the blocks
        for *similar* lines; the best-matching pair (if any) is used as a
        synch point, and intraline difference marking is done on the
        similar pair. Lots of work, but often worth it.
        Example:
        >>> d = Differ()
        >>> results = d._fancy_replace(['abcDefghiJkl\n'], 0, 1,
        ...                            ['abcdefGhijkl\n'], 0, 1)
        >>> print(''.join(results), end="")
        - abcDefghiJkl
        ?    ^  ^  ^
        + abcdefGhijkl
        ?    ^  ^  ^
        """

        # don't synch up unless the lines have a similarity score of at
        # least cutoff; best_ratio tracks the best score seen so far
        best_ratio, cutoff = 0.74, 0.75
        cruncher = difflib.SequenceMatcher(self.charjunk)
        eqi, eqj = None, None   # 1st indices of equal lines (if any)

        # search for the pair that matches best without being identical
        # (identical lines must be junk lines, & we don't want to synch up
        # on junk -- unless we have to)
        for j in range(blo, bhi):
            bj = str(b[j])
            cruncher.set_seq2(bj)
            for i in range(alo, ahi):
                ai = str(a[i])
                if ai == bj:
                    if eqi is None:
                        eqi, eqj = i, j
                    continue
                cruncher.set_seq1(ai)
                # computing similarity is expensive, so use the quick
                # upper bounds first -- have seen this speed up messy
                # compares by a factor of 3.
                # note that ratio() is only expensive to compute the first
                # time it's called on a sequence pair; the expensive part
                # of the computation is cached by cruncher
                if cruncher.real_quick_ratio() > best_ratio and \
                      cruncher.quick_ratio() > best_ratio and \
                      cruncher.ratio() > best_ratio:
                    best_ratio, best_i, best_j = cruncher.ratio(), i, j
        if best_ratio < cutoff:
            # no non-identical "pretty close" pair
            if eqi is None:
                # no identical pair either -- treat it as a straight replace
                yield from self._plain_replace(a, alo, ahi, b, blo, bhi)
                return
            # no close pair, but an identical pair -- synch up on that
            best_i, best_j, best_ratio = eqi, eqj, 1.0
        else:
            # there's a close pair, so forget the identical pair (if any)
            eqi = None

        # a[best_i] very similar to b[best_j]; eqi is None iff they're not
        # identical

        # pump out diffs from before the synch point
        yield from self._fancy_helper(a, alo, best_i, b, blo, best_j)

        # do intraline marking on the synch pair
        aelt, belt = a[best_i], b[best_j]
        if eqi is None:
            # pump out a '-', '?', '+', '?' quad for the synched lines
            atags = []
            btags = []

            cruncher.set_seqs(str(aelt), str(belt))
            for tag, ai1, ai2, bj1, bj2 in cruncher.get_opcodes():
                if tag == 'replace':
                    atags.append(('^', ai1, ai2))
                    btags.append(('^', bj1, bj2))
                elif tag == 'delete':
                    atags.append(('-', ai1, ai2))
                elif tag == 'insert':
                    btags.append(('+', bj1, bj2))
                elif tag == 'equal':
                    # Ignore equal sections as they do not need
                    # highlighting
                    pass
                else:
                    raise ValueError('unknown tag %r' % (tag,))

            # Labels will sometimes skew the output when they
            # are displayed on their own lines, so ensure that
            # both sets of changes report a label.
            has_label = bool(aelt.label or belt.label)
            fake_label = ('' if has_label else None)

            # Left
            yield {
                **self._tag_item('<', aelt),
                'changes': {
                    'text': atags,
                },
                'label': aelt.label or fake_label,
            }

            # Right
            yield {
                **self._tag_item('>', belt),
                'changes': {
                    'text': btags,
                },
                'label': belt.label or fake_label,
            }
        else:
            # the synch pair is identical
            # TODO:
            yield '  ' + aelt

        # pump out diffs from after the synch point
        yield from self._fancy_helper(a, best_i+1, ahi, b, best_j+1, bhi)

    def _fancy_helper(self, a, alo, ahi, b, blo, bhi):
        if alo < ahi:
            if blo < bhi:
                yield from self._fancy_replace(a, alo, ahi, b, blo, bhi)
            else:
                yield from self._tag_range('-', a[alo:ahi])
        elif blo < bhi:
            yield from self._tag_range('+', b[blo:bhi])
