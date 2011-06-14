import logging
import os
import re

from django.utils.safestring import mark_safe
from djblets.siteconfig.models import SiteConfiguration

try:
    from enchant import DictWithPWL
    from enchant.tokenize import get_tokenizer, URLFilter, WikiWordFilter, \
                                 EmailFilter, HTMLChunker, Chunker
    has_enchant = True
except ImportError:
    has_enchant = False

try:
    from pygments.formatters.html import _escape_html_table, escape_html
except ImportError:
    # It's possible that this table will move in the future. If so, we want
    # to know, but we don't want to break.
    logging.warning('pygments.formatters.html._escape_html_table could not '
                    'be imported. Falling back on a custom table. Please '
                    'report this!')
    _escape_html_table = {
        ord('&'): u'&amp;',
        ord('<'): u'&lt;',
        ord('>'): u'&gt;',
        ord('"'): u'&quot;',
        ord("'"): u'&#39;',
    }

    def escape_html(text):
        return text.translate(_escape_html_table)


class _HTMLChunker(Chunker):
    """Chunks the content of text within an HTML fragment, stripping tags.

    This is used to handle only the text portions, ignoring anything inside
    a tag. Unlike enchant's HTMLChunker, this also processes entities,
    converting them back to text. The only entities converted are those that
    Pygments otherwise converts in its mapping table.
    """
    _entity_mapping = dict([(v, k) for k, v in _escape_html_table.iteritems()])

    def next(self):
        buf = ''
        entity = ''
        start_chunk = 0
        in_tag = False
        in_entity = False

        offset = self.offset

        for i, c in enumerate(self._text[offset:]):
            if c == '<':
                assert not in_tag
                in_tag = True

                if buf:
                    yield buf, start_chunk
                    buf = ''
            elif c == '>':
                assert in_tag
                in_tag = False
                start_chunk = i + 1
                buf = ''
            elif not in_tag:
                if c == '&':
                    assert not in_entity
                    in_entity = True
                    entity = ''
                elif in_entity:
                    if c == ';':
                        in_entity = False
                        assert entity

                        if entity in self._entity_mapping:
                            buf += unichr(self._entity_mapping[entity])
                        else:
                            # We don't have anything to do. We don't know
                            # what this is. We'll just skip it. It may
                            # affect spell checking, but won't affect the
                            # resulting output otherwise.
                            #
                            # It should really never happen, since we're
                            # assuming input from Pygments, which is specific
                            # about its mapping.
                            pass
                    else:
                        entity += c
                else:
                    buf += c

        if buf:
            yield buf, start_chunk


class EntityChunker(Chunker):
    _entity_mapping = dict([(v, k) for k, v in _escape_html_table.iteritems()])

    def next(self):
        in_entity = False
        entity = ''
        buf = ''
        offset = self.offset

        if offset >= len(self._text):
            raise StopIteration()

        for i, c in enumerate(self._text[offset:]):
            if c == '&':
                assert not in_entity
                in_entity = True
                entity = c
            elif in_entity:
                entity += c

                if c == ';':
                    in_entity = False

                    if entity in self._entity_mapping:
                        buf += unichr(self._entity_mapping[entity])
                    else:
                        # We don't have anything to do. We don't know
                        # what this is. We'll just skip it. It may
                        # affect spell checking, but won't affect the
                        # resulting output otherwise.
                        #
                        # It should really never happen, since we're
                        # assuming input from Pygments, which is specific
                        # about its mapping.
                        pass
            else:
                buf += c

        self.offset = len(self._text)
        print self._text
        print '************ %s' % buf
        return buf, offset


class SpellChecker(object):
    SPELL_CHECKED_SPANS_RE = re.compile('<span class="[sc]">[^<]*</span>')
    SPELLERR_SPAN_START = '<span class="speller">'
    SPELLERR_SPAN_END = '</span>'

    # A list of file extensions we exclude from spell checking.
    # In the future, we may want to make this configurable.
    SPELL_CHECKED_EXCLUSIONS = set([
        '.xml',
        '.svg',
        '.html',
        '.sgml',
    ])

    def __init__(self):
        self.dictionary = None
        self.tokenizer = None

    def can_check(self, filename):
        return (has_enchant and
                os.path.splitext(filename)[1] not in
                self.SPELL_CHECKED_EXCLUSIONS)

    def check_lines(self, lines):
        """Check for spell errors with marked lines.

        For spell errrors in strings and comments, this can change
        their classname to ``spellerr''
        """
        self._init_checker()

        for line in lines:
            new_line = ""
            prev_line_end = 0

            # We only care about strings and comments, and will therefore be
            # looking up each <span> with the appropriate classes.
            for m in self.SPELL_CHECKED_SPANS_RE.finditer(line):
                # From here, we need to be careful about how the content is
                # parsed and replaced. We're parsing HTML, and have to handle
                # text only inbetween tags, and deal with decoding/encoding
                # entities.
                contents = m.group()
                begin = m.start()
                end = begin + len(contents)
                new_contents = ''

                new_line += line[prev_line_end:begin]

                print '>>>>> %s' % contents
                print begin

                new_contents = line[5][:begin]
                contents_offset = 0

                for word, word_pos in self.tokenizer(contents):
                    escaped_len = len(escape_html(word))

                    new_contents += contents[contents_offset:word_pos]
                    contents_offset = word_pos
                    word_end = word_pos + escaped_len
                    print '------ %s' % word
                    print "...... %s" % new_contents
                    print word_pos


                    if not self.dictionary.check(word):
                        print "****** %s" % word

                        new_contents += self.SPELLERR_SPAN_START + \
                                        contents[word_pos:word_end] + \
                                        self.SPELLERR_SPAN_END
                        print '!!!! %s' % contents[word_pos:word_end]
                    else:
                        new_contents += contents[word_pos:word_end]

                    contents_offset += escaped_len

                print "...... %s" % new_contents

                new_contents += contents[contents_offset:]
                print "### %s" % new_contents
                new_line += new_contents

            if not new_line:
                new_line = line

            yield new_line

    def _init_checker(self):
        if self.dictionary:
            return

        siteconfig = SiteConfiguration.objects.get_current()
        lang = siteconfig.get('diffviewer_spell_checking_language')
        dict_dir = siteconfig.get('diffviewer_spell_checking_dir')
        self.dictionary = DictWithPWL(lang, dict_dir)
        self.tokenizer = get_tokenizer(lang,
                                       (EntityChunker, HTMLChunker),
                                       (URLFilter, WikiWordFilter, EmailFilter))
