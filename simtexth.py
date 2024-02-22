# coding=utf-8
# Copyright (C) 2016 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR GPL-3.0-only WITH Qt-GPL-exception-1.0

from __future__ import annotations

from typing import Final

from translator import Translator
from translatormessage import TranslatorMessage

textSimilarityThreshold: Final[int] = 190

TML = list[TranslatorMessage]

"""
  How similar are the two texts?  The approach used here relies on co-occurrence
  matrices and is very efficient.

  Let's see with an example: how similar are “here” and “hither”?  The
  co-occurrence matrix M for “here” is M[h,e] = 1, M[e,r] = 1, M[r,e] = 1, and 0
  elsewhere; the matrix N for “hither” is N[h,i] = 1, N[i,t] = 1, ...,
  N[h,e] = 1, N[e,r] = 1, and 0 elsewhere.  The union U of both matrices is the
  matrix U[i,j] = max { M[i,j], N[i,j] }, and the intersection V is
  V[i,j] = min { M[i,j], N[i,j] }.  The score for a pair of texts is

      score = (sum of V[i,j] over all i, j) / (sum of U[i,j] over all i, j),

  a formula suggested by Arnt Gulbrandsen.  Here we have

      score = 2 / 6,

  or one third.

  The implementation differs from this in a few details.  Most importantly,
  repetitions are ignored; for input “xxx”, M[x,x] equals 1, not 2.
"""

"""
  Every character is assigned to one of 20 buckets so that the co-occurrence
  matrix requires only 20 * 20 = 400 bits, not 256 * 256 = 65536 bits or even
  more if we want the whole Unicode.  Which character falls in which bucket is
  arbitrary?

  The second half of the table is a replica of the first half, because of
  laziness.
"""

# fmt: off
indexOf: Final[bytearray] = bytearray([
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    #   !   "   #   $   %   &   '   (   )   *   +   ,   -   .   /
    0, 2, 6, 7, 10, 12, 15, 19, 2, 6, 7, 10, 12, 15, 19, 0,
    # 0 1   2   3   4   5   6   7   8   9   :   ;   <   =   >   ?
    1, 3, 4, 5, 8, 9, 11, 13, 14, 16, 2, 6, 7, 10, 12, 15,
    # @ A   B   C   D   E   F   G   H   I   J   K   L   M   N   O
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 6, 10, 11, 12, 13, 14,
    # P Q   R   S   T   U   V   W   X   Y   Z   [   \   ]   ^   _
    15, 12, 16, 17, 18, 19, 2, 10, 15, 7, 19, 2, 6, 7, 10, 0,
    # ` a   b   c   d   e   f   g   h   i   j   k   l   m   n   o
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 6, 10, 11, 12, 13, 14,
    # p q   r   s   t   u   v   w   x   y   z   {   |   }   ~
    15, 12, 16, 17, 18, 19, 2, 10, 15, 7, 19, 2, 6, 7, 10, 0,

    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 2, 6, 7, 10, 12, 15, 19, 2, 6, 7, 10, 12, 15, 19, 0,
    1, 3, 4, 5, 8, 9, 11, 13, 14, 16, 2, 6, 7, 10, 12, 15,
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 6, 10, 11, 12, 13, 14,
    15, 12, 16, 17, 18, 19, 2, 10, 15, 7, 19, 2, 6, 7, 10, 0,
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 6, 10, 11, 12, 13, 14,
    15, 12, 16, 17, 18, 19, 2, 10, 15, 7, 19, 2, 6, 7, 10, 0
])
# fmt: on

"""
  The entry bitCount[i] (for i between 0 and 255) is the number of bits used to
  represent i in binary.
"""

# fmt: off
bitCount: Final[bytearray] = bytearray([
    0, 1, 1, 2, 1, 2, 2, 3, 1, 2, 2, 3, 2, 3, 3, 4,
    1, 2, 2, 3, 2, 3, 3, 4, 2, 3, 3, 4, 3, 4, 4, 5,
    1, 2, 2, 3, 2, 3, 3, 4, 2, 3, 3, 4, 3, 4, 4, 5,
    2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5, 6,
    1, 2, 2, 3, 2, 3, 3, 4, 2, 3, 3, 4, 3, 4, 4, 5,
    2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5, 6,
    2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5, 6,
    3, 4, 4, 5, 4, 5, 5, 6, 4, 5, 5, 6, 5, 6, 6, 7,
    1, 2, 2, 3, 2, 3, 3, 4, 2, 3, 3, 4, 3, 4, 4, 5,
    2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5, 6,
    2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5, 6,
    3, 4, 4, 5, 4, 5, 5, 6, 4, 5, 5, 6, 5, 6, 6, 7,
    2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5, 6,
    3, 4, 4, 5, 4, 5, 5, 6, 4, 5, 5, 6, 5, 6, 6, 7,
    3, 4, 4, 5, 4, 5, 5, 6, 4, 5, 5, 6, 5, 6, 6, 7,
    4, 5, 5, 6, 5, 6, 6, 7, 5, 6, 6, 7, 6, 7, 7, 8
])
# fmt: on


