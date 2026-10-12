"""Compiled resources ship ready to run, independently of external PBX doubles."""
import gettext
import unittest

from boundary_support import ROOT


class TranslationCatalog(unittest.TestCase):
    def test_spanish_catalog_aliases_include_management_and_routing_messages(self):
        expected = {
            'Fail Over Destination': 'Destino de contingencia',
            'Continue Destination': 'Destino al continuar',
            'Delete Profile': 'Eliminar perfil',
            'Profile deleted.': 'Perfil eliminado.',
        }
        for locale in ('es', 'es_ES', 'es_AR'):
            with (ROOT / 'module/i18n' / locale / 'LC_MESSAGES/callflowhooks.mo').open('rb') as stream:
                translations = gettext.GNUTranslations(stream)
            for message, translation in expected.items():
                self.assertEqual(translations.gettext(message), translation, locale)
            for message in ('Handler Time Limit', 'Digit Entry Timeout',
                            'Confirm deletion of this profile. This removes its configuration and credentials.'):
                self.assertNotEqual(translations.gettext(message), message, locale)

    def test_unknown_and_user_authored_text_is_preserved(self):
        with (ROOT / 'module/i18n/es_ES/LC_MESSAGES/callflowhooks.mo').open('rb') as stream:
            translations = gettext.GNUTranslations(stream)
        self.assertEqual(translations.gettext('Atención de la obra social del cliente'),
                         'Atención de la obra social del cliente')
        self.assertEqual(gettext.NullTranslations().gettext('Fail Over Destination'),
                         'Fail Over Destination')
