# coding=utf-8
# Copyright (C) 2016 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR GPL-3.0-only WITH Qt-GPL-exception-1.0

from typing import Final, NamedTuple

from qtpy.QtCore import QLocale

Q_EQ: Final[int] = 0x01
Q_LT: Final[int] = 0x02
Q_LEQ: Final[int] = 0x03
Q_BETWEEN: Final[int] = 0x04

Q_NOT: Final[int] = 0x08
Q_MOD_10: Final[int] = 0x10
Q_MOD_100: Final[int] = 0x20
Q_LEAD_1000: Final[int] = 0x40

Q_AND: Final[int] = 0xFD
Q_OR: Final[int] = 0xFE
Q_NEWRULE: Final[int] = 0xFF

Q_OP_MASK: Final[int] = 0x07

Q_NEQ: Final[int] = Q_NOT | Q_EQ
Q_GT: Final[int] = Q_NOT | Q_LEQ
Q_GEQ: Final[int] = Q_NOT | Q_LT
Q_NOT_BETWEEN: Final[int] = Q_NOT | Q_BETWEEN

englishStyleRules: Final[bytes] = bytes([Q_EQ, 1])
frenchStyleRules: Final[bytes] = bytes([Q_LEQ, 1])
latvianRules: Final[bytes] = bytes([Q_MOD_10 | Q_EQ, 1, Q_AND, Q_MOD_100 | Q_NEQ, 11, Q_NEWRULE,
                                    Q_NEQ, 0])
icelandicRules: Final[bytes] = bytes([Q_MOD_10 | Q_EQ, 1, Q_AND, Q_MOD_100 | Q_NEQ, 11])
irishStyleRules: Final[bytes] = bytes([Q_EQ, 1, Q_NEWRULE,
                                       Q_EQ, 2])
gaelicStyleRules: Final[bytes] = bytes([Q_EQ, 1, Q_OR, Q_EQ, 11, Q_NEWRULE,
                                        Q_EQ, 2, Q_OR, Q_EQ, 12, Q_NEWRULE,
                                        Q_BETWEEN, 3, 19])
slovakStyleRules: Final[bytes] = bytes([Q_EQ, 1, Q_NEWRULE,
                                        Q_BETWEEN, 2, 4])
macedonianRules: Final[bytes] = bytes([Q_MOD_10 | Q_EQ, 1, Q_NEWRULE,
                                       Q_MOD_10 | Q_EQ, 2])
lithuanianRules: Final[bytes] = bytes([Q_MOD_10 | Q_EQ, 1, Q_AND, Q_MOD_100 | Q_NEQ, 11, Q_NEWRULE,
                                       Q_MOD_10 | Q_NEQ, 0, Q_AND, Q_MOD_100 | Q_NOT_BETWEEN, 10, 19])
russianStyleRules: Final[bytes] = bytes([Q_MOD_10 | Q_EQ, 1, Q_AND, Q_MOD_100 | Q_NEQ, 11, Q_NEWRULE,
                                         Q_MOD_10 | Q_BETWEEN, 2, 4, Q_AND, Q_MOD_100 | Q_NOT_BETWEEN, 10, 19])
polishRules: Final[bytes] = bytes([Q_EQ, 1, Q_NEWRULE,
                                   Q_MOD_10 | Q_BETWEEN, 2, 4, Q_AND, Q_MOD_100 | Q_NOT_BETWEEN, 10, 19])
romanianRules: Final[bytes] = bytes([Q_EQ, 1, Q_NEWRULE,
                                     Q_EQ, 0, Q_OR, Q_MOD_100 | Q_BETWEEN, 1, 19])
slovenianRules: Final[bytes] = bytes([Q_MOD_100 | Q_EQ, 1, Q_NEWRULE,
                                      Q_MOD_100 | Q_EQ, 2, Q_NEWRULE,
                                      Q_MOD_100 | Q_BETWEEN, 3, 4])
