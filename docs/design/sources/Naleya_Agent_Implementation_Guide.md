> **Superseded duration note (2026-11-07):** This source guide describes the story duration as a century. That duration is superseded by [docs/design/decisions.md](../decisions.md), ruling 25: about a thousand Earth years. The source text below is retained unchanged.

# Gone: Naleya glyph and language implementation guide

Use this file with the three supplied PDFs. Implement the established writing system and language; preserve the shapes and meanings rather than inventing a new alien font or translating English letter by letter.

## 1. Read these sources

| File | Role | Useful pages |
|---|---|---|
| `Gone_Naleya_Language_Reference.pdf` | Main language specification, v0.13, 71 pages | 1 sound; 2 glyph chart; 3-7 grammar and relationships; 8 clocks; 16 drives; 17-20 reference, qualities and operating states; 25-27 relationships, motion and possession; 32-37 clauses, certainty and instructions; 44-47 quantity, time and references; 55-68 dictionary; 69 console labels; 70-71 worlds, names and translation effect |
| `Gone_Nalesha_Translations.pdf` | Worked translation examples, v0.13, 13 pages | Use its native text, romanization and gloss as regression examples |
| `Gone_Naleya_Story_Synopsis.pdf` | Full-spoiler story context, 9 pages | 2-7 parallel synopsis; 8 eleven additional roots; 9 descriptive compounds and a proposed proper name |

The project conversation calls the language **Naleya**; the main reference and translation PDF call the working language **Nalesha**. These refer to the same current system. Use a stable internal language ID such as `naleya`; do not create separate languages or rename supplied assets to resolve the spelling difference. The native word `Nalesha` is syllabifiable as `na-le-sha`; the project label `Naleya` contains a sound outside the native inventory and should not be fed to the glyph renderer as native text.

The main reference specifies grammar and the 274 existing dictionary entries, including compounds. The story appendix adds eleven roots and descriptive compounds; it does not retroactively insert them into the other PDFs. `Eshapani`, the proposed native name for Spanish, remains a proposed proper-name adaptation. Keep that provenance in language data.

This Markdown supplies exact vector construction and a runnable renderer. Its coordinates have been checked segment by segment against **all 50 signs on page 2 of the current language PDF**. PDF text extraction cannot recover those signs: they are drawn paths, not encoded letters.

## 2. The writing system

This is a **syllabary with 50 signs**. One written sign represents one syllable, not one Roman letter or an entire word.

- Vowels: `a e i o u`.
- Consonant categories: `p t k m n l w sh ch`.
- A syllable is either a vowel alone or one consonant category followed by one vowel: `V` or `CV`.
- `sh` and `ch` each represent one consonant. Parse them before single-letter consonants.
- No consonant clusters or final consonants occur.
- No separate `r`, `h`, `v`, English-style `y`, or `s` phoneme exists. The `h` in `sh/ch` is part of the Roman digraph.
- `p` includes p-like and b-like realizations without a lexical distinction. Do not add a separate `b` sign.
- The syllables `ti`, `tu`, `mi`, and `no` exist in the chart. Earlier rejection of those as particular pronouns or negation words does **not** remove the signs from the syllabary. Negation is `cha`.
- Read left to right. Native signs have no uppercase/lowercase distinction.
- Word boundaries remain visible. A multiword compound does not become one giant sign.
- A tense suffix is attached to its predicate word, so its sign follows without a word gap: `peshupa`, not `peshu pa`.

Examples:

| Romanized spelling | Syllables/signs |
|---|---|
| `tala pama` | `ta la` / word gap / `pa ma` |
| `te mu nawa lina` | `te` / gap / `mu` / gap / `na wa` / gap / `li na` |
| `shasha` | `sha sha` |
| `peshupa` | `pe shu pa` |
| `mokepopu` | `mo ke po pu` |
| `Tewa` | `te wa` |

The signs are original project designs. Render their supplied geometry. Do not substitute Hangul, Chinese, Japanese, Unicode box-drawing characters, runes, or arbitrary science-fiction glyphs.

