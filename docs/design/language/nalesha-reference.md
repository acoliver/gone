# Nalesha language reference

> **Status:** Working name **Nalesha**, version **v0.13**, dated 22 October 2026. The synopsis uses **Naleya** as the project name for the same script and grammar; the final name remains open. Native glyphs appear in all three archived source PDFs in [`docs/design/sources/`](../sources/); text extraction preserves romanization, not glyph artwork. The Spanish story bible, [`docs/design/biblia.md`](../biblia.md), takes precedence on story facts. This digest follows *Gone_Naleya_Language_Reference.txt* unless a note identifies a synopsis addition or correction.

## Scope and pronunciation

Nalesha is the shipbuilders' language. It has five stable vowels, **a, e, i, o, u**, approximately as in Spanish. Adjacent vowels remain separate syllables. The consonants are **p, t, k, m, n, l, w, sh, ch**. The p-family includes p-like and b-like realizations that do not distinguish words. **sh** is the sustained hushing sound, **ch** the stop-plus-hush in English *chair*. Each is one consonant despite the two-letter romanization. No independent r, h, v, English y, or separate s occurs. Syllables are V or CV, with no clusters or final consonants.

The oldest network favored a smaller standard sound inventory; the exact sound losses are setting-specific. Long-distance voice networks spread an administrative pronunciation. Printing fixed the component system, and segmented displays favored broad square strokes. The current ship register is regular, while accents, idioms and names retain older variation.

The penultimate syllable has gentle prominence: **NA**-wa, **TA**-la, na-**LE**-sha. Unstressed vowels remain audible. A word rises slightly toward its prominent syllable and releases afterward; phrases can carry a broader rise and fall. Pitch does not distinguish words, tense or gender. Emotion and region can affect melody. Alarm speech stretches important words and repeats whole clauses rather than using a musical interval to carry essential meaning.

## The 50 syllable signs

Read left to right. One cell represents one pronounced syllable. Consonant structure occupies the upper band and vowel structure the lower band. A vowel-only sign has a small upper carrier with no consonant sound. The signs are original designs, not Earth-script substitutions. Character cells have equal width, with wider spaces between words. Components are systematic; dots, rotation and case do not alter pronunciation.

| Onset | a | e | i | o | u |
|---|---|---|---|---|---|
| vowel only | a | e | i | o | u |
| p | pa | pe | pi | po | pu |
| t | ta | te | ti | to | tu |
| k | ka | ke | ki | ko | ku |
| m | ma | me | mi | mo | mu |
| n | na | ne | ni | no | nu |
| l | la | le | li | lo | lu |
| w | wa | we | wi | wo | wu |
| sh | sha | she | shi | sho | shu |
| ch | cha | che | chi | cho | chu |

The extracted PDF did not preserve native sign artwork. Consult the original PDF for glyph shapes and native typesetting. Numbers use the same phonetic signs, not Arabic digits. A boxed group marks a reference or equipment identifier, read digit by digit. A missing symbol never implies a numeral. Punctuation occupies word gaps.

## Grammar

### Clause, predicate and tense

The basic order is **subject + [negation] + finite predicate + [object or task]**. The present is unmarked; an unmarked action is ongoing unless context says otherwise. Attach **-pa** to a predicate for an event that ended before now, at any distance. For a past state, **-pa** locates the condition in the past; context can say whether it continues. Attach **-pu** for an expected event very soon, unless an explicit time phrase supplies a later time. Tense stays on the predicate even when a time phrase moves the event. Verbs do not agree with gender, count or rank. There is no separate be-verb, article, gerund, progressive conjugation, past-perfect or subjunctive conjugation.

Past actions may overlap through **la** (while/during), without a special progressive form. General truths and habits use a bare predicate with context or a repeated-time expression. **pami** marks earlier/before; **pumi** after/later, and between tasks means then. **nemi** is now. Explicit times anchor the interval but do not replace predicate endings. A future conditional uses bare predicate in the **she** (if) clause and -pu in its consequence; the consequence is expected after its condition, not necessarily soon after speaking. A generic consequence may stay bare. **shome** introduces an imagined alternative while ordinary tense remains.

A nominal predicate takes tense on its noun head; a location predicate takes tense on **to**. Objects do not inherit predicate tense. **Malu lokemi** means “the ship is damaged.” **Malu lakemupu** means “the ship is going to be destroyed.”

### Negation, necessity, ability and permission

**cha** negates the following predicate or operator, and also serves as a negative reply. Its position controls scope: **cha nu** means no necessity, “need not”; **nu cha** means necessity not to act, “must not.” The source's line 539 wording “nu no kuta” conflicts with its defined negator and is corrected to **nu cha kuta** in the errata below. **cha pe** means cannot; **pe** marks ability, not moral judgment. The form alone does not distinguish ethical refusal from practical inability.

**nu** covers need, must, should and have to. It is the finite predicate; its task verb remains bare. Thus **nupa** means needed and **nupu** going to need. Context supplies urgency. **pe** means able or possible, and can scope over a statement in **pe wele** (“it is possible that”). **poli** means permitted/allowed, distinct from ability. **chawi + addressee + bare task** requests an action. Requests, orders and requirements have no special imperative conjugation; authority, responsibility, relationship and urgency determine their social force. A bare task can function as a command in context.

**Chali + beneficiary + bare task** means help someone act. One finite predicate can govern a task chain. A following task begins when the preceding step reaches its required endpoint; its ongoing activity need not stop. Independent assertions carry their own tense. **li** joins equivalent phrases or clauses. **pumi** can order steps; one requirement, request or permission can govern a coordinated chain. Permission for one step does not imply permission for a later step. **cho** affirms the proposition, including a negatively phrased one; **cha** denies it. Repeat a short clause when useful to make a reply clear. **ku** reports task completion; acknowledgment does not itself assert completion.