class Candidate:
    def __init__(self, c: str = "", s: str = "", d: str = "", t: str = "") -> None:
        self.context: str = c
        self.source: str = s
        self.disambiguation: str = d
        self.translation: str = t

    def __eq__(self, other: "Candidate") -> bool:
        return (
            self.translation == other.translation
            and self.source == other.source
            and self.context == other.context
            and self.disambiguation == other.disambiguation
        )

    def __ne__(self, other: "Candidate") -> bool:
        return not (self == other)


CandidateList = list[Candidate]


class CoMatrix:
    """
    The matrix has 20 * 20 = 400 entries.
    This requires 50 bytes, or 13 words.
    Some operations are performed on words for more efficiency.
    """

    def __init__(self, string: str = "") -> None:
        ba: bytes = string.encode("utf-8")
        self.b: bytearray = bytearray([0] * 52)
        c: int = 0
        d: int
        i: int

        # The Knuth books are not in the office only for show; they help make
        # loops 30% faster and 20% as readable.
        for i, d in enumerate(ba):
            self.setCoOccurrence(c, d)
            if i < len(ba) - 1:
                c = ba[i + 1]
                self.setCoOccurrence(d, c)

    def setCoOccurrence(self, c: int, d: int) -> None:
        k: int = indexOf[c] + 20 * indexOf[d]
        self.b[k >> 3] |= 1 << (k & 0x7)

    def worth(self) -> int:
        w: int = 0
        i: int
        for i in range(50):
            w += bitCount[self.b[i]]
        return w

    def reunion(self, other: "CoMatrix") -> "CoMatrix":
        p: CoMatrix = CoMatrix()
        i: int
        for i in range(13):
            for j in range(4):
                p.b[i + j] = self.b[i + j] | other.b[i + j]
        return p

    def intersection(self, other: "CoMatrix") -> "CoMatrix":
        p: CoMatrix = CoMatrix()
        i: int
        for i in range(13):
            for j in range(4):
                p.b[i + j] = self.b[i + j] & other.b[i + j]
        return p


class StringSimilarityMatcher:
    """
    This class is more efficient for searching through a large array of candidate strings, since we only
    have to construct the CoMatrix for the \a stringToMatch once,
    after that we just call getSimilarityScore(strCandidate).
    See also getSimilarityScore
    """

    def __init__(self, stringToMatch: str) -> None:
        self.m_cm: CoMatrix = CoMatrix(stringToMatch)
        self.m_length: int = len(stringToMatch)

    def getSimilarityScore(self, strCandidate: str) -> int:
        cm_target: CoMatrix = CoMatrix(strCandidate)
        delta: int = abs(self.m_length - len(strCandidate))
        score: int = ((self.m_cm.intersection(cm_target).worth() + 1) << 10) // (
            self.m_cm.reunion(cm_target).worth() + (delta << 1) + 1
        )
        return score


def getSimilarityScore(str1: str, str2: str) -> int:
    """
    Checks how similar two strings are.
    The return value is the score, and a higher score is more similar
    than one with a low score.
    Linguist considers a score over 190 to be a good match.
    See also StringSimilarityMatcher
    """
    return StringSimilarityMatcher(str1).getSimilarityScore(str2)


def similarTextHeuristicCandidates(
    tor: Translator,
    text: str,
    maxCandidates: int,
) -> CandidateList:
    scores: list[int] = []
    candidates: CandidateList = []
    matcher: StringSimilarityMatcher = StringSimilarityMatcher(text)

    mtm: TranslatorMessage
    for mtm in tor.messages():
        if mtm.type() == TranslatorMessage.Type.Unfinished or not mtm.translation():
            continue

        s: str = mtm.sourceText()
        score: int = matcher.getSimilarityScore(s)

        if len(candidates) == maxCandidates and score > scores[maxCandidates - 1]:
            del candidates[-1]

        if len(candidates) < maxCandidates and score >= textSimilarityThreshold:
            cand: Candidate = Candidate(
                mtm.context(), s, mtm.comment(), mtm.translation()
            )

            i: int = 0
            ignore: bool = False
            while i < len(candidates):
                if score == scores[i] and candidates[i] == cand:
                    ignore = True
                if score >= scores[i]:
                    break
                i += 1
            if not ignore:
                scores.insert(i, score)
                candidates.insert(i, cand)

    return candidates