## 3. Exact geometry and metrics

Each sign combines **an onset component in the upper band** with **a vowel component in the lower band**. A vowel-only sign uses the small upper carrier; that carrier has no consonant sound.

The executable block below contains the complete geometry. Interpret each inner point list as its own polyline. Separate lists must remain separate strokes. A repeated starting point closes that particular outline; do not automatically close every path or fill the shapes.

| Property | Exact reference value |
|---|---|
| Coordinate direction | +x right; +y **up** |
| Nominal cell | 10 x 10 native units |
| Onset band | y = 4 through 9 |
| Vowel band | y = 0 through 2 |
| Stroke width | 0.72 native units |
| Stroke caps | Butt/flat |
| Stroke joins | Miter/square |
| Fill | None; stroked paths |
| Glyph advance | 10.3 native units |
| Extra word gap | 6 native units, in addition to the preceding glyph advance |

For nominal cell size `S` pixels, multiply coordinates and stroke width by `S / 10`. Advance by `1.03 * S` per sign; add `0.6 * S` per word boundary. Do not center each sign by its individual ink bounding box: all signs share the same fixed cell origin and advance.

For a screen or SVG with downward-positive y, map canonical points using:

```text
screen_x = cell_left + native_x * S / 10
screen_y = baseline  - native_y * S / 10
```

This is one y inversion. A second flip will reverse the vowel and onset arrangement. `a` is the lower cup; `e` the lower cap; `i` the lower L; `o` a lower closed rectangle; `u` a lower top-and-right corner. Keep the 6.5-unit strokes in `sh` and `ch`; rounding the source geometry to integers changes the designs.

Line height is a layout choice. The renderer uses `1.65 * S`; the story PDF used approximately `1.58 * S`. Wrap at word boundaries, preserve explicit line breaks, and avoid splitting a suffix away from its word. At small sizes preserve the distinguishing strokes and open spaces; check actual game resolution before adding glow or wear.

## 4. Working reference renderer

Save this block as `naleya_glyphs.py`. It uses only the Python standard library. It generates vector SVGs, validates syllable spelling, wraps complete words, and renders octal digit strings using the native digit signs.

It is a **renderer**, not a translator, dictionary validator, or complete morphological analyzer. A syllabically valid spelling can still be an unknown word or an incorrect sentence. Author translations from the supplied dictionary and grammar first.