### Questions, reference and pronouns

**ka** ends a yes/no question. A question word takes the place of the unknown item: **ke** what, **me** who, **ke maki** asks “how many”; **maki** means quantity or count. There is no object-case ending. Pronouns retain the same form as subject, object or association anchor. A repeated topic can be omitted once established, but the predicate retains its tense. Technical reports repeat referents when ambiguity matters.

Person stems are **ko** speaker, **wu** addressee and **ni** third person. Add a count: **na** one, **mu** two, **lu** multiple with exact count unspecified. Add **-sho** for a close personal bond or **-po** for a non-close relationship: **nisho** close third person, **nipo** non-close third person, **wusho** close addressee, **wupo** non-close addressee. Bare **wu** or **ni** plus a count leaves the relationship unstated, useful for objects, unknown referents or deliberate vagueness. Pronouns carry no gender. Self-directed action repeats the pronoun, as in **Ko na tewo ko na** (“I am treating myself”).

The computer consistently uses **wupo** for the addressee and **nipo** for third parties outside its group. A threat display can make nipo mean enemy; elsewhere it can mean visitor, outsider or another crew. Wupo itself does not mean enemy. Rank does not determine closeness; custom normally leaves the first close address to the senior person. Withholding a close form after it has been offered is an insult. Between romantic partners, switching from close to non-close address signals a breakup; temporary conflict can retain close address. A familiar third-person outsider form can imply an enemy, but context may identify a non-hostile outsider.

**wa** and **che** identify this/nearer and that/other established referent without gender or grammatical case. Establish their referents first. When two established third referents compete, **wa ni na** resumes the focus and **che ni na** distinguishes the other. **ni na** itself suits a person or thing and is relationship-neutral. In indirect reports, pronouns and relationship markers remain anchored to the current speaker. Direct quotation establishes the quoted speaker's viewpoint.

### Kinship, affiliation, association and compounds

**X po Y** means Y comes from X; **X wo Y** means Y is a source of X. Thus **ko na po mali** is my offspring, a person from me; **ko na wo mali** is my parent, the person I come from. Explicit nouns **namo** man and **napa** woman supply gender when wanted. **-pi** narrows a relationship to kin; **-sha** identifies a mate. For example, **namo**, man; **namopi**, a man in the family; **namosha**, male mate; **namopo**, outside man. Age is not implied by origin expressions.

**Possessor + count + ki + possessed head** expresses ownership, affiliation or association. Counts describe the possessor, not the possessions: **ko na ki mu waki**, my two things; **ko mu ki waki**, the thing associated with us two. **ki** also marks a belonging group: **ko na ki malu shapi**, my ship tribe/crew. **shapi** means tribe, crew, family or people according to its modifiers and context. **malu shapi** is crew, normally anchored to a ship tribe. **malipo** is an outside person, read as enemy or stranger by context. Anchoring exclusion to a prior group gives betrayal: **ko lu ki malipo**, our outsider, normally traitor; it denotes a broken bond, not ownership of a stranger.

Compounds are modifier-before-head, with the final word as head: **tala pama**, stasis bay; **nawa lina**, energy system; **sheni pelo**, navigation console; **shasha nawa lina**, reserve power system. Spaces remain between roots. A numeral precedes its noun: **mu malu**, two ships. Do not add **lu** after an explicit numerical quantity. **te + number** marks order, as **te mu nawa lina**, second power system, distinct from a reserve system.

A quality precedes its noun and follows a subject as predicate: **mokemi kimela pelo**, broken computer terminal; **kimela pelo mokemi**, the terminal is broken. Several equal modifiers join with **li**. **chela** explicitly marks manner after a quality: **welu chela peshu**, repair carefully. Attributive negation precedes the quality: **cha welu mali**, a person who is not careful. If the action definitely happened, assert the action and lack of care separately. In coordinated actions, **wenu chela** marks coordinated action together. **cha wele** negates a whole statement. This differs from negation that applies to every member of a set, as in **ma shapi mali cha ...**.

**wemi** is benevolent moral nature and **mashu** malevolent moral nature. Neither is taste, health or machinery status. **shuma** is tasty, **lopi** harmful, **nelo** correct judgment and **loka** wrong judgment or unacceptable act.

### Clauses and logical relations

**wele** introduces statement content after knowing, believing, thinking or reporting. **mewa** follows a noun phrase to introduce a relative clause in which that noun supplies one missing argument. **kume** closes an embedded clause when the outer statement resumes; it may be omitted at an unambiguous utterance end. Connectors are fully pronounced; pitch, stress and pause do not replace them. **poma** introduces an asserted cause; **lashi** an intended purpose, without claiming success. **shome** scopes an imagined condition and result. **meli** means think/judge/infer and remains open to revision; **wome** believe/accept as true; **pisha** know/recognize, without guaranteeing the speaker is correct. Outer and embedded predicates independently carry tense. Negating belief differs from believing a negative statement.

**lo** joins alternatives. **li** joins equivalent phrases or clauses. **wenu** means with/accompanied by, not partnership or possession. **pata** joins components or describes committed partnership between people. **komu** is the continuing joined bond. **toka** means enter; with a place it is spatial entry, with a person as object in an intimate context it expresses sex. With a movement verb, a place can be a direct object or follow **ta**: **toka tala pama** / **toka ta tala pama**. Entering does not itself establish partnership. Repeated shared meals can conventionally suggest dating in a social context, but work, family and crew meals need not imply it.

### Quantity, comparison and time

