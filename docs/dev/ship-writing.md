# Ship writing and perceived Spanish

Ship displays physically contain Naleya writing. Spanish appears in the
protagonist's perception, in the same screen area. The ship does not change
language. The working power-room console keeps its existing two-press behavior.
STANDBY has no text. Its heading is `te mu nawa lina`, perceived as
SISTEMA DE ENERGÍA SECUNDARIO. INACTIVE shows `palo`, perceived as INACTIVO;
ACTIVE shows `shenu`, perceived as EN FUNCIONAMIENTO.

## Data and drawing

`app/ship_text.gd` maps semantic message ids to `native` and `perceived_es`.
Native text is stored as romanized words. Loading the catalog validates every
word with `Naleya.syllabify`; missing ids or invalid native writing report an
error. Native rendering never uses a Latin font.

`ShipTextCanvas` lays out native writing with `Naleya.layout` and draws the
quads returned by `Naleya.expand_strokes`. It applies the canvas y inversion
once. The heading and state word remain at the old screen positions, with
native ink heights of about 0.05 m and 0.10 m. Spanish uses Godot's fallback
font, centered in those areas and reduced in size if necessary to fit.

`ShipTextCache` owns at most two reusable transparent raster SubViewports for
all scene text. It copies completed images after `frame_post_draw` into shared
`ImageTexture` pairs, one unique pair per frame on cache misses. Its key includes
both complete strings, style, dimensions, layout version and font identity.
Reference counts protect resident pairs; LRU eviction retains at most 32
unreferenced pairs. Headless tests exercise queue and image completion without
awaiting rendering. A separate windowed integration checks the GPU boundary.

`ShipDisplay` retains its 1024 by 640 console style and observable semantic
canvases, without owning raster viewports. Approaching the power doorway
prefetches both console states. Each display and navigation sign owns its own
blend material. The screen shader crossfades the texture alpha masks. Its nine-tap blur radius rises from zero
to 12 texture pixels on native ink and falls from 12 to zero on Spanish.
Both opacity and blur depend only on `perceive`, never wall-clock time. The
native texture remains unchanged underneath the effect. The shader parameter
uploads only when the effective rendered amount changes, including immediately
on text resets and physical-only toggles.

## Attention and timing

`Player` supplies its current camera eye and forward vector after each physics
tick. Attention requires a screen center within 4.0 m and a front face toward
the eye. The camera's forward ray must intersect the screen plane in front of
the eye, inside the screen rectangle expanded by 0.20 m on every side.
`ShipDisplay` supplies its world-space right and up half extents from its quad
size and basis, plus its front normal. The pure `DisplayPerception.attends`
function has no scene dependencies. This permits a level gaze at the console's
interaction stand: the standing eye is above the screen center, but its ray
still meets the expanded rectangle. The former 14-degree center cone rejected
that view. At 60 Hz, the first reading holds for 72 ticks (1.2 s) and ramps for
96 ticks (1.6 s). Completed first-reading memory belongs
to `Game.writing_memory` and is shared by all displays. Later readings hold
for 21 ticks (0.35 s) and ramp for 36 ticks (0.6 s).

Looking away subtracts 1/21 from perception per tick, restoring fully native
writing within 21 ticks. Returning starts another hold; if some Spanish has
not yet decayed, the ramp begins from that remaining value. A changed message
resets perception immediately to zero and starts a fresh reading. The slow
first timing stays in force until one resolution fully completes, so changing
text during the first reading restarts the full slow hold and ramp. This is
his realization that he can read the ship's writing; an early button press
must not skip it. After any completed resolution, all readings use the later
timings, including text changes and returning after looking away.

Set `power_room.console_display.physical_only = true` to force only the
rendered amount to zero. Attention and perception state continue unchanged
by the switch. Disabling it immediately presents the current model amount,
so a player who kept attending to resolved text sees Spanish at once.

## Navigation signs

`ShipText.hatch_label(deck, section)` and `deck_label(deck)` accept positive
integer identifiers. They convert quantities once to octal for native text:
`lometa [16]
shelani paki [51]` resolves to `CUBIERTA 14
SECCIÓN 41`.
The section term is the project compound recorded in the
[language reference](../design/language/nalesha-reference.md#project-additions-navigation-compounds).
Native digit runs are indivisible boxed tokens. Brackets never reach a font.
The rectangle uses the same 0.72-unit stroke as the signs, padded one native
unit beyond the digit ink edges; layout includes its half-stroke extents.
These box dimensions are renderer choices, not language rules.

Navigation uses 1024 by 512 textures with equally sized lines. Hatch quads
are 0.92 by 0.46 m, centered 1.82 m above the deck on the leaf's raised stencil
area above the wheel. Lift quads are 0.92 by 0.23 m at 1.82 m, on the door pair,
and show only the deck. There are no duplicate signs above the doors.
Anchors and sizes come from layout face/lift records. The destination section
belongs to the face's travel direction, including both section-41 bay faces.
The bay's existing ajar leaf carries its own two labels in slab-local frames.
Inaccessible boundary reverse faces retain data but have no visible surface.

Labels are children of the moving leaves. GameStep projects door snapshots
before attention, then ShipScene supplies each label's current world frame to
LabelAttention. Moving faces change spatial cells when needed; unload/reload
retains their reading state. A standing player looking level at either the
hatch center or the lift doors intersects the existing attention rectangle and
margin without camera pitch changes.

`ShipScene` requests initial navigation pairs after standing, before approaching
the hatch, and connector pairs at the existing four-meter prefetch threshold.
No navigation raster jobs run during wake. A sign surface attaches only after
its immutable pair is ready. `LabelAttention` indexes faces by deck and spatial
cell, retaining the source space for each face. Only nearby, front-facing,
ray-hit rectangles with unobstructed sight accrue perception. The same pure
segment/AABB test as interaction rejects occlusion. Previously attended faces
decay to native within 21 ticks, including after unload; their lightweight state
belongs to Game and survives scene replacement. Candidate ids are sorted.
The cache contains no perception state. All labels and the console share
`Game.writing_memory`, so a completed hatch reading establishes later timing
for the console too.

## Adding a string

Add a semantic id and both authored strings to `ShipText.MESSAGES`. Validate
native words against the language reference rather than transliterating
Spanish. Extend `tests/ship_text_test.gd` with the intended meaning pair.
Pass the heading and state ids to `ShipDisplay.set_messages`, and pass the
same `Game.writing_memory` when building another display. Tick attention once
per physics tick. Call `set_messages` only when its semantic message changes.

The guarded unit suite covers the catalog, both render layers, blank standby,
attention geometry, shared memory, exact tick timings, resets and determinism.
A real `Player` rig wired to `PowerRoom` stands at the interaction point with
level look state and advances its own physics ticks to resolve the inactive
console, then turns its yaw 90 degrees to verify decay. The capture script at
`tmp/naleya/capture_console.gd` uses the same player-driven attention path
without aiming the camera down at the screen.
The `scenarios/power-room.json` harness lane checks both full label strings at
console-inactive and power-active while retaining its gameplay and lighting
checks. Run it as described in [harness.md](harness.md). Harness console events
record `native_label` and `perceived_label` regardless of current perception.