<!-- BEGIN_REFERENCE_RENDERER -->
```python
"""Reference rendering of Gone's existing 50 Naleya/Nalesha signs."""
import argparse
from pathlib import Path
import re
from xml.sax.saxutils import escape

ONSETS = ['', 'p', 't', 'k', 'm', 'n', 'l', 'w', 'sh', 'ch']
VOWELS = 'aeiou'
SYLLABLES = [c + v for c in ONSETS for v in VOWELS]
DIGITS = ['mo', 'na', 'mu', 'shi', 'le', 'chi', 'wi', 'shu']

# Canonical coordinates: +x right, +y UP, nominal 10 x 10 cell.
# Every inner array is a separate open polyline. A repeated endpoint closes
# that particular contour. Do not connect separate polylines.
ONSET_PATHS = {
    '': [[(3, 6), (3, 9), (6, 9), (6, 6), (3, 6)]],
    'p': [[(1, 4), (1, 9), (7, 9), (7, 6), (1, 6)]],
    't': [[(1, 9), (7, 9)], [(4, 9), (4, 4)], [(2, 4), (6, 4)]],
    'k': [[(1, 4), (1, 9)], [(1, 6), (6, 6), (6, 9)], [(6, 6), (6, 4), (8, 4)]],
    'm': [[(1, 4), (1, 9), (7, 9), (7, 4)], [(4, 9), (4, 6)]],
    'n': [[(1, 9), (1, 4), (7, 4), (7, 9)]],
    'l': [[(1, 9), (1, 4), (7, 4)]],
    'w': [[(1, 9), (1, 4), (7, 4), (7, 9)], [(4, 4), (4, 7)]],
    'sh': [[(7, 9), (1, 9), (1, 6.5), (7, 6.5), (7, 4), (1, 4)]],
    'ch': [[(1, 4), (1, 9)], [(7, 4), (7, 9)], [(1, 6.5), (7, 6.5)]],
}
VOWEL_PATHS = {
    'a': [[(1, 2), (1, 0), (7, 0), (7, 2)]],
    'e': [[(1, 0), (1, 2), (7, 2), (7, 0)]],
    'i': [[(1, 2), (1, 0), (7, 0)]],
    'o': [[(1, 0), (1, 2), (7, 2), (7, 0), (1, 0)]],
    'u': [[(1, 2), (7, 2), (7, 0)]],
}

SYLLABLE_RE = re.compile(r'(?:sh|ch|[ptkmnlw])?[aeiou]')
CHUNK_RE = re.compile(r'[A-Za-z]+|[0-7]+|[.,:;!?()\"]')

def syllabify(word):
    """Strict spelling validation; never silently discard unsupported sounds."""
    word = word.lower()
    parts = SYLLABLE_RE.findall(word)
    if not word or ''.join(parts) != word:
        raise ValueError(f'Invalid native word: {word!r}')
    return parts

def glyph_paths(syllable):
    if syllable not in SYLLABLES:
        raise ValueError(f'Unknown syllable: {syllable!r}')
    return ONSET_PATHS[syllable[:-1]] + VOWEL_PATHS[syllable[-1]]

def octal(value, min_digits=1):
    """Input is a nonnegative integer quantity, not already formatted digits."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError('Expected a nonnegative integer')
    return format(value, 'o').zfill(min_digits)

def clock(hour, interval, beat=None):
    """Integer local-unit values -> octal display; performs no Earth-time conversion."""
    fields = [(hour, 32), (interval, 64)]
    if beat is not None:
        fields.append((beat, 64))
    if any(not isinstance(v, int) or isinstance(v, bool) or not 0 <= v < limit
           for v, limit in fields):
        raise ValueError('Clock field outside the full-day range')
    return ':'.join(octal(v, 2) for v, _ in fields)

def chunk_units(chunk):
    """One unbreakable text chunk -> syllables or editorial punctuation.

    Numeric text is ALREADY OCTAL. Each written digit uses its native sign.
    This does not translate English/Spanish, validate vocabulary, or add grammar.
    """
    units = []
    cursor = 0
    for match in CHUNK_RE.finditer(chunk):
        if match.start() != cursor:
            raise ValueError(f'Unsupported text in {chunk!r}')
        token = match.group()
        if token.isalpha():
            units.extend(('glyph', s) for s in syllabify(token))
        elif token.isdigit():
            units.extend(('glyph', DIGITS[int(d)]) for d in token)
        else:
            units.append(('punct', token))
        cursor = match.end()
    if cursor != len(chunk):
        raise ValueError(f'Unsupported text in {chunk!r}')
    return units

def render_svg(roman, width=640, size=28, padding=16, color='#172d3c'):
    """Syllabic native text in -> SVG, with word wrapping and a single y flip.

    size is the nominal 10-unit cell height. No bitmap or external font is
    required for signs; ordinary font text is used only for punctuation.
    """
    if size <= 0 or padding < 0 or width <= 2 * padding:
        raise ValueError('Invalid layout dimensions')
    if not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
        raise ValueError('Use a six-digit hexadecimal color')
    available = width - 2 * padding
    advance = size * 1.03
    word_gap = size * .6
    punctuation_advance = size * .35
    line_height = size * 1.65  # Implementation choice, not a language rule.
    scale = size / 10
    row = 0
    cursor = 0.0
    pending_space = False
    elements = []
    for match in re.finditer(r'\n|[ \t]+|[^\s]+', roman):
        token = match.group()
        if token == '\n':
            row += 1
            cursor = 0.0
            pending_space = False
            continue
        if token.isspace():
            pending_space = True
            continue
        units = chunk_units(token)
        token_width = sum(advance if kind == 'glyph' else punctuation_advance
                          for kind, _ in units)
        if token_width > available:
            raise ValueError(f'Word or number exceeds line width: {token!r}')
        gap = word_gap if pending_space and cursor else 0
        if cursor and cursor + gap + token_width > available:
            row += 1
            cursor = 0.0
            gap = 0
        cursor += gap
        pending_space = False
        baseline = padding + row * line_height + size
        for kind, value in units:
            x = padding + cursor
            if kind == 'glyph':
                for path in glyph_paths(value):
                    pts = ' '.join(f'{x + px * scale:.4f},{baseline - py * scale:.4f}'
                                   for px, py in path)
                    elements.append(f'<polyline points="{pts}"/>')
                cursor += advance
            else:
                elements.append(
                    f'<text x="{x:.4f}" y="{baseline:.4f}" stroke="none" '
                    f'fill="{color}" font-family="sans-serif" '
                    f'font-size="{size * .78:.4f}">{escape(value)}</text>')
                cursor += punctuation_advance
    height = padding * 2 + (row + 1) * line_height
    body = '\n'.join(elements)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height:.4f}" viewBox="0 0 {width} {height:.4f}">\n'
            f'<g fill="none" stroke="{color}" stroke-width="{.72 * scale:.4f}" '
            f'stroke-linecap="butt" stroke-linejoin="miter">\n{body}\n</g>\n</svg>')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--text', default='te mu nawa lina')
    parser.add_argument('--output', default='naleya.svg')
    parser.add_argument('--width', type=float, default=640)
    parser.add_argument('--size', type=float, default=28)
    args = parser.parse_args()
    Path(args.output).write_text(render_svg(args.text, args.width, args.size), encoding='utf-8')
```
<!-- END_REFERENCE_RENDERER -->