Numbers and quantifiers apply to a selected set. **ma** all/whole; **washi** each, distributed over members; **shomi** some, at least one, without excluding all; **kumi** only, excluding relevant alternatives; **mo** zero/none. **chome** means different/distinct. **lako** more/greater; **molu** less/fewer; **woli** equal in the stated property; **mopu** introduces the comparison standard; **kami** almost/near but short of a target. **pani** adequate against a goal and **shaku** excessive relative to a goal.

**wama** marks a continuing state (still); **wumi** marks a state reached by the reference time (already). Both precede the predicate and do not require **chela**; **tame** follows a negative predicate for not yet; **temi** sets an ending boundary (until); **nape** sets a starting boundary (since). The default reference time is now. **nali** marks recurrence; **nalemi** regular/habitual. An until statement bounds its asserted interval; state any later death or shutdown separately if relevant.

Comparison follows **A + comparison operator + property + mopu + B**. The operator takes tense when needed; the property remains bare.

### Identifiers

**nami** introduces a stable reference label after the counted pronoun. Labels identify a discourse referent, not its count, gender or rank. Names, roles and labels remain attached to the referent as subject, object or possessor. Written identifiers are boxed and read digit by digit. In speech, **kume** can close a multi-digit identifier when following words might be mistaken for digits. Count words retain ordinary place-value reading. Distinct labels alone do not prove distinct bodies.

### Numbers

Native numbers are base eight. The digit words for values 0 through 7 are **mo, na, mu, shi, le, chi, wi, shu**. Eight is written 10, not a ninth digit. Place words are **nala** = 10 octal (8 decimal), **naka** = 100 octal (64), **nata** = 1000 octal (512), **we** = 10000 octal (4096), **chu** = 100000 octal (32768). We and chu are place words, not digits.

Formal cardinal speech names each nonzero place with its multiplier; zero-valued places are omitted: **na nala mu** = 12 octal (10 decimal), **mu nala le** = 24 octal (20), **na naka chi** = 105 octal (69), **na nata mu naka shi nala le** = 1234 octal (668). Boxed identifiers retain every digit and are read digit by digit: 105 is **na mo chi**. A radix tick introduces base-eight fractional digits. Units follow measured quantities. Quantities, counts, ordinal labels and boxed identifiers are distinct constructions.

### Native clock

The full day contains 32 local hours, written 40 in octal. Hour labels run 00 through 37, then return to 00; 40 describes a duration of one day and is not an hour label. Each hour has 100 octal intervals (64 decimal), and each interval has 100 octal beats (64 decimal). The format is **hour:interval:beat**; interval and beat labels run 00 through 77. Rollover is 37:77:77 to 00:00:00 the next day. The halfway point 20:00:00 does not reset the clock. There is no AM/PM, half-day, 12-hour or 16-hour convention. Daylight does not create another numbering system. These are local units; no conversion to Earth seconds is defined. Preserve the local quantity and clock convention when translating; Earth-decimal values in this reference explain values for readers and do not define a second ship numbering system. The source calls the local year **tanu**, but gives no Earth-year duration. Story durations explicitly identified as Earth years remain Earth-year quantities.

## Lexicon

The following tables preserve all **274 numbered entries**, in the source's groupings. “Use” retains the source's distinctions and cautions. Romanized compounds are shown as in the source. The source's native-script column cannot be reconstructed from the text extraction.

### Grammar and pronouns, 001–025

| No. | Word | Meaning | Use |
|---:|---|---|---|
| 001 | ko | first person | Add count: ko na = I; ko lu = we. No gender marking. |
| 002 | wu | second person | Wusho = bonded; wupo = non-close. Add a count. |
| 003 | pi | kin; family relation | Bound suffix on a person word; namopi = male kin. |
| 004 | ni | third person | Nisho = bonded; nipo = non-close. Add a count. |
| 005 | lu | plural; several | Unspecified multiple count; ko lu = we, wu lu = you all. |
| 006 | ki | association; belonging | Possessor + ki + possessed head; counts describe each referent. |
| 007 | pa | past ending | Predicate ending: event ended before now, at any time distance. |
| 008 | ne | current; contemporary | Optional lexical time modifier; never a required present-tense particle. |
| 009 | pu | future ending | Predicate ending: expected very soon unless time is specified. |
| 010 | la | while; during | Temporal overlap. Bare present actions are already ongoing. |
| 011 | ku | finished; completed | Finished/completed. As task reply, reports completion. |
| 012 | cha | not; denial | Negates following predicate or operator; also a negative reply. |
| 013 | cho | affirmation; yes | Affirms the proposition, including a negatively phrased proposition. |
| 014 | ka | yes/no question | Placed at the end of a polar question. |
| 015 | ke | what | Appears where the unknown thing belongs. |
| 016 | me | who | Appears where the unknown person belongs. |
| 017 | to | at; in; on | Location relation, not the verb activate. |
| 018 | ta | to; toward | Destination, recipient, result or nominal goal, such as a meal. |
| 019 | po | outside; from; non-close | X po Y = Y from X. On pronouns, marks non-close relation. |
| 020 | li | and | Joins equivalent phrases or clauses. |
| 021 | lo | or | Joins alternatives. |
| 022 | she | if | Open condition: bare predicate after if; -pu in future result. |
| 023 | te | ordinal marker | Precedes a number: te mu = second. |
| 024 | nu | need; must; should | Need/must/should/have to; task requirement can be impersonal. |
| 025 | pe | can; possible | Ability or possibility, not permission by default. |

### People and the body, 026–050