malteseRules: Final[bytes] = bytes([Q_EQ, 1, Q_NEWRULE,
                                    Q_EQ, 0, Q_OR, Q_MOD_100 | Q_BETWEEN, 1, 10, Q_NEWRULE,
                                    Q_MOD_100 | Q_BETWEEN, 11, 19])
welshRules: Final[bytes] = bytes([Q_EQ, 0, Q_NEWRULE,
                                  Q_EQ, 1, Q_NEWRULE,
                                  Q_BETWEEN, 2, 5, Q_NEWRULE,
                                  Q_EQ, 6])
arabicRules: Final[bytes] = bytes([Q_EQ, 0, Q_NEWRULE,
                                   Q_EQ, 1, Q_NEWRULE,
                                   Q_EQ, 2, Q_NEWRULE,
                                   Q_MOD_100 | Q_BETWEEN, 3, 10, Q_NEWRULE,
                                   Q_MOD_100 | Q_GEQ, 11])
tagalogRules: Final[bytes] = bytes([Q_LEQ, 1, Q_NEWRULE,
                                    Q_MOD_10 | Q_EQ, 4, Q_OR, Q_MOD_10 | Q_EQ, 6, Q_OR, Q_MOD_10 | Q_EQ, 9])

japaneseStyleForms: Final[list[str]] = ["Universal Form"]
englishStyleForms: Final[list[str]] = ["Singular", "Plural"]
frenchStyleForms: Final[list[str]] = ["Singular", "Plural"]
icelandicForms: Final[list[str]] = ["Singular", "Plural"]
latvianForms: Final[list[str]] = ["Singular", "Plural", "Nullar"]
irishStyleForms: Final[list[str]] = ["Singular", "Dual", "Plural"]
# Gaelic uses the grammatical Singular for the Plural cardinality,
# so using the Latin terms is expected to cause confusion.
gaelicStyleForms: Final[list[str]] = ["1/11", "2/12", "Few", "Many"]
slovakStyleForms: Final[list[str]] = ["Singular", "Paucal", "Plural"]
macedonianForms: Final[list[str]] = ["Singular", "Dual", "Plural"]
lithuanianForms: Final[list[str]] = ["Singular", "Paucal", "Plural"]
russianStyleForms: Final[list[str]] = ["Singular", "Dual", "Plural"]
polishForms: Final[list[str]] = ["Singular", "Paucal", "Plural"]
romanianForms: Final[list[str]] = ["Singular", "Paucal", "Plural"]
slovenianForms: Final[list[str]] = ["Singular", "Dual", "Trial", "Plural"]
malteseForms: Final[list[str]] = ["Singular", "Paucal", "Greater Paucal", "Plural"]
welshForms: Final[list[str]] = ["Nullar", "Singular", "Dual", "Sexal", "Plural"]
arabicForms: Final[list[str]] = ["Nullar", "Singular", "Dual", "Minority Plural", "Plural", "Plural (100-102, ...)"]
tagalogForms: Final[list[str]] = ["Singular", "Plural (consonant-ended)", "Plural (vowel-ended)"]