Usage:

```bash
python3 naleya_glyphs.py --text "te mu nawa lina" --output secondary_power.svg
python3 naleya_glyphs.py --text "Tewa" --output tewa.svg
python3 naleya_glyphs.py --text "07:20 24:03" --output clock_examples.svg
```

Numeric strings passed to `render_svg` are **already octal**, not decimal quantities. Call `octal(quantity)` or `clock(hour, interval, beat)` first when input values are integer quantities. `clock(7, 16)` returns `07:20`; the SVG renderer then draws the native signs for those written digits. It rejects digits `8` and `9` instead of quietly producing an incorrect display.

The punctuation in this renderer is editorial, matching the PDFs' use of ordinary punctuation. It is not an additional native alphabet. Punctuation is the only part of this sample that uses an ordinary font. Extend punctuation support deliberately if production text needs more marks; never let a failed native glyph fall back to a Latin letter or an unrelated font.

The reference mentions a radix tick before base-eight fractional digits, but does not supply its exact production geometry or a signed-number display convention. The sample does not implement those engineering formats. Specify them explicitly if a console needs negative coordinates or fractional readings; do not insert an Earth-decimal format by assumption.

## 5. Porting it into the game

Choose a suitable production representation: generated SVGs/textures, a shared vector drawing routine, a mesh/atlas, or a custom font. The geometry above remains identical in each approach.

For a Godot-style 2D canvas, transform every point with the formula above and draw each polyline with a flat cap and the scaled stroke width. For a Rust renderer, generate equivalent line geometry or expand the strokes into filled outlines. Keep separate polylines separate; overlapping strokes can be unioned after expansion.

If making a font:

- Fonts need **filled outlines**: expand the centerline strokes into outlines with the specified caps and joins. An open polyline alone is not a usable ordinary font glyph.
- A convenient conversion is 1000 units/em: multiply native coordinates by 100, use stroke width 72, glyph advance 1030, and space advance 600. These values reproduce the reference proportions.
- Include the half-stroke extents in font metrics and atlas padding. The bottom stroke reaches y = -0.36 in native units; clipping at baseline zero will cut it off.
- Use the same advance for every native sign. Avoid unintended kerning and contextual forms.
- Keep semantic Romanized text alongside the display encoding so search, localization, logs and accessibility do not depend on opaque glyph codes.