| No. | Word | Meaning | Use |
|---:|---|---|---|
| 026 | mali | person; human | Member of their human community, not all living things. |
| 027 | namo | man; male person | Explicit male noun; origin expression does not imply age. |
| 028 | napa | woman; female person | Explicit female noun; origin expression does not imply age. |
| 029 | nasha | child | A person before adult status. |
| 030 | mila | body | Organism's physical body; technical use for hull body is possible. |
| 031 | nami | name; designation | Name or stable reference ID; follows counted pronoun when needed. |
| 032 | malu shapi | crew; ship tribe | Normally anchored: ko na ki malu shapi. |
| 033 | nalu | commander | Person holding command; not necessarily a military rank. |
| 034 | neli | operator; specialist | Trained person responsible for a function. |
| 035 | noli | passenger | Carried person without an operating assignment. |
| 036 | sha | mate; pair relation | Bound person suffix; namosha = male mate. |
| 037 | shapi | tribe; belonging group | Family, crew or people as a social collective, by context. |
| 038 | ko na wo mali | parent; progenitor | ko na wo mali = person I come from. |
| 039 | ko na po mali | offspring | ko na po mali = person who comes from me. |
| 040 | wachapi | elder | Older person, sometimes a title of respect. |
| 041 | kuta | kill | Cause death; a person or hazard can be the subject. |
| 042 | lami | head | Body part; not the default term for a leader. |
| 043 | lapi | hand | Grasping body part; extension to manipulator is natural. |
| 044 | lani | eye | Seeing organ; can describe a camera in informal speech. |
| 045 | chelenu | ear | Hearing organ. |
| 046 | shelumi | mouth | Speaking or eating opening. |
| 047 | wamolu | blood | Circulating bodily fluid; distinct from coolant. |
| 048 | melo | mind; thought | Mental activity or an individual thought, by context. |
| 049 | nima | voice | A person's audible expression or a synthesized voice. |
| 050 | loma | foot; supporting limb | Standing or walking support of a body. |

### Space and navigation, 051–075

| No. | Word | Meaning | Use |
|---:|---|---|---|
| 051 | malu | vessel; ship | Inhabited carrier; not restricted to spacecraft. |
| 052 | wena | world; planet | Planetary world, sometimes its inhabited environment. |
| 053 | showa | star; sun | Stellar body, including the local sun. |
| 054 | showi | outer space | Expanse between worlds; not empty volume in a tank. |
| 055 | moshali | moon | Natural satellite. |
| 056 | shena | heading; course | Direction selected for travel. |
| 057 | sheni | navigation | Finding and maintaining a route; also navigation function. |
| 058 | washano | position | Where an object is located. |
| 059 | shanu | destination | Intended endpoint of travel. |
| 060 | shela | route; path | Traversable way, physical or planned. |
| 061 | sheli | distance | Separation measured along an agreed reference. |
| 062 | waleno | speed | Rate of movement; direction specified separately. |
| 063 | shulu | direction | Orientation or bearing. |
| 064 | mishela | map; chart | Spatial representation. |
| 065 | shuna | orbit | Repeating gravitational route. |
| 066 | washela | trajectory | Projected or observed movement path. |
| 067 | shuwi | transit | Passage between locations; does not imply faster-than-light travel. |
| 068 | shuwo | arrival | Reaching a destination or arrival state. |
| 069 | shapo | departure | Leaving an origin. |
| 070 | shipo | approach; come toward | Approach destination or come toward reference location. |
| 071 | chawu | port; haven | Place where vessels can shelter and exchange people or goods. |
| 072 | chesha | beacon | Identifiable source used for guidance. |
| 073 | makiwa | coordinate | Component of a reference position. |
| 074 | wepata | vector | Directed magnitude in technical use. |
| 075 | walowa | horizon; visible limit | Boundary of a view, physical or instrument-defined. |

### Power and machinery, 076–100

| No. | Word | Meaning | Use |
|---:|---|---|---|
| 076 | nawa | flow; drive; energy | Shared root for energetic activity; not political authority. |
| 077 | lina | system; linked assembly | Interacting parts considered as a functional whole. |
| 078 | kama | engine; drive unit | Machine whose work produces propulsion or movement. |
| 079 | chami | generator | Device producing usable electrical power. |
| 080 | wakemo | reactor | Controlled energy-producing reaction chamber. |
| 081 | walu | battery; energy store | Device retaining energy for later release. |
| 082 | kana | conduit; channel | Route carrying fluid, energy or signal. |
| 083 | mikani | circuit | Completed functional path, particularly electrical. |
| 084 | papelo | distribution bus | Shared path supplying multiple branches. |
| 085 | komu | coupling; joined bond | Connection between parts; continuing partnership between people. |
| 086 | shokala | valve | Component regulating passage through a conduit. |
| 087 | kali | pump | Device driving fluid circulation. |
| 088 | kalo | force; thrust | Physical push; propulsion force in engine contexts. |
| 089 | wetani | coolant | Working fluid used to carry away heat. |
| 090 | kela | heat; temperature | Thermal condition; a unit or context specifies the measurement. |
| 091 | pukeli | pressure | Force per area in technical use; also a pressing condition. |
| 092 | kelo | electric current | Electrical flow; the technical narrowing of the older flow vocabulary. |
| 093 | meka | load; demand | Work or draw placed on a system. |
| 094 | wimeli | capacity | Amount a system can hold or deliver. |
| 095 | kemu | stock; stored supply | Quantity held for use, including material supplies. |
| 096 | shokemu | fuel | Consumable source of energy. |
| 097 | kewi | light; illumination | Emitted or received light, not a light fixture. |
| 098 | kewo | field | Distributed physical influence in technical contexts. |
| 099 | shoketa | sensor | Device detecting a physical condition. |
| 100 | chena | signal | Deliberately distinguishable transmission or indication. |