japaneseStyleLanguages: Final[list[QLocale.Language]] = [
    QLocale.Language.Bislama,
    QLocale.Language.Burmese,
    QLocale.Language.Chinese,
    QLocale.Language.Dzongkha,
    QLocale.Language.Fijian,
    QLocale.Language.Guarani,
    QLocale.Language.Hungarian,
    QLocale.Language.Indonesian,
    QLocale.Language.Japanese,
    QLocale.Language.Javanese,
    QLocale.Language.Korean,
    QLocale.Language.Malay,
    QLocale.Language.NauruLanguage,
    QLocale.Language.Oromo,
    QLocale.Language.Persian,
    QLocale.Language.Sundanese,
    QLocale.Language.Tatar,
    QLocale.Language.Thai,
    QLocale.Language.Tibetan,
    QLocale.Language.Turkish,
    QLocale.Language.Vietnamese,
    QLocale.Language.Yoruba,
    QLocale.Language.Zhuang,
]
englishStyleLanguages: Final[list[QLocale.Language]] = [
    QLocale.Language.Abkhazian,
    QLocale.Language.Afar,
    QLocale.Language.Afrikaans,
    QLocale.Language.Albanian,
    QLocale.Language.Amharic,
    QLocale.Language.Assamese,
    QLocale.Language.Aymara,
    QLocale.Language.Azerbaijani,
    QLocale.Language.Bashkir,
    QLocale.Language.Basque,
    QLocale.Language.Bengali,
    QLocale.Language.Bulgarian,
    QLocale.Language.Catalan,
    QLocale.Language.Cornish,
    QLocale.Language.Corsican,
    QLocale.Language.Danish,
    QLocale.Language.Dutch,
    QLocale.Language.English,
    QLocale.Language.Esperanto,
    QLocale.Language.Estonian,
    QLocale.Language.Faroese,
    QLocale.Language.Finnish,
    QLocale.Language.Friulian,
    QLocale.Language.WesternFrisian,
    QLocale.Language.Galician,
    QLocale.Language.Georgian,
    QLocale.Language.German,
    QLocale.Language.Greek,
    QLocale.Language.Greenlandic,
    QLocale.Language.Gujarati,
    QLocale.Language.Hausa,
    QLocale.Language.Hebrew,
    QLocale.Language.Hindi,
    QLocale.Language.Interlingua,
    QLocale.Language.Interlingue,
    QLocale.Language.Italian,
    QLocale.Language.Kannada,
    QLocale.Language.Kashmiri,
    QLocale.Language.Kazakh,
    QLocale.Language.Khmer,
    QLocale.Language.Kinyarwanda,
    QLocale.Language.Kirghiz,
    QLocale.Language.Kurdish,
    QLocale.Language.Lao,
    QLocale.Language.Latin,
    QLocale.Language.Lingala,
    QLocale.Language.Luxembourgish,
    QLocale.Language.Malagasy,
    QLocale.Language.Malayalam,
    QLocale.Language.Marathi,
    QLocale.Language.Mongolian,
    # Missing: Nahuatl,
    QLocale.Language.Nepali,
    QLocale.Language.NorthernSotho,
    QLocale.Language.NorwegianBokmal,
    QLocale.Language.NorwegianNynorsk,
    QLocale.Language.Occitan,
    QLocale.Language.Oriya,
    QLocale.Language.Pashto,
    QLocale.Language.Portuguese,
    QLocale.Language.Punjabi,
    QLocale.Language.Quechua,
    QLocale.Language.Romansh,
    QLocale.Language.Rundi,
    QLocale.Language.Shona,
    QLocale.Language.Sindhi,
    QLocale.Language.Sinhala,
    QLocale.Language.Somali,
    QLocale.Language.SouthernSotho,
    QLocale.Language.Spanish,
    QLocale.Language.Swahili,
    QLocale.Language.Swati,
    QLocale.Language.Swedish,
    QLocale.Language.Tajik,
    QLocale.Language.Tamil,
    QLocale.Language.Telugu,
    QLocale.Language.Tongan,
    QLocale.Language.Tsonga,
    QLocale.Language.Tswana,
    QLocale.Language.Turkmen,
    QLocale.Language.Uigur,
    QLocale.Language.Urdu,
    QLocale.Language.Uzbek,
    QLocale.Language.Volapuk,
    QLocale.Language.Wolof,
    QLocale.Language.Xhosa,
    QLocale.Language.Yiddish,
    QLocale.Language.Zulu,
] + ([QLocale.Language.Nahuatl] if hasattr(QLocale.Language, 'Nahuatl') else [])
frenchStyleLanguages: Final[list[QLocale.Language]] = [
    # keep synchronized with frenchStyleCountries
    QLocale.Language.Armenian,
    QLocale.Language.Breton,
    QLocale.Language.French,
    QLocale.Language.Portuguese,
    QLocale.Language.Filipino,
    QLocale.Language.Tigrinya,
    QLocale.Language.Walloon,
]
latvianLanguage: Final[list[QLocale.Language]] = [
    QLocale.Language.Latvian
]
icelandicLanguage: Final[list[QLocale.Language]] = [
    QLocale.Language.Icelandic
]
irishStyleLanguages: Final[list[QLocale.Language]] = [
    QLocale.Language.Divehi,
    QLocale.Language.Inuktitut,
    QLocale.Language.Inupiak,
    QLocale.Language.Irish,
    QLocale.Language.Manx,
    QLocale.Language.Maori,
    QLocale.Language.NorthernSami,
    QLocale.Language.Samoan,
    QLocale.Language.Sanskrit,
]
gaelicStyleLanguages: Final[list[QLocale.Language]] = [
    QLocale.Language.Gaelic,
]
slovakStyleLanguages: Final[list[QLocale.Language]] = [
    QLocale.Language.Slovak,
    QLocale.Language.Czech,
]
macedonianLanguage: Final[list[QLocale.Language]] = [QLocale.Language.Macedonian]
lithuanianLanguage: Final[list[QLocale.Language]] = [QLocale.Language.Lithuanian]
russianStyleLanguages: Final[list[QLocale.Language]] = [
    QLocale.Language.Bosnian,
    QLocale.Language.Belarusian,
    QLocale.Language.Croatian,
    QLocale.Language.Russian,
    QLocale.Language.Serbian,
    QLocale.Language.Ukrainian,
]
polishLanguage: Final[list[QLocale.Language]] = [QLocale.Language.Polish]
romanianLanguages: Final[list[QLocale.Language]] = [
    QLocale.Language.Romanian,
]
slovenianLanguage: Final[list[QLocale.Language]] = [QLocale.Language.Slovenian]
malteseLanguage: Final[list[QLocale.Language]] = [QLocale.Language.Maltese]
welshLanguage: Final[list[QLocale.Language]] = [QLocale.Language.Welsh]
arabicLanguage: Final[list[QLocale.Language]] = [QLocale.Language.Arabic]
tagalogLanguage: Final[list[QLocale.Language]] = [QLocale.Language.Filipino]

