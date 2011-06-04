import re

from djblets.siteconfig.models import SiteConfiguration
from enchant import DictWithPWL
from enchant.checker import SpellChecker
from enchant.tokenize import EmailFilter, URLFilter


siteconfig = SiteConfiguration.objects.get_current()
language = siteconfig.get('diffviewer_spell_checking_language')
pwl = siteconfig.get('diffviewer_spell_checking_dir')

spell_checker_cache = {}

class SpellCheckerWithPWL(SpellChecker):
    """Implement a spell checker with personal word list."""

    def __init__(self, pwl=None, *args, **kwargs):
        SpellChecker.__init__(self, *args, **kwargs)
        if pwl:
            self.dict = DictWithPWL(self.lang, pwl)


def get_spell_checker(language, pwl):
    """Retrieve a spell checker if it is in cache, otherwise create one."""

    if (language, pwl) not in spell_checker_cache:
        spell_checker_cache[language, pwl] = SpellCheckerWithPWL(
                                             lang=language, pwl=pwl,
                                             filters=[EmailFilter, URLFilter])

    return spell_checker_cache[language, pwl]

spell_checker = get_spell_checker(language, pwl)