**Optional engineering convention, not established language canon:** map the ordered 50 signs to Unicode Private Use Area `U+E000` through `U+E031`, inclusive. Use this onset order:

```text
['', 'p', 't', 'k', 'm', 'n', 'l', 'w', 'sh', 'ch']
```

Within each onset, order vowels `a e i o u`. Then:

```text
codepoint = 0xE000 + onset_index * 5 + vowel_index
```

Thus `a` is U+E000, `pa` U+E005, `na` U+E019, and `chu` U+E031. This encodes whole syllables. It does not assign Unicode codepoints to the Roman letters inside them. The PUA mapping is a proposed implementation choice; freeze and document whichever mapping the repository adopts.

## 6. Numbers and the full-day clock

All native numerals are base eight. There are **eight digits, 0 through 7**; the value eight is written `10`. The earlier conversational shorthand “0-8” must not create a ninth digit.

| Written octal digit | Native syllable/sign |
|---|---|
| 0 | `mo` |
| 1 | `na` |
| 2 | `mu` |
| 3 | `shi` |
| 4 | `le` |
| 5 | `chi` |
| 6 | `wi` |
| 7 | `shu` |

These use the same syllable signs as ordinary words. Do not invent another numerical alphabet or show Arabic numerals on the physical ship display. Zero is explicit, never a missing character.

Distinguish a **spoken cardinal** from **written digits or an identifier**:

- Decimal 10 is octal `12`; its formal cardinal is `na nala mu`, one eight and two.
- Octal identifier `105` is read digit by digit: `na mo chi`. Identifiers are boxed to distinguish their role.
- Place words are `nala` = 8, `naka` = 64, `nata` = 512, `we` = 4096, `chu` = 32768 in Earth-decimal explanations. `we` and `chu` are not digits.
- Ordinals use `te` before the number. `te mu` means second; it is not inherently reserve or backup.

Clock rules:

- A full day has **32 local hours**, written `40` in octal.
- Every clock covers that complete day. No AM/PM, 12-hour or 16-hour convention exists.
- Hour labels range `00..37`; `40` is a duration of one day, not a clock hour label.
- Each hour contains 64 intervals, each interval 64 beats: interval/beat labels `00..77`.
- Full display: `HH:II:BB`. Rollover: `37:77:77` -> `00:00:00`.
- Midnight is `00:00:00`; midday is `20:00:00` and does not reset the clock.
- Decimal input “7th hour, 16th minute/interval” becomes `07:20`; “20th hour, 3rd minute/interval” becomes `24:03`.
- Local hour/interval/beat lengths in Earth seconds are not fixed. Do not quietly assign 3600 Earth seconds per local hour or 60 subdivisions per field.

An analog clock has **one complete 32-hour revolution**. Label every other hour to avoid crowding. The 16 labels, in clockwise order from the top, are:

```text
00 02 04 06 10 12 14 16 20 22 24 26 30 32 34 36
```

Render those labels with native digit signs. Midday points down; midnight points up. With `h`, `i`, `b` as ordinary integer local-unit values, clockwise angles from the top are:

```text
hour_angle     = 2*pi * (h + i/64 + b/4096) / 32
interval_angle = 2*pi * (i + b/64) / 64
beat_angle     = 2*pi * b / 64
screen_x       = center_x + radius * sin(angle)
screen_y       = center_y - radius * cos(angle)
```

The story's century and thirty-year journey use explicitly identified **Earth years**, `Tewa ki tanu`; they do not establish a native year length. In octal, 100 Earth years is `144` and 30 is `36`.

## 7. Language constraints that affect implementation

Use the full PDFs when writing dialogue. The following rules prevent common implementation errors.

### Clause and time