frenchStyleCountries: Final[list[QLocale.Country]] = [
    # keep synchronized with frenchStyleLanguages
    QLocale.Country.AnyCountry,
    QLocale.Country.AnyCountry,
    QLocale.Country.AnyCountry,
    QLocale.Country.Brazil,
    QLocale.Country.AnyCountry,
    QLocale.Country.AnyCountry,
    QLocale.Country.AnyCountry
]


class NumerusTableEntry(NamedTuple):
    rules: bytes
    forms: list[str]
    languages: list[QLocale.Language]
    countries: list[QLocale.Country]
    gettextRules: str
    
    @property
    def rulesSize(self) -> int:
        return len(self.rules)
    

numerusTable: Final[list[NumerusTableEntry]] = [
    NumerusTableEntry(b'', japaneseStyleForms, japaneseStyleLanguages, [], "nplurals=1; plural=0;"),
    NumerusTableEntry(englishStyleRules, englishStyleForms, englishStyleLanguages, [], "nplurals=2; plural=(n != 1);"),
    NumerusTableEntry(frenchStyleRules, frenchStyleForms, frenchStyleLanguages, frenchStyleCountries,
                      "nplurals=2; plural=(n > 1);"),
    NumerusTableEntry(latvianRules, latvianForms, latvianLanguage, [],
                      "nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n != 0 ? 1 : 2);"),
    NumerusTableEntry(icelandicRules, icelandicForms, icelandicLanguage, [],
                      "nplurals=2; plural=(n%10==1 && n%100!=11 ? 0 : 1);"),
    NumerusTableEntry(irishStyleRules, irishStyleForms, irishStyleLanguages, [],
                      "nplurals=3; plural=(n==1 ? 0 : n==2 ? 1 : 2);"),
    NumerusTableEntry(gaelicStyleRules, gaelicStyleForms, gaelicStyleLanguages, [],
                      "nplurals=4; plural=(n==1 || n==11) ? 0 : (n==2 || n==12) ? 1 : (n > 2 && n < 20) ? 2 : 3;"),
    NumerusTableEntry(slovakStyleRules, slovakStyleForms, slovakStyleLanguages, [],
                      "nplurals=3; plural=((n==1) ? 0 : (n>=2 && n<=4) ? 1 : 2);"),
    NumerusTableEntry(macedonianRules, macedonianForms, macedonianLanguage, [],
                      "nplurals=3; plural=(n%100==1 ? 0 : n%100==2 ? 1 : 2);"),
    NumerusTableEntry(lithuanianRules, lithuanianForms, lithuanianLanguage, [],
                      "nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && (n%100<10 || n%100>=20) ? 1 : 2);"),
    NumerusTableEntry(russianStyleRules, russianStyleForms, russianStyleLanguages, [],
                      "nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : "
                      "n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);"),
    NumerusTableEntry(polishRules, polishForms, polishLanguage, [],
                      "nplurals=3; plural=(n==1 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);"),
    NumerusTableEntry(romanianRules, romanianForms, romanianLanguages, [],
                      "nplurals=3; plural=(n==1 ? 0 : (n==0 || (n%100 > 0 && n%100 < 20)) ? 1 : 2);"),
    NumerusTableEntry(slovenianRules, slovenianForms, slovenianLanguage, [],
                      "nplurals=4; plural=(n%100==1 ? 0 : n%100==2 ? 1 : n%100==3 || n%100==4 ? 2 : 3);"),
    NumerusTableEntry(malteseRules, malteseForms, malteseLanguage, [],
                      "nplurals=4; plural=(n==1 ? 0 : "
                      "(n==0 || (n%100>=1 && n%100<=10)) ? 1 : (n%100>=11 && n%100<=19) ? 2 : 3);"),
    NumerusTableEntry(welshRules, welshForms, welshLanguage, [],
                      "nplurals=5; plural=(n==0 ? 0 : n==1 ? 1 : (n>=2 && n<=5) ? 2 : n==6 ? 3 : 4);"),
    NumerusTableEntry(arabicRules, arabicForms, arabicLanguage, [],
                      "nplurals=6; plural=(n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : "
                      "(n%100>=3 && n%100<=10) ? 3 : n%100>=11 ? 4 : 5);"),
    NumerusTableEntry(tagalogRules, tagalogForms, tagalogLanguage, [],
                      "nplurals=3; plural=(n==1 ? 0 : (n%10==4 || n%10==6 || n%10== 9) ? 1 : 2);"),
]