### Rooms and equipment, 101–125

| No. | Word | Meaning | Use |
|---:|---|---|---|
| 101 | pali | seat; sit | Sitting support as noun; sitting as action predicate. |
| 102 | mepalu | table; work surface | Raised surface used for work or eating. |
| 103 | pama | room; bay | Bounded functional space, not necessarily small. |
| 104 | lometa | deck; floor level | Walkable level of vessel. |
| 105 | pana | door; hatch | Closable passage between spaces. |
| 106 | shelani | corridor | Passage linking rooms. |
| 107 | wopa | wall | Lateral boundary or partition. |
| 108 | wamenu | ceiling | Overhead boundary of an occupied space. |
| 109 | pela | bed; berth | Support intended for resting or sleeping. |
| 110 | taleki | pod; capsule | Small enclosure for a person or payload. |
| 111 | pelo | console | Station for observing and directing equipment. |
| 112 | pelu | panel | Surface grouping controls, access points or indicators. |
| 113 | pema | display | Surface presenting visual information. |
| 114 | pemi | key; control | Individual input device, physical or projected. |
| 115 | lapita | handle; grip | Part intended to be held or operated by hand. |
| 116 | keweni | lamp | Device providing illumination. |
| 117 | shawela | window; viewport | Transparent opening, not software window by default. |
| 118 | lopewa | stairs; steps | Stepped passage between levels. |
| 119 | kotewa | lift | Platform or cabin carrying loads between levels. |
| 120 | shapewu | cabinet; locker | Enclosed storage fitting. |
| 121 | pesha | clothing; suit | Worn covering; modifiers distinguish pressure suits. |
| 122 | peshi | helmet | Protective head covering. |
| 123 | penasha | seal; gasket | Fitted barrier preventing unwanted passage. |
| 124 | mapeshu | tool | Portable implement used to perform work. |
| 125 | chashu | vent | Opening for controlled gas passage. |

### Life support and stasis, 126–150

| No. | Word | Meaning | Use |
|---:|---|---|---|
| 126 | tala | stasis; suspension | Held biological state; not ordinary sleep. |
| 127 | tali | sleep | Normal biological sleep. |
| 128 | talo | wakefulness | Awake, responsive state; not necessarily full recovery. |
| 129 | talu | life support | Maintaining conditions required for occupants to live. |
| 130 | tana | air; breath | Breathing medium in everyday use. |
| 131 | tani | water | Water as substance, not any fluid. |
| 132 | mato | food | Material intended for nourishment. |
| 133 | wanu | waste | Material rejected from a living or working process. |
| 134 | mewela | medicine | Therapeutic substance or practice, by context. |
| 135 | lopu | injury | Physical harm to a body. |
| 136 | lapu | pain | Unpleasant bodily sensation. |
| 137 | tema | illness | Harmful biological condition. |
| 138 | shemi | infection | Invasion or spread of a biological agent. |
| 139 | temo | clean; sterile | Free of the relevant contamination; a standard fixes the threshold. |
| 140 | shashumu | contaminated | Contains unwanted material or organisms. |
| 141 | tena | containment | Holding substance or organism within controlled bounds. |
| 142 | shoteni | oxygen | Technical substance name within breathing-air vocabulary. |
| 143 | teno | atmosphere | Gas envelope or enclosed gas environment. |
| 144 | mapenu | gravity | Gravitational attraction or experienced downward pull. |
| 145 | tewe | protection; shelter | Keeping person or thing from harmful exposure. |
| 146 | mitewi | patient | Person receiving treatment, not adjective patient. |
| 147 | tewo | treat; treatment | Intervention intended to improve a biological condition. |
| 148 | tewu | recovery | Return toward functioning biological state. |
| 149 | shosha | organism | Living individual, human or otherwise. |
| 150 | woteshi | death | End of an organism's life. |

### States and actions, 151–175

| No. | Word | Meaning | Use |
|---:|---|---|---|
| 151 | shenu | actively working; running | Currently performing relevant task, not merely powered. |
| 152 | palo | off; disengaged | Switched off or disengaged; does not assert a defect. |
| 153 | taka | emergency; dangerous breach | Urgent loss of safe conditions; bodily danger by context. |
| 154 | shasha | reserve; held ready | Set aside for use if needed, rather than merely second. |
| 155 | peshu | repair; restore | Perform repairs or restoration. A past repair attempt need not have succeeded. |
| 156 | moketa | fail; failure | Attempted or required operation fails; identify cause separately. |
| 157 | lokemi | damaged | Physically or functionally impaired. |
| 158 | lome | intact; sound | Undamaged in relevant inspection. |
| 159 | penu | ready; available | Capable with current prerequisites met. Weli alone asserts capability. |
| 160 | pena | low; scarce | Below expected operating amount. |
| 161 | pani | adequate; normal | Within required or accepted range. |
| 162 | shaku | high; excessive | Above accepted operating amount. |
| 163 | palu | open | Passage or access point is unclosed. |
| 164 | moku | closed | Passage/access point shut, not necessarily sealed. |
| 165 | toka | enter | Enter a place; input data; person object can express sex. |
| 166 | powe | exit | Move out of a place. |
| 167 | pata | connect; join | Join parts or committed partners; not merely accompany a meal. |
| 168 | kuni | disconnect | Break a working connection. |
| 169 | pasha | stop; halt | Cease activity or motion. |
| 170 | pashi | like; prefer | Experiencer is ordinary subject; no inverted construction. |
| 171 | pila | see; read | Interpret visual information; reading is contextual use. |
| 172 | chelapi | hear | Receive and interpret sound. |
| 173 | pisha | know; recognize | Assert knowledge or recognize; speaker can be mistaken or lying. |
| 174 | pishi | speak; report | Express information in speech; technical use includes reporting. |
| 175 | pita | change; set | Alter something, often with ta followed by target state. |