- Default order: subject, negation/operator, finite predicate, object/task. There are no articles or gender agreement.
- Bare action = ongoing now. `-pa` attaches to the finite predicate for ended past; `-pu` for expected near future, unless an explicit date, interval or condition moves it later.
- A state or nominal predicate can take the same endings. There is no required be-verb, gerund, subjunctive conjugation, or separate positional past/future particle.
- `nu` covers need/must/should/have to; its task complement stays bare. `nupa peshu` = needed to repair. Do not put the same tense ending on every verb in a task chain.
- Do not identify tense merely by stripping final syllables from arbitrary words. `napa` is woman; it is not a past form of the digit `na`. Use known lexemes and grammatical context.
- A past repair attempt does not prove success. Acknowledgement and completion also differ: `cho` affirms/accepts; `ku` reports completion.

### Polarity, ability, requests and certainty

- `cha` = not/no; `cho` = affirmative. Do not use English/Spanish `no`, `yes` or `si` as native polarity words.
- `cha nu` = need not; `nu cha` = must not. `cha pe` = cannot. Preserve operator scope.
- `pe` = ability/possibility; `poli` = permission; `chawi` requests an action. Rank and duty affect the social force of a command, not conjugation.
- `pisha` = know, `wome` = believe, `meli` = think/infer, `pe wele ...` = it is possible that ... . Believing something does not make it a narrator-confirmed fact.
- `ka` ends a yes/no question. `ke`, what, and `me`, who, occupy the unknown argument's position.

### Relationships and count

- Person stems: `ko` speaker, `wu` addressee, `ni` third person. Add `-sho` for personal closeness or `-po` for non-closeness, then an explicit count: `na` one, `mu` two, `lu` unspecified multiple, or another count.
- Examples: `ko na`, I; `ko mu`, we two; `wusho na`, one close addressee; `wupo lu`, several non-close addressees; `nisho lu`, close third-person group; `nipo na`, one outsider/non-close person.
- No separate English-style plural-you word is needed. Change the count while retaining the same person/relation construction.
- Pronouns have no gender and no distinct subject/object case forms. `ni na` can refer to a person or a thing; names, context and `wa`/`che` distinguish referents.
- `wupo` can be formal or threatening in context. It is not a dedicated second-person enemy form. The computer uses `wupo` for the addressee, and `nipo` for outsiders; a threat context can make the latter mean enemy.
- Shipmates are not automatically close. Rank does not create a bond; custom normally lets the senior person initiate close address. Once offered, withholding it is an insult. A romantic change from close to non-close address withdraws the relationship, rather than merely expressing anger.
- If numeric discourse labels are needed, `nisho na nami mu` means one close person labeled 2; `nisho mu` means two close people. Identity labels are not counts, ranks or genders.

### Possession, origin and partnership

- Possession/association: possessor + `ki` + possessed head. `ko na ki waki`, my thing; `ko lu ki waki`, our thing. Counts on the possessor count possessors, not possessions.
- `X po Y` = Y from X; `X wo Y` = Y source of X. `ko na po napa` = daughter, woman from me; `ko na wo namo` = father, man I come from. These explicit nouns carry gender; the pronouns do not.
- Crew is an anchored ship tribe: `ko na ki malu shapi`, my crew. `ko lu ki malipo`, our outsider, conventionally means traitor in a broken-belonging context.
- `pata` connects parts or establishes a committed couple; `komu` is the continuing bond. Use `wenu`, with, for accompanying someone: eat with, sit with, come with. “Join for dinner” is not translated with `pata`.
- `toka` means enter/input, and with a person as object in an intimate context also expresses sex. This creates no gender agreement or separate marriage institution.

### Qualities, clauses, quantity and time