def getNumerusInfo(language: QLocale.Language, country: QLocale.Country) -> tuple[bytes, list[str], str, bool]:
    rules: bytes = b''
    forms: list[str] = []
    gettextRules: str = ''
    while True:
        entry: NumerusTableEntry
        for entry in numerusTable:
            j: int
            for j in range(len(entry.languages)):
                if (entry.languages[j] == language
                        and ((not entry.countries and country == QLocale.Country.AnyCountry)
                             or (entry.countries and entry.countries[j] == country))):
                    rules = entry.rules
                    gettextRules = entry.gettextRules
                    forms = list(entry.forms)
                    return rules, forms, gettextRules, True

        if country == QLocale.Country.AnyCountry:
            break
        country = QLocale.Country.AnyCountry
            
    return rules, forms, gettextRules, False


def getNumerusInfoString() -> str:
    langs: list[str] = []
    entry: NumerusTableEntry
    for entry in numerusTable:
        j: int
        for j in range(len(entry.languages)):
            loc: QLocale = QLocale(entry.languages[j],
                                   entry.countries[j] if entry.countries else QLocale.Country.AnyCountry)
            lang: str = QLocale.languageToString(entry.languages[j])
            if loc.language() == QLocale.Language.C:
                lang += ' (!!!)'
            elif entry.countries and entry.countries[j] != QLocale.Country.AnyCountry:
                lang += f' ({QLocale.territoryToString(loc.territory())})'
            else:
                lang += f' [{QLocale.territoryToString(loc.territory())}]'
            langs.append(f'{lang:<40} {loc.name():<8} {entry.gettextRules}')
    langs.sort()
    return '\n'.join(langs)