### Numbers and time, 176–200

| No. | Word | Meaning | Use |
|---:|---|---|---|
| 176 | mo | zero | Explicit zero; never represented by empty space. |
| 177 | na | one | Cardinal digit 1. |
| 178 | mu | two | Cardinal digit 2. |
| 179 | shi | three | Cardinal digit 3. |
| 180 | le | four | Cardinal digit 4. |
| 181 | chi | five | Cardinal digit 5. |
| 182 | wi | six | Cardinal digit 6. |
| 183 | shu | seven | Cardinal digit 7. |
| 184 | we | place 10000 in base eight | Value 4096 decimal; a place word, not a digit. |
| 185 | chu | place 100000 in base eight | Value 32768 decimal; a place word, not a digit. |
| 186 | nala | eight; place 10 | Base-eight place value 10; decimal value 8. |
| 187 | naka | place 100 in base eight | Decimal value 64, not decimal one hundred. |
| 188 | nata | place 1000 in base eight | Decimal value 512, not decimal one thousand. |
| 189 | nemi | now | Current reference time. |
| 190 | pami | before; earlier | Earlier-time expression; -pa still attaches to past predicate. |
| 191 | pumi | after; later | After / later; pumi between tasks means then, after the prior step. |
| 192 | tami | day; full clock cycle | 32 local hours, written 40 octal; clock runs 00 through 37. |
| 193 | shali | daylight; day | Light part of a planetary cycle. |
| 194 | shalu | darkness; night | Dark part of a planetary cycle. |
| 195 | teli | hour; watch | One of 32 local hours per day; contains 64 intervals. |
| 196 | tili | interval | One of 64 intervals per local hour; contains 64 beats. |
| 197 | tiki | beat | One of 64 beats per interval; not equated to an Earth second. |
| 198 | pala | beginning | Initial boundary of an event or span. |
| 199 | kalu | ending | Final boundary of an event or span. |
| 200 | nali | again; recurrence | Event repeats; not the tense marker for a new occurrence. |

### Relationships and expression, 201–208

| No. | Word | Meaning | Use |
|---:|---|---|---|
| 201 | sho | close; personally bonded | Real trusted bond, not automatic crew or rank category. |
| 202 | wo | source of; progenitor | X wo Y = Y is a source of X; inverse of X po Y. |
| 203 | ma | whole; totality | Whole/all quantifier; bound ma-kuta still means eradicate. |
| 204 | chali | help; assist | Chali + beneficiary + bare task; necessity scopes over task. |
| 205 | loka | wrong; incorrect | Incorrect judgment or unacceptable act, not generic equipment rating. |
| 206 | naki | large base-eight place | 10000000000 octal = 1073741824 decimal; 8 to the power 10. |
| 207 | wa | this; nearer referent | Identifies one discourse referent without assigning gender. |
| 208 | che | that; other referent | Identifies another discourse referent without assigning gender. |

### Events, judgment and drives, 209–223

| No. | Word | Meaning | Use |
|---:|---|---|---|
| 209 | waki | thing; entity | Nonspecific entity, distinct from mali person. Po waki is a stranger or unidentified outside thing. |
| 210 | taku | hit; strike; impact | Taku ongoing; takupa ended impact; takupu imminent expected impact. |
| 211 | nelo | right; correct | Correctness of judgment or claim, not direction or moral purity. |
| 212 | mashu | evil; malevolent nature | Moral nature, distinct from fault, taste or physical harm. |
| 213 | lopi | harmful; injurious | Causes or tends to cause harm; does not imply malicious intent. |
| 214 | tanewa | smoke | Airborne products of burning; not ordinary air. |
| 215 | tane | breathe; inhale | Take a breathing medium into the body. Tane tanewa = breathing smoke. |
| 216 | lakemu | destroyed; ruined | Beyond usable function in context; stronger than damaged. |
| 217 | pake | happen; occur | Event takes place; -pu expresses expected imminent occurrence. |
| 218 | nawi | space; spatial extent | Space as medium/extent folded, distinct from outer space showi. |
| 219 | wesha | fold; bend over | Ordinary folding root extended to spatial folding in engineering. |
| 220 | chalu | ride; travel carried | Travel supported or carried along a medium; technical H-drive metaphor. |
| 221 | nawi wesha kama | S-drive; space-fold engine | Folds space. Can be used with conventional propulsion, but travel is much slower. |
| 222 | chalu kama | H-drive; ride engine | Moves efficiently through S-fold; useless without that fold. |
| 223 | tanu | year | Local year; physical duration relative to Earth year unspecified. |

### Qualities, operation and joining, 224–234

| No. | Word | Meaning | Use |
|---:|---|---|---|
| 224 | wemi | good; benevolent nature | Moral opposite of mashu; not tasty, healthy or operational. |
| 225 | shuma | tasty; pleasant in flavor | Sensory food taste, not moral goodness. |
| 226 | weli | functional; capable | Able to perform function when supplied prerequisites. |
| 227 | mokemi | broken; faulted | Defect prevents proper function despite normal prerequisites. |
| 228 | paleno | idle; standing by | Powered and capable, with no assigned task running. |
| 229 | naweli | powered; energized | Supplied with usable power; says nothing about capability. |
| 230 | kimela | compute; calculation | Processing information; kimela lina = computer, kimela pelo = terminal. |
| 231 | kimela lina | computer | Computation system, rather than physical display alone. |
| 232 | kimela pelo | computer terminal | Console providing access to computation or ship network. |
| 233 | chela | manner linker | Quality + chela before predicate marks how action is performed. |
| 234 | welu | careful; attentive | Attention to relevant conditions; not itself moral nature. |