- Quality before noun: `mokemi kimela pelo`, broken terminal. Quality after subject: `kimela pelo mokemi`, the terminal is broken.
- Manner: quality + `chela` before the action, e.g. `shuli chela lowi`, move rapidly. Habitual `nalemi chela` is not ongoing aspect; ongoing is already bare.
- `wele` introduces statement content; `mewa` a relative clause; `kume` can close it when the surrounding sentence resumes. `li` and; `lo` or.
- `she` introduces an open if-condition; the future result normally uses `-pu`. `shome` scopes an imagined alternative without a separate subjunctive.
- `poma` states an actual reason; `lashi` a purpose, which does not assert success.
- `pami` before, `pumi` after/then, `la` while. In a procedure, `pumi` explicitly sequences tasks; acknowledgements do not start the next task unless its prerequisite is met.
- Quantifiers: `ma` all, `washi` each, `shomi` some/at least one, `kumi` only, `mo` zero/none. “Not all” and “none” have different scopes; preserve the PDF examples.
- Comparisons: `lako` greater, `molu` less, `woli` equal, `mopu` than/compared with; pattern A + comparison + property + `mopu` + B. `kami` means almost, without reaching the threshold.
- `wama` still, `wumi` already, `tame` yet, `temi` until, `nape` since. Still and again (`nali`) are different.

## 8. Technical meanings must remain distinct

Keep these states separate in the language and in game data. A single English `on`, `off` or `bad` boolean is insufficient to author all the labels.

| Native | Meaning |
|---|---|
| `weli` | Capable/functional when prerequisites are supplied |
| `naweli` | Powered/energized |
| `shenu` | Actively performing work |
| `paleno` | Powered, capable, idle/standing by |
| `palo` | Off/disengaged; does not assert a defect |
| `penu` | Ready: capability and current prerequisites satisfied |
| `mokemi` | Broken/faulted despite normal prerequisites |
| `moketa` | Required or attempted operation failing/fails |
| `lokemi` | Damaged; may still operate |
| `lakemu` | Destroyed/ruined beyond usable function in context |

These are semantic distinctions, not an instruction to store them as ten unrelated booleans. Preserve coherent combinations: a capable terminal without power is not broken; powered standby is not active work.

Moral `wemi`/`mashu`, good nature/evil nature, are separate from mechanical state. `shuma` means tasty, `lopi` harmful, `nelo` correct, and `loka` incorrect/unacceptable. A harmful environment or a damaged engine is not inherently evil. Outsider/enemy status does not establish moral evil either.

## 9. Existing console wording

Use the supplied wording as fixtures. Select the state that matches actual game facts; do not mechanically substitute a generic English on/off label.

| Meaning | Native wording |
|---|---|
| Stasis bay | `tala pama` |
| Stasis pod | `tala taleki` |
| Secondary power system | `te mu nawa lina` |
| Reserve power system | `shasha nawa lina` |
| Engine | `kama` |
| Navigation console | `sheni pelo` |
| Life-support system | `talu lina` |
| Emergency | `taka` |
| Power is low | `nawa pena` |
| Engine is failing | `kama moketa` |
| Hatch is open | `pana palu` |
| Containment is failing | `tena moketa` |
| Stasis system inactive | `tala lina palo` |
| S-drive, full name | `nawi wesha kama` |
| S-drive, short name | `wesha kama` |
| H-drive | `chalu kama` |

Secondary is ordinal second; reserve means held ready. They are not interchangeable. S folds space; H rides the fold and is useless without it. The native console uses descriptive native names, not the English letters S/H.

## 10. Ship text and perceived Spanish

The protagonist is from Earth and speaks Spanish; the ship and its builders are from another human civilization. This should emerge through evidence rather than an opening explanation.

The **physical consoles remain in the native writing**. The protagonist perceives meaningful Spanish replacing it, like a hallucination. A blink or shift of attention can restore the square signs. Do not implement this as the ship announcing that it has switched its language to Spanish. Keep the cause unresolved in the opening.

Recommended data/view separation:

```text
semantic message ID and actual game state
    -> authored native sentence and structured quantities
        -> syllabic glyph renderer: physical ship view
    -> authored Spanish perception string
        -> optional protagonist perception overlay
```

The Spanish may add articles, supply a known character's gender, reorder words or compress a phrase. Do not force the native grammar to resemble Spanish. Preserve the underlying count, polarity, operating state and local clock quantities in both views. Keep the native layer stable beneath any perception effect.

`Tewa` is the retained adaptation of Tierra, written `te` + `wa`. The builders' homeworld is `ko lu ki wena`, literally Our Planet. `po wena`, outside/stranger planet, can mean Earth or enemy planet in context. Do not swap these worlds or let the English phrase “our planet” silently change the proper name's referent when an outsider quotes it.