### Accompaniment, motion and rupture, 235–244

| No. | Word | Meaning | Use |
|---:|---|---|---|
| 235 | paki | part; component | Constituent that can be joined to another part. |
| 236 | mate | eat | Consume food. Mate wenu someone means eat with that person. |
| 237 | wenu | with; accompanied by | Shared participation, not possession or partnership by itself. |
| 238 | shuli | quick; rapid | High rate or short completion time, specified by context. |
| 239 | lowi | move; movement | Change position; with object, move it. Ta marks destination. |
| 240 | nalemi | regular; habitual | Recurring pattern; frequency can modify action with chela. |
| 241 | moke | break; rupture | Action of breaking, unlike broken-state mokemi. |
| 242 | mokepo | explode; rupture outward | Moke + po outward; violent outward rupture or release in context. |
| 243 | moketo | implode; rupture inward | Moke + to inward; collapse toward interior in context. |
| 244 | mali waki | robot; person-thing | Person + thing, with thing as head; does not itself mean evil. |

### Clauses, certainty and permission, 245–258

| No. | Word | Meaning | Use |
|---:|---|---|---|
| 245 | wele | that; statement linker | Introduces content of knowledge, belief, thought or report. |
| 246 | mewa | relative-clause linker | Follows described noun; that noun fills one missing argument. |
| 247 | kume | embedded-clause ending | Closes embedded clause or delimited spoken identifier. |
| 248 | poma | because; reason | Introduces asserted cause, distinct from intended purpose. |
| 249 | lashi | so that; intended purpose | Introduces a goal; does not assert it was achieved. |
| 250 | shome | suppose; imagined case | Scopes imagined condition and result; ordinary tense applies. |
| 251 | wome | believe; accept as true | Belief or conviction, not necessarily tentative opinion. |
| 252 | meli | think; judge; infer | Present assessment or reasoning, open to revision. |
| 253 | poli | permitted; allowed | Permission status of subject; distinct from ability pe. |
| 254 | chawi | request; ask to act | Chawi + addressee + bare task. Tense attaches to chawi. |
| 255 | wape | receive; obtain | Receive offered object; permission question can request one. |
| 256 | laku | increase; raise quantity | Increase quantity such as speed; not merely set it high. |
| 257 | toli | stay; remain | Continue at a location; la shalu specifies during night. |
| 258 | shalu mato | dinner; night meal | Conventional meal name using night/darkness plus food. |

### Quantity, comparison and time, 259–274

| No. | Word | Meaning | Use |
|---:|---|---|---|
| 259 | washi | each; distributively | Applies predicate separately to every member of stated set. |
| 260 | shomi | some; at least one | Nonempty part of active set; does not itself exclude all. |
| 261 | kumi | only; exclusively | Precedes focused constituent and excludes relevant alternatives. |
| 262 | chome | different; distinct | Difference in relevant identity or property, stated by context. |
| 263 | lako | more; greater | Comparison operator; a property and mopu standard can follow. |
| 264 | molu | less; fewer | Comparison operator for quantity, count or degree. |
| 265 | woli | equal in value | Equality in stated property; not automatic identity of objects. |
| 266 | mopu | compared with; than | Introduces comparison standard after degree or property. |
| 267 | kami | almost; nearly | Near a stated threshold without having reached it at reference time. |
| 268 | wama | still; continuing | Stated event or condition continues at reference time. |
| 269 | wumi | already; attained by now | Event or state reached by reference time. |
| 270 | tame | yet; by reference time | With negative predicate, not yet within stated interval. |
| 271 | temi | until; ending boundary | Sets end of interval; can introduce time or clause. |
| 272 | nape | since; starting boundary | Sets start of interval; can introduce time or clause. |
| 273 | tale | alive; living | Life state, independent of wakefulness, stasis or working machinery. |
| 274 | maki | quantity; count | Number or amount being compared or asked about. |

## Names and naming patterns

The native names below are examples, not casting decisions. Names use the same syllable inventory, and their meanings need not be transparent to contemporary speakers. Names are not gender-coded by final vowel. A personal name comes first; a family or house name can follow without a particle. Example full names: **Talemi Pashona**, **Kapiwa Melashu**, **Shenali Towapi**. These surnames are proper names, not common-word entries. **Nalu Talemi** means Commander Talemi.

Example personal names and pronunciations: **Talemi** (ta-LE-mi), **Kapiwa** (ka-PI-wa), **Shenali** (she-NA-li), **Mapelo** (ma-PE-lo), **Shawemi** (sha-WE-mi), **Welapa** (we-LA-pa), **Lapeshi** (la-PE-shi), **Nakelu** (na-KE-lu).

Example vessel and place names: **Pumi Shela**, “Later Path”; **Showa Kewi**, “Starlight” (literally star light); **Tewe Malu**, “Shelter Vessel”; **Shali Chawu**, “Daylight Haven.”

**Tewa** (TE-wa) is the borrowed name for Earth, adapted from Spanish *Tierra* to Nalesha sounds. It is a recent adaptation, not centuries of sound change. **ko lu ki wena**, literally “our planet,” is also the shipbuilders' homeworld's proper name. **po wena**, “outside planet,” is the conventional relational name for Earth in this setting; enemy planet is contextual, especially in military reports. **po wena po mali** means a person from the outside planet: the first **po** modifies the planet, and the second links origin. **Tewa po mali** means person from Earth. Po marks an outside boundary or origin, not hostility by itself. The homeworld's embedded “our” remains in its name when an outsider quotes it.

## Console and interface text

| English interface meaning | Perceived Spanish example | Nalesha romanization |
|---|---|---|
| Stasis bay | SALA DE ESTASIS | tala pama |
| Stasis pod | CÁPSULA DE ESTASIS | tala taleki |
| Secondary power system | SISTEMA DE ENERGÍA SECUNDARIO | te mu nawa lina |
| Reserve power system | SISTEMA DE ENERGÍA DE RESERVA | shasha nawa lina |
| Actively working | EN FUNCIONAMIENTO | shenu |
| Off / inactive | INACTIVO | palo |
| Engine | MOTOR | kama |
| Navigation console | CONSOLA DE NAVEGACIÓN | sheni pelo |
| Life support system | SISTEMA DE SOPORTE VITAL | talu lina |
| Emergency | EMERGENCIA | taka |
| Power is low | ENERGÍA BAJA | nawa pena |
| Engine has failed / is failing | FALLO DEL MOTOR | kama moketa |
| Hatch is open | ESCOTILLA ABIERTA | pana palu |
| Containment is failing | FALLO DE CONTENCIÓN | tena moketa |
| Stasis system is inactive | SISTEMA DE ESTASIS INACTIVO | tala lina palo |

These Spanish strings illustrate perceived renderings. The physical writing remains in Nalesha. The rendering can supply articles, change word order, turn a relationship syllable into a phrase, choose a Spanish pronoun from known context, or resolve several short words into one idiomatic label. Names usually remain names; boxed identifiers can appear as Earth digits. Recurring sign patterns may let the protagonist recognize a function before he can explain it. A glance may seem to show a Spanish label, then return to square characters. The panel need not animate or switch language.

The perceived Spanish expresses meanings without changing Nalesha's grammar. Keep its cause unresolved in the opening. Do not let the language label announce Earth, alien origin or Spanish before the story establishes that information.

## Addendum: synopsis vocabulary

These eleven roots extend v0.13 and do not appear in the original PDFs. They are disclosed by *Gone_Naleya_Story_Synopsis.txt*, not retroactively part of the original lexicon.

| Root | Meaning and use |
|---|---|
| tapo | awaken; become awake. **talo** remains the state of wakefulness. |
| mene | remember; recall earlier events or information, distinct from pisha “know.” |
| pateli | writing; written signs. **pema** is the physical display. |
| chenu | try; attempt. Chenu + bare task; a past attempt does not assert success. |
| shalo | war; wage war. Armed conflict between groups; does not assert moral evil. |
| lamu | pregnant; gestating. A biological state; pronouns and agreement remain genderless. |
| mepe | hide; conceal. Make an object unavailable to ordinary observation or discovery. |
| pame | restrain; hold back. Restrict movement; not necessarily injure. |
| pome | unintentional; accidental. **pome chela** marks an unintended action or outcome. |
| tasho | task assigned by an authority; directive. **nu** still supplies all must/need/should meanings. |
| tela | die. Become no longer alive. **tale** is alive; **woteshi** is death as a noun. |

**Eshapani** (e-sha-PA-ni) is a proposal for Spanish as a proper-name adaptation, not a confirmed addition. It names Spanish without claiming that all Earth speaks one language. **Tewa** names Earth in the reference and synopsis. Synopsis compounds and expressions:

| Form | Meaning and source note |
|---|---|
| wesha kama | S-drive / fold engine; short for nawi wesha kama. |
| chalu kama | H-drive / ride engine; works efficiently through the S-fold and is useless alone. |
| kalo kama | thrust engine / conventional propulsion; descriptive compound. |
| showa makiwa pama | astrometrics / star-coordinate room; descriptive room name. |
| pishi chena | report signals / logs; recorded reports, without implying every report is true. |
| tewe lina | protection system / defenses; can be dangerous to the protagonist. |
| kuta mapeshu | killing tool / weapon; the ship itself is the instrument. |
| malu shapi ki malipo | the crew's outsider / traitor; betrayal follows from broken belonging in context. |
| Ko Lu Ki Wena | Our Planet, the shipbuilders' homeworld name. |
| Tewa | Earth. |

## Project additions: navigation compounds

**Shelani paki** means section on ship navigation signs: literally “corridor part,” using **shelani** (106) and **paki** (235), modifier before head. This is a project compound, separate from the v0.13 lexicon and the synopsis additions above. It introduces no new root. Deck remains **lometa** (104), lift **kotewa** (119), and hatch **pana** (105).

Signs use boxed identifiers read digit by digit: deck 14 is `lometa [16]` (na wi); section 41 is `shelani paki [51]` (chi na). Perceived Spanish shows `CUBIERTA 14` and `SECCIÓN 41`. Square brackets in source text are renderer markup, never printed punctuation. The stroked rectangle, 0.72-unit stroke and one-unit padding beyond digit ink are implementation choices, not additions to the language rules.

## Errata and open questions

- **Negation erratum:** source reference line 539 says **nu no kuta**. It should read **nu cha kuta**, consistent with the defined negator cha. No second negator is introduced.
- Retro references such as **0xDEADBEEF** and **C:\>** are placeholders until their rendering is decided for native base-eight notation or the perceived-Spanish layer.
- The final language name remains open: Nalesha is the v0.13 working name; Naleya is the synopsis project name for the same language.
- The cause of the protagonist's perceived Spanish remains unresolved: perception, technology or an unreliable mind are possibilities, not decisions.
- Native glyph artwork appears in the three archived source PDFs in `docs/design/sources/`; text extraction does not preserve it.