The synopsis contains full spoilers. Use it to maintain story continuity; do not expose its betrayal, death or ending material in early environmental labels. Leave arrival, survival and the totality of Earth's casualties unresolved as the supplied synopsis does.

## 11. Story appendix vocabulary

Retain these as the disclosed supplement to the 274-entry reference:

| Root | Meaning |
|---|---|
| `tapo` | Awaken/become awake; `talo` is wakefulness |
| `mene` | Remember; distinct from know |
| `pateli` | Writing/written signs; `pema` is the display |
| `chenu` | Try/attempt + bare task; does not assert success |
| `shalo` | War/wage war |
| `lamu` | Pregnant/gestating |
| `mepe` | Hide/conceal |
| `pame` | Restrain/hold back |
| `pome` | Accidental/unintentional; `pome chela` marks manner |
| `tasho` | Assigned task/directive; does not replace `nu` |
| `tela` | Die; `tale` alive; `woteshi` death |

Descriptive compounds in the synopsis include `kalo kama`, thrust engine/conventional propulsion; `showa makiwa pama`, star-coordinate room/astrometrics; `pishi chena`, report signals/logs; `tewe lina`, protection system/defenses; and `kuta mapeshu`, killing tool/weapon. `Eshapani` is the proposed proper name for Spanish, `e-sha-pa-ni`.

## 12. What to implement and verify

1. Read the repository instructions and locate its existing UI/localization/rendering code. Keep an existing compatible implementation rather than replacing it gratuitously.
2. Add a single canonical syllable table and the exact component geometry. Generate all 50 signs from it. Keep the Romanized source strings versioned.
3. Produce a labeled 10 x 5 proof sheet in the same order as language-reference page 2. Compare every sign, especially `n` versus `w`, the five lower vowel forms, and the `sh/ch` crossbars.
4. Pick the engine's production representation and verify actual console resolution, scaling, wrapping, clipping, stroke weight, and fallback behavior.
5. Connect semantic label keys to approved native strings and separate Spanish perception strings. Missing native translations should be visible in development rather than silently shown in English or fake glyphs.
6. Implement local clock formatting and numerical rendering from structured values, separate from Earth physical-time conversion. Test full-day rollover and both hands of the analog display.
7. Check relationship/count selection, tense, polarity, word boundaries and equipment state against the supplied translation fixtures. Use roles or stable IDs where several people would otherwise become ambiguous.
8. Document new vocabulary and unresolved design choices. Do not coin replacements for established words merely to make a label shorter.

Minimum useful checks:

```python
from naleya_glyphs import SYLLABLES, syllabify, clock, octal, chunk_units

assert len(SYLLABLES) == len(set(SYLLABLES)) == 50
assert syllabify('shasha') == ['sha', 'sha']
assert syllabify('peshupa') == ['pe', 'shu', 'pa']
assert syllabify('mokepopu') == ['mo', 'ke', 'po', 'pu']
assert syllabify('Tewa') == ['te', 'wa']
assert octal(8) == '10' and octal(64) == '100' and octal(512) == '1000'
assert clock(7, 16) == '07:20'
assert clock(20, 3) == '24:03'
assert clock(16, 0, 0) == '20:00:00'
assert clock(31, 63, 63) == '37:77:77'
assert chunk_units('07') == [('glyph', 'mo'), ('glyph', 'shu')]

for bad in ['hello', 'veseo', 'tierra', 'psha', 'pesh-u']:
    try:
        syllabify(bad)
    except ValueError:
        pass
    else:
        raise AssertionError(bad)

# Also exercise the game clock: the beat after (31, 63, 63) rolls to
# (0, 0, 0), with the day incremented. Formatting alone does not advance time.
```

Acceptance: exact supplied shapes, one sign per valid syllable, native numerical signs, full 32-hour clocks, authored native grammar, consistent relationship/count semantics, and a separate Spanish perception layer that preserves the same underlying facts.
