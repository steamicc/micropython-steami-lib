# Spleen fonts on the V1c screen (MicroPython) — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** On the 240 px V1c screen, draw every `steami_screen` text and the pixel text in the Spleen faces, with Arduino's cells and positions. The 128 px panel keeps 8x8, with accents folded and a real degree sign.

**Architecture:**
- `spleen.py` (generated, frozen) holds the tables.
- A new `steami_screen/fonts.py` holds the pure helpers: code mapping, face ladder, widths, ink masks and the run drawer.
- `GC9A01Display.draw_glyphs()` blits native faces through a 2x1 palette with a key, and fills runs for replicated faces. It resolves the colour once.
- `Screen` (device.py) fits and draws by ink (TEXT, LABEL, VALUE) when k > 1. When k = 1 it only folds accents and draws '°'.
- A fork PR moves the firmware file system 16 KB up, to make room in flash.

**Tech Stack:** MicroPython 1.29 `framebuf` (GS4_HMSB frame, MONO_HLSB glyphs, `blit` with palette and key), CPython 3.10+ mock tests with pytest 9.2.0, ruff 0.17.6, GNU ld for the STM32WB55 firmware fork.

**Spec:** `docs/superpowers/specs/2026-11-27-steami-screen-spleen-design.md` (this repo). The shared rules are in sections 5.1-5.5 and 8.1 of the Arduino design `/tmp/claude-1000/-home-nedjar-sandbox-wiki-steami/1346e80f-1de2-4e4c-bae2-38b41b348575/scratchpad/wt-4b-font/docs/superpowers/specs/2026-11-26-steami-display-v1c-font-design.md`.

**References (read only):**
- `A=/tmp/claude-1000/-home-nedjar-sandbox-wiki-steami/1346e80f-1de2-4e4c-bae2-38b41b348575/scratchpad/wt-4b-font` (4b-font, HEAD `3527b5e`): `tests/native/test_steami_screen/test_main.cpp` and `golden_layout.py` hold the 240 px goldens.
- Code maps: `/tmp/claude-1000/-home-nedjar-sandbox-wiki-steami/fd048878-c715-498a-8954-e4ba541f26c4/scratchpad/spleen-map-{device,adapters,tests,firmware,arduino}.md`.

## Global Constraints

**Repo and tooling**
- Repo `micropython-steami-lib`, worktree `/tmp/claude-1000/-home-nedjar-sandbox-wiki-steami/fd048878-c715-498a-8954-e4ba541f26c4/scratchpad/wt-spleen`. Branch `feat/steami-screen-spleen` from v0.30.2 (`6defa45`). Issue #461. All commands run from the worktree root unless a task says otherwise.
- Tools: a `.venv` made in Task 0 (the system `python3` has pytest 9.0.2 and no ruff module, so `make lint` fails without it). `.venv/bin/python -m pytest --version` must say 9.2.0 and `.venv/bin/python -m ruff --version` 0.17.6 (the versions pinned in `pyproject.toml`, the same as the uv tool). `make` picks up `.venv/bin/python` by itself; every direct pytest call in this plan is `.venv/bin/python -m pytest`. `make test-mock` and `make lint` pass after every task. `.venv/` is git-ignored.
- New test files end in `_mock.py`. Tests target Python 3.10.

**Lint rules that bite (ruff 0.17.6, repo config)**
- At most 10 parameters besides `self` (PLR0913 and PLR0917, also in tests).
- In `.py` comments, docstrings and strings write ASCII `x`, `*` and `-`: `×` and `−` trip RUF001-RUF003, and so does `µ` (write `us`). `°`, the accented letters, `Ÿ`, `€` and `·` pass.
- No uppercase local variables (N806, also in tests): use `sp.F8X16` or a module-level alias, never `F8X16 = sp.F8X16` inside a function.
- Fixtures and helpers shared from `tests/test_steami_screen_scaling_mock.py` (`mods`, `panel`, `lit`, `box`, `count`, `outside`, `RecordingDisplay`, the palette indexes) are imported the way `tests/test_steami_screen_class_mock.py` imports `board_module`: `from tests.test_steami_screen_scaling_mock import (...)  # noqa: F401 (mods and panel are fixtures)`, and each test that takes an imported fixture as a parameter carries `# noqa: F811`. Never import a `test_*` name.

**MicroPython-safe Python** (`fonts.py`, `device.py`, `gc9a01.py` run on the board, the mock tests only under CPython)
- No `int.bit_length()`, `str.isascii()`, `str.translate`/`str.maketrans`: use shift loops (as `_band` does today), `for ch in s: if ch not in VALUE_KEY`, and `EXTRA.find(ch)`.
- MicroPython `str` indexing is O(i) on UTF-8: iterate with `for ch in s` and a counter, never `s[i]` in a loop.

**Commits**
- Format `<type>(<scope>): <Description.>`, at most 78 characters, ending with a period.
- Scopes come from `commitlint.config.js`: `steami_screen`, `gc9a01`, `tests`, `docs`.
- No attribution lines, never "[skip ci]".
- Every commit step stages its own files by name (`git add <paths>`), never `git add -A` or `git add .`.

**spleen.py**
- Copy it byte for byte from `/tmp/claude-1000/-home-nedjar-sandbox-wiki-steami/1346e80f-1de2-4e4c-bae2-38b41b348575/scratchpad/spleen-mp/spleen.py`:
  - sha256 `c550418ca14a68ca0cb18bdbce2e3eeafb544830d77ce41c601df8a00303ae30`, 33 479 B, 718 lines;
  - destination `lib/steami_screen/steami_screen/spleen.py`.
- Never hand-edit it, never run `ruff format` on it.
- Facts: `VERSION = "2.1.0"`, `VALUE_KEY = " +-.:0123456789"`.
- `EXTRA = "°ÀÂÄÇÈÉÊËÎÏÔÖÙÛÜàâäçèéêëîïôöùûüÿŸ"` (codes 127..159). `FOLD = "°AAACEEEEIIOOUUUaaaceeeeiioouuuyY"`.
- Faces `(w, h, ascent, key, data)`:

  | Face | w, h, ascent, key | len(data) |
  |---|---|---|
  | `F6X12` | 6, 12, 9, None | 1536 |
  | `F8X16` | 8, 16, 12, None | 2048 |
  | `F12X24` | 12, 24, 19, VALUE_KEY | 720 |
  | `F16X32` | 16, 32, 26, VALUE_KEY | 960 |

- Glyph bytes: `bpr = (w + 7) // 8`. Full set: offset `(code - 32) * h * bpr`. Value set: offset `VALUE_KEY.find(ch) * h * bpr`. Rows run top to bottom, MSB = column 0.

**Code of a character**
- `o = ord(ch)`: if `32 <= o <= 126`, the code is `o`.
- Else `i = EXTRA.find(ch)`: if `i >= 0`, the code is `127 + i`.
- Else the code is 63 (`'?'`).
- The 6x12 slot 159 holds Y.

**240 px (k = 2)**

Faces:
- TEXT at f: `F8X16`, n = f/2 (no face when f is odd).
- LABEL: `F6X12`, n = 1, whatever f; advance 6, cell height 12.
- VALUE, text made only of `VALUE_KEY` characters, judged on the whole text:
  - f % 4 == 0: `F16X32`, n = f/4;
  - else f % 3 == 0: `F12X24`, n = f/3;
  - else f even: `F8X16`, n = f/2;
  - else no face.
- VALUE with any other character: the TEXT ladder.
- Bold: only VALUE on `F12X24`/`F16X32`, a strike at x and x + n.
- Narrow: VALUE `'.'`/`':'` on every face. The glyph is drawn at pen x − (w//4)·n, and the advance is half.

Metrics:
- TEXT/VALUE advance = 4f. Cell height = 8f.
- `max_chars` = `width // (8 if k == 1 else 4 * k)`: 16 / 30.
- `text_height(scale=1)` = `(8 if k == 1 else 16) * max(scale, 1)`.

Rows and margins:
- Title cap half-width = 13 × 8 // 2 = 52, so the cap margin is 14. Floor = `(16f + 4k)·W // (128k)`: f 2 → 37, f 3 → 52, f 4 → 67. Every title sits at row 37.
- Value label: cell top = value top − u(4) − 12 = value top − 19. Its lowering loop stops at value top − 12.
- Graph labels: max label first ink row = `gy + u(2)` = 74; others: last ink row = `yp − k − u(2)`.
- Compass and watch letters: cell at `(x − tw//2, y − text_height()//2)`.
- Menu: row test stays `STEAMI_MENU_ROW_CELLS * 8 * k` = 192 px (5 rows, kept difference).

u() values on 240: u(2)=3, u(3)=5, u(4)=7, u(5)=9, u(8)=15, u(15)=28, u(31)=58.

**Native blit**
- Source tuple `(memoryview(data)[o:o + h*bpr], w, h, framebuf.MONO_HLSB)`.
- Palette: a `bytearray(1)` holding `(b << 4) | c`, wrapped as a 2x1 `GS4_HMSB` FrameBuffer. `c = rgb_to_index(color)`, `b = 1 if c == 0 else 0`, key `b`.
- All arguments positional.
- Replicated faces: one `fill_rect` per run. With bold, the width is `(b − a + 2)·n` instead of `(b − a + 1)·n`.

**128 px (k = 1)**
- 8x8 framebuf text stays.
- Only the characters of `EXTRA` change (the ruling): the 32 accented letters fold through `FOLD8 = "\x7f" + spleen.FOLD[1:]` to one ASCII byte, and '°' is drawn with `DEGREE8 = b"\x30\x48\x48\x30\x00\x00\x00\x00"` (MONO_HLSB rows of Arduino `SteamiFont.cpp` glyph 127), 6 `fill_rect` runs at scale 1.
- Every other character is left as it is, so `framebuf.text` draws it as in v0.30: a control character, a literal `"\x7f"` or a non-ASCII character outside `EXTRA` (`"€"`, `"ñ"`, emoji) stays one checkerboard per UTF-8 byte. The degree is found by splitting the text at '°' before folding, so a literal `"\x7f"` is never taken for a degree.
- The 128 path never imports `steami_screen.spleen` and never touches `GS4_HMSB` or `blit`.
- Every existing 128 golden entry stays byte-identical.

**Firmware**

Separate repo `steamicc/micropython-steami`.
- New `ports/stm32/boards/STEAM32_WB55RG/stm32wb55xg_steami.ld`:

  | Region | Origin | Length |
  |---|---|---|
  | FLASH | 0x08000000 | 528K |
  | FLASH_APP | 0x08008000 | 496K |
  | FLASH_FS | 0x08084000 | 256K (ends 0x080C4000) |

  Plus `ASSERT`s:
  - FLASH end == FS origin;
  - FLASH_APP end == FS origin;
  - FS end ≤ 0x080E0000 (BLE_HCILayer v1.20.0).
- Other edits:
  - `LD_FILES` in `mpconfigboard.mk` names it for the plain and the mboot builds;
  - `rfcore_firmware.py` `STAGING_AREA_START = 0x80C4000`.
- Never pushed without the maintainer's approval.
- The fork PR merges before the lib PR.

**Hardware**
- V1c steps are controller steps: the board is shared and needs a slot booking.

## Review Focus

1. **BLACK text, or text over a coloured background** (the selected menu bar, a gauge ring, `clear(RED)`): only the glyph's set bits change. BLACK text is visible and nothing around a glyph is painted. Tested in Task 5 (`test_draw_glyphs_keeps_the_background`).
2. **Characters outside the font** (`"€"`, `"ñ"`, `"\n"`, `"\x7f"`, emoji): one `'?'` cell on 240, one cell counted, no exception. On 128 they are not touched (only `EXTRA` folds): framebuf keeps drawing them as in v0.30 (one checkerboard per UTF-8 byte), and a literal `"\x7f"` is never drawn as a degree. Tested in Task 4 (`test_mock_code_of_a_character`, `test_mock_fold8`), Task 6 (`test_mock_pixel_text_unknown_character_is_a_question_mark`) and Task 9 (`test_mock_128_leaves_other_characters_to_framebuf`).
3. **Pixel text partly or fully off the panel** (negative x or y, x ≥ 240, scale 3): clipped to the frame, no exception, native and replicated faces alike. Tested in Task 6 (`test_mock_pixel_text_clips_at_the_panel_edges`).
4. **Empty and blank strings** (`title("")`, `subtitle("", "x")`, `menu([""])`, `value("")`, `text("   ", at="N")`): nothing raises, nothing is drawn outside the circle. Tested in Task 7 (`test_mock_empty_texts_raise_nothing`) and Task 8 (`test_mock_value_of_empty_text_raises_nothing`).
5. **`str(val)` forms that are not plain numbers** (`nan`, `1e-05`, `-0.5`): the face is judged on the whole text. "nan" and "1e-05" take the TEXT ladder (never bold) and "-0.5" takes the value set. Tested in Task 8 (`test_mock_value_face_follows_the_whole_text`).

---

### Task 0: Tooling and the design documents

**Files:**
- Commit: `docs/superpowers/plans/2026-11-27-steami-screen-spleen.md`, `docs/superpowers/specs/2026-11-27-steami-screen-spleen-design.md` (untracked today; PRs #447 and #454 committed their plan and spec the same way)

- [ ] **Step 1: Make the venv.** `python3 -m venv .venv && .venv/bin/pip install -e ".[dev,test]"` (`make install` also needs npm, so call pip directly).
- [ ] **Step 2: Check the versions.** `.venv/bin/python -m pytest --version` → `pytest 9.2.0`; `.venv/bin/python -m ruff --version` → `ruff 0.17.6`. `make lint` → "All checks passed!"; `make test-mock` → no failure (the v0.30.2 baseline). `git status --short` lists only the two documents (`.venv/` is ignored).
- [ ] **Step 3: Commit the documents.** `git add docs/superpowers/plans/2026-11-27-steami-screen-spleen.md docs/superpowers/specs/2026-11-27-steami-screen-spleen-design.md && git commit -m "docs(steami_screen): Add the Spleen fonts design and plan."`. If the plan changes later (ticked boxes, controller notes), commit it the same way before Task 14.

### Task 1: Commit the generated `spleen.py`

**Files:**
- Create: `lib/steami_screen/steami_screen/spleen.py` (copy)
- Create: `tests/test_steami_screen_spleen_mock.py`

**Interfaces:**
- Produces: the module `steami_screen.spleen` (contract above); in the test file, the fixture `sp` (the imported `steami_screen.spleen`, loaded through `load_driver_mock("steami_screen", None)` and cleaned up with `cleanup_driver("steami_screen")`).

- [ ] **Step 1: Write the failing tests** in `tests/test_steami_screen_spleen_mock.py`:
  - `test_mock_spleen_is_the_generated_file`: the sha256 of `lib/steami_screen/steami_screen/spleen.py` equals the value in Global Constraints. Its first line is `# SPDX-License-Identifier: BSD-2-Clause`.
  - `test_mock_spleen_contract(sp)`:
    - `sp.VERSION == "2.1.0"`;
    - `sp.VALUE_KEY == " +-.:0123456789"`;
    - `len(sp.EXTRA) == len(sp.FOLD) == 33`;
    - `sp.FOLD[0] == "°"`, `sp.FOLD[32] == "Y"`;
    - `sp.F6X12[:4] == (6, 12, 9, None)`, `sp.F8X16[:4] == (8, 16, 12, None)`, `sp.F12X24[:4] == (12, 24, 19, sp.VALUE_KEY)`, `sp.F16X32[:4] == (16, 32, 26, sp.VALUE_KEY)`;
    - `[len(f[4]) for f in (sp.F6X12, sp.F8X16, sp.F12X24, sp.F16X32)] == [1536, 2048, 720, 960]`;
    - each `data` is `bytes`.
- [ ] **Step 2: Run.** `.venv/bin/python -m pytest tests/test_steami_screen_spleen_mock.py -q` → FAIL (`ModuleNotFoundError: steami_screen.spleen`).
- [ ] **Step 3: Copy the file.** `cp /tmp/claude-1000/-home-nedjar-sandbox-wiki-steami/1346e80f-1de2-4e4c-bae2-38b41b348575/scratchpad/spleen-mp/spleen.py lib/steami_screen/steami_screen/spleen.py`, then `sha256sum` it and compare with the Global Constraints value. Nothing else changes: `manifest.py`'s `package("steami_screen")` already freezes it.
- [ ] **Step 4: Run.** `.venv/bin/python -m pytest tests/test_steami_screen_spleen_mock.py tests/test_examples.py -q` → PASS. `make lint` → "All checks passed!". `make test-mock` → no failure.
- [ ] **Step 5: Commit.** `git add lib/steami_screen/steami_screen/spleen.py tests/test_steami_screen_spleen_mock.py && git commit -m "feat(steami_screen): Add the generated Spleen 2.1.0 font module."`

### Task 2: The framebuf stub refuses read-only buffers, like MicroPython

**Files:**
- Modify: `tests/fake_machine/framebuf_stub.py` (constructor L22-48, every public method signature, `_as_framebuffer` L220-226)
- Test: `tests/test_framebuf_stub_mock.py`

**Interfaces:**
- Produces:
  - `FrameBuffer(buffer, width, height, fmt, stride=None, /)` raises `TypeError("object with buffer protocol required")` for a read-only buffer (`bytes`, `memoryview(bytes)`);
  - every public method is positional-only (`fill`, `fill_rect`, `pixel`, `hline`, `vline`, `rect`, `line`, `blit(fbuf, x, y, key=-1, palette=None, /)`, `scroll`, `text`);
  - the module helper `_make(fb, buffer, width, height, fmt, stride, writable)` holds the constructor body;
  - `_as_framebuffer(obj)` builds read-only sources and palettes with `writable=False` (through `FrameBuffer.__new__(FrameBuffer)`).

- [ ] **Step 1: Write the failing tests:**
  - `test_constructor_rejects_a_read_only_buffer`: `FrameBuffer(bytes(8), 8, 8, MONO_HLSB)` and `FrameBuffer(memoryview(bytes(8)), 8, 8, MONO_HLSB)` raise `TypeError`.
  - `test_constructor_accepts_writable_buffers`: `bytearray(8)`, `memoryview(bytearray(8))` and `array.array("B", bytes(8))` are accepted.
  - `test_signatures_are_positional_only`: each of these raises `TypeError`:
    - `FrameBuffer(bytearray(8), 8, 8, MONO_HLSB, stride=8)`;
    - `dst.blit(src, 0, 0, key=0)`;
    - `dst.blit(src, 0, 0, 0, palette=pal)`;
    - `dst.rect(0, 0, 2, 2, 1, fill=True)`.
  - `test_blit_draws_a_read_only_glyph_through_a_palette_and_key`:
    - setup: a GS4 4x1 frame filled with 3, and `src = (memoryview(bytes([0b10100000]))[0:1], 3, 1, MONO_HLSB)`;
    - a palette FrameBuffer over `bytearray([(1 << 4) | 0])` with key 1 gives `[0, 3, 0, 3]` (BLACK text drawn);
    - palette byte `(0 << 4) | 5` with key 0 gives `[5, 3, 5, 3]`;
    - the same with the palette given as the tuple `(bytes([0x05]), 2, 1, GS4_HMSB)`.
- [ ] **Step 2: Run.** `.venv/bin/python -m pytest tests/test_framebuf_stub_mock.py -q` → `test_constructor_rejects_a_read_only_buffer` and `test_signatures_are_positional_only` FAIL. The other two already pass with the current stub (`FrameBuffer(*obj)` has no read-only check, palette blits work): they are regression guards for Step 3.
- [ ] **Step 3: Implement.** Follow the C order for the read-only test (modframebuf.c L280-323): format branch, then `if memoryview(buffer).readonly: raise TypeError(...)` when `writable`, then the size check. A non-buffer object makes `memoryview()` raise `TypeError` too. Also update the module docstring.
- [ ] **Step 4: Run.** `.venv/bin/python -m pytest tests/test_framebuf_stub_mock.py -q` → PASS (including `test_blit_accepts_a_tuple_source`). `make test-mock` → no failure. If any library code calls a stub method with a keyword, it would fail on the board too: report it, do not loosen the stub.
- [ ] **Step 5: Commit.** `git add tests/fake_machine/framebuf_stub.py tests/test_framebuf_stub_mock.py`, message `test(tests): Make the framebuf stub refuse read-only buffers.`

### Task 3: The gc9a01 driver's `blit` passes a palette

**Files:**
- Modify: `lib/gc9a01/gc9a01/device.py:175-176`
- Test: `tests/test_gc9a01_mock.py` (next to `test_blit_with_key`, L410)

**Interfaces:**
- Produces: `GC9A01.blit(self, fb, x, y, key=-1, palette=None)`. It forwards `self.framebuf.blit(fb, x, y, key, palette)`, positionally. `fb` may be a FrameBuffer or a read-only `(buf, w, h, fmt[, stride])` tuple.

- [ ] **Step 1: Write the failing test** `test_blit_with_palette_maps_then_keys(rig)`. Setup: `rig.dev.fill(2)` and `glyph = (memoryview(bytes([0b10100000]))[0:1], 3, 1, framebuf.MONO_HLSB)`.
  - A palette over `bytearray([(0 << 4) | 9])` with key 0, blitted at (50, 60), gives `[9, 2, 9]` on x 50..52.
  - A palette over `bytearray([(1 << 4) | 0])` with key 1, blitted at (50, 61), gives `[0, 2, 0]`.
- [ ] **Step 2: Run.** `.venv/bin/python -m pytest tests/test_gc9a01_mock.py -q -k blit_with_palette` → FAIL (`TypeError`: too many positional arguments).
- [ ] **Step 3: Implement** the signature above, with a docstring that says "palette is applied before the key test". `text()` stays 8x8.
- [ ] **Step 4: Run.** `.venv/bin/python -m pytest tests/test_gc9a01_mock.py -q` → PASS. `make test-mock` → no failure.
- [ ] **Step 5: Commit.** `git add lib/gc9a01/gc9a01/device.py tests/test_gc9a01_mock.py`, message `feat(gc9a01): Pass a palette through blit().`

### Task 4: `steami_screen/fonts.py`, the font helpers

**Files:**
- Create: `lib/steami_screen/steami_screen/fonts.py`
- Test: `tests/test_steami_screen_spleen_mock.py`

**Interfaces:**
- Consumes: `steami_screen.spleen` (imported inside `face()` only).
- Produces:
  - `TEXT = 0`, `LABEL = 1`, `VALUE = 2`.
  - `EXTRA: str`, a copy of `spleen.EXTRA`.
  - `FOLD8: str = "\x7f" + spleen.FOLD[1:]`, as a literal.
  - `DEGREE8 = (8, 8, 0, None, b"\x30\x48\x48\x30\x00\x00\x00\x00")`, a face tuple.
  - `code(ch: str) -> int`.
  - `fold8(s: str) -> str`: a character of `EXTRA` at index i becomes `FOLD8[i]`; every other character (ASCII, control characters, `"\x7f"`, non-ASCII outside `EXTRA`) is unchanged. The loop uses `EXTRA.find(ch)` only for `ord(ch) > 126`.
  - `face(s: str, ink: int, f: int) -> tuple | None`. It returns `(fc, n)`, where `fc` is a spleen face tuple and n the replication, by the ladder of Global Constraints. LABEL ignores f. `""` counts as value text. The spleen module is imported on the first call and kept in a module global `_sp`, so later calls do no import.
  - `offset(fc: tuple, ch: str) -> int`: the byte offset in `fc[4]`. It is never called with a character outside a value set's key.
  - `advance(ink: int, f: int) -> int`: 6 for LABEL, else 4f (240 metrics).
  - `widths(s: str, ink: int, f: int) -> list`: the prefix widths in one pass (a running sum), `len == len(s)`. For VALUE, `'.'`/`':'` count `advance // 2`.
  - `width(s: str, n: int, ink: int, f: int) -> int`: the width of the first n characters (0 for n = 0), iterating `for ch in s` with a counter.
  - `masks(fc: tuple, s: str) -> list`: the prefix ink masks. Bit r is set when row r of a glyph has a non-zero byte. `len == len(s)`. Each glyph's row mask is cached in a module dict keyed by the small int `(fc[1] << 16) | offset` (the height tells the four faces apart), so a glyph's rows are scanned once per boot.
  - `ink_rows(m: int) -> tuple`: `(lowest set bit, highest set bit)` of `m != 0`.
  - `draw_runs(fr, fc: tuple, glyphs, n: int, bold: int, c) -> None`:
    - `fr(x, y, w, h, c)` is a fill_rect callable;
    - `glyphs` is an iterable of `(offset, x, y)`;
    - it makes one `fr` call per run of set bits.

- [ ] **Step 1: Write the failing tests** (`sp` is the spleen fixture, `fonts` the imported module):
  - `test_mock_fold_copy_matches_spleen`:
    - `fonts.EXTRA == sp.EXTRA`;
    - `fonts.FOLD8[1:] == sp.FOLD[1:]`;
    - `fonts.FOLD8[0] == "\x7f"`;
    - every `ord(ch) < 128`.
  - `test_mock_code_of_a_character`:

    | ch | code |
    |---|---|
    | `" "` | 32 |
    | `"~"` | 126 |
    | `"°"` | 127 |
    | `"À"` | 128 |
    | `"é"` | 148 |
    | `"Ÿ"` | 159 |
    | `"€"`, `"ñ"`, `"\n"`, `"\x7f"` | 63 each |

  - `test_mock_fold8`:
    - `fold8("Été 23°C") == "Ete 23\x7fC"`;
    - `fold8("Ÿ€ñ") == "Y€ñ"` (outside `EXTRA`: left to framebuf, as in v0.30);
    - `fold8("a\tb\x7f\n") == "a\tb\x7f\n"`.
  - `test_mock_face_ladder`:
    - `[face("23.5", VALUE, f) for f in 1..12]`, by identity and n: `None, (F8X16,1), (F12X24,1), (F16X32,1), None, (F12X24,2), None, (F16X32,2), (F12X24,3), (F8X16,5), None, (F16X32,3)`;
    - `"12:30 PM"`: f 2 → `(F8X16,1)`, f 3 → `None`, f 4 → `(F8X16,2)`;
    - `face("", VALUE, 4) == (F16X32, 1)`;
    - `face("Été", VALUE, 4) == (F8X16, 2)`;
    - `face("TEMP", LABEL, 2)` and `face("TEMP", LABEL, 4)` → `(F6X12, 1)`;
    - TEXT: f 2 → `(F8X16, 1)`, f 6 → `(F8X16, 3)`, f 3 → `None`.
  - `test_mock_glyph_offsets`:
    - `offset(F8X16, "A") == 528`;
    - `offset(F8X16, "é") == 1856`;
    - `offset(F16X32, ".") == 192`;
    - `offset(F12X24, "9") == 672`;
    - the 6x12 slot 159 holds Y: `sp.F6X12[4][o:o + 12] == sp.F6X12[4][p:p + 12]` with `o = offset(sp.F6X12, "Ÿ")`, `p = offset(sp.F6X12, "Y")`.
  - `test_mock_widths`:
    - `width("12:30 PM", 8, VALUE, 2) == 60`;
    - `width("23.5", 4, VALUE, 4) == 56`;
    - `width("23.5", 4, VALUE, 2) == 28`;
    - `width("TEMP", 4, LABEL, 2) == 24`;
    - `width("Hi", 2, TEXT, 2) == 16`;
    - `width("a.b", 3, TEXT, 2) == 24`;
    - `width("1.5", 2, VALUE, 4) == 24`;
    - `width("1.5", 0, VALUE, 4) == 0`;
    - `widths("1.5", VALUE, 4) == [16, 24, 40]`, `widths("", TEXT, 2) == []`;
    - `advance(VALUE, 4) == 16`.
  - `test_mock_masks_and_ink_rows`:
    - `masks(F6X12, "TEMP")[-1] == 0x1FE`;
    - `masks(F8X16, "Hg")[-1] == 0x7FFC`;
    - `ink_rows(masks(F16X32, "8")[-1]) == (6, 25)`;
    - `ink_rows(masks(F12X24, "8")[-1]) == (4, 18)`;
    - `masks(F8X16, "É")[-1] & 1 == 1`;
    - `masks(F8X16, " ") == [0]`;
    - `masks(F8X16, "") == []`;
    - calling `masks(F16X32, "8")` twice gives the same list (the cache returns what the scan gave).
  - `test_mock_draw_runs_one_call_per_run`, with `rec` a list-appending `fr` and the glyph at `(0, 10, 20)`:
    - face `(8, 1, 0, None, b"\xb0")`, n 2: `[(10, 20, 2, 2, c), (14, 20, 4, 2, c)]`;
    - the same with bold 1: `[(10, 20, 4, 2, c), (14, 20, 6, 2, c)]`;
    - face `(16, 1, 0, None, b"\x80\x01")`, n 1: `[(10, 20, 1, 1, c), (25, 20, 1, 1, c)]`;
    - `b"\x00"`: `[]`;
    - `DEGREE8`, n 1: `[(12, 20, 2, 1, c), (11, 21, 1, 1, c), (14, 21, 1, 1, c), (11, 22, 1, 1, c), (14, 22, 1, 1, c), (12, 23, 2, 1, c)]`.
  - `test_mock_fonts_loads_spleen_only_for_a_face` (without the `sp` fixture, on a fresh `load_driver_mock`): after `import steami_screen.fonts` and calls to `code`, `fold8`, `width`, `advance`, `draw_runs(DEGREE8…)`, `"steami_screen.spleen" not in sys.modules`. After `face("A", TEXT, 2)` it is in.
- [ ] **Step 2: Run.** `.venv/bin/python -m pytest tests/test_steami_screen_spleen_mock.py -q` → the new tests FAIL (`ModuleNotFoundError: steami_screen.fonts`).
- [ ] **Step 3: Implement `fonts.py`.** Masks stay below 2**26 (value sets ink rows ≤ 25, 8x16 ≤ 15), so they remain MicroPython small ints. Follow "MicroPython-safe Python" of Global Constraints: `ink_rows` uses shift loops (as `_band` does today), the value-set test is `for ch in s: if ch not in VALUE_KEY`, the fold uses `EXTRA.find`. `draw_runs` keeps per-row work minimal; its loop is not fixed by the tests, so use this one:

```python
w, h, data = fc[0], fc[1], fc[4]
bpr = (w + 7) // 8
top = 1 << (8 * bpr - 1)
for o, gx, gy in glyphs:
    for r in range(h):
        i = o + r * bpr
        v = data[i] if bpr == 1 else (data[i] << 8) | data[i + 1]
        col, bit = 0, top
        while v:                      # stops as soon as no set bit is left
            if v & bit:
                a = col
                while v & bit:
                    v &= ~bit
                    bit >>= 1
                    col += 1
                fr(gx + a * n, gy + r * n, (col - a + bold) * n, n, c)
            else:
                bit >>= 1
                col += 1
```

- [ ] **Step 4: Run.** `.venv/bin/python -m pytest tests/test_steami_screen_spleen_mock.py tests/test_examples.py -q` → PASS. `make lint` and `make test-mock` → clean. MicroPython smoke check: `/tmp/claude-1000/-home-nedjar-sandbox-wiki-steami/fd048878-c715-498a-8954-e4ba541f26c4/scratchpad/fw-rebase/mpy-cross/build/mpy-cross -O3 -o /tmp/claude-1000/-home-nedjar-sandbox-wiki-steami/fd048878-c715-498a-8954-e4ba541f26c4/scratchpad/fonts.mpy lib/steami_screen/steami_screen/fonts.py` succeeds, and `grep -nE 'bit_length|isascii|translate\(|maketrans' lib/steami_screen/steami_screen/fonts.py` prints nothing. Repeat both for `device.py` and `gc9a01.py` at the end of Tasks 5-9.
- [ ] **Step 5: Commit.** `git add lib/steami_screen/steami_screen/fonts.py tests/test_steami_screen_spleen_mock.py`, message `feat(steami_screen): Add the font helpers for the Spleen faces.`

### Task 5: `GC9A01Display.draw_glyphs()`

**Files:**
- Modify: `lib/steami_screen/steami_screen/gc9a01.py` (`__init__` L74-82, new method)
- Test: `tests/test_steami_screen_gc9a01_mock.py` (`RecordingRaw` L52-79, new tests)

**Interfaces:**
- Consumes: `fonts.draw_runs` (Task 4); `raw.blit(fb, x, y, key, palette)` (Task 3).
- Produces: `GC9A01Display.draw_glyphs(self, fc, glyphs, n, bold, color) -> None`.
  - `c = rgb_to_index(color)` is computed once per call.
  - n ≥ 2: `fonts.draw_runs(self._fill_rect_raw, fc, glyphs, n, bold, c)`.
  - n == 1: one blit per entry, plus one at x + 1 when bold, with key `b`.
  - On first use (lazy), it creates `self._pal_buf = bytearray(1)` and `self._pal` (2x1 `GS4_HMSB` FrameBuffer).
  - The blit is looked up once per call into a local (`raw.blit` if present, else `raw.framebuf.blit`), never cached on `self`: one attribute lookup per string, and a test that wraps `raw.blit` sees every call. `raw.blit` is kept (not `raw.framebuf.blit`) because it is the driver method that carries the palette (Task 3).
  - `__init__` sets `self._pal = None` and touches neither `framebuf` nor `raw.blit`.
  - `draw_scaled_text` stays (public, 8x8, no longer used by `Screen` on 240).

- [ ] **Step 1: Write the failing tests.** First give `RecordingRaw` a `blit(self, fb, x, y, key=-1, palette=None)`. It records `("blit", bytes(fb[0]), fb[1], fb[2], fb[3], x, y, key, (palette.pixel(0, 0), palette.pixel(1, 0)))`.
  - `test_draw_glyphs_blits_native_faces_with_one_colour_lookup(recorded, adapter_mod, monkeypatch)`:
    - wrap `adapter_mod.rgb_to_index` to count calls;
    - `display.draw_glyphs(F8X16, [(528, 10, 20), (1168, 18, 20)], 1, 0, (255, 255, 255))` gives `raw.calls == [("blit", data[528:544], 8, 16, 3, 10, 20, 0, (0, 5)), ("blit", data[1168:1184], 8, 16, 3, 18, 20, 0, (0, 5))]`, with 1 lookup. Offset 1168 is "i".
  - `test_draw_glyphs_bold_is_a_second_blit_one_pixel_right`: `F16X32`, `[(offset of "8", 50, 60)]`, n 1, bold 1 → two blits at x 50 and 51.
  - `test_draw_glyphs_black_uses_key_1`: colour `(0, 0, 0)` → key 1, palette `(1, 0)`.
  - `test_draw_glyphs_fills_runs_for_replicated_faces`: `F8X16`, `[(528 + 7*16, 10, 20)]` ('H'), n 2 →
    - only `fill_rect` calls, 19 of them, every height 2, colour 5;
    - the first two are `("fill_rect", 10, 24, 4, 2, 5)` and `("fill_rect", 20, 24, 4, 2, 5)`, and the row-6 bar is `("fill_rect", 10, 32, 14, 2, 5)`;
    - with bold 1, the first two become widths 6.
  - `test_draw_glyphs_keeps_the_background(real)` (Review Focus 1), using 'A' (44 set pixels):
    - frame filled DARK (index 2), 'A' native at (10, 20) in WHITE: the cell's set bits read 5 and the other 84 cell pixels read 2;
    - frame filled WHITE, the same 'A' in BLACK: set bits read 0, others 5;
    - the same in BLACK at n 2: set bits read 0 in 2x2 blocks.
  - `test_size_defaults_to_240` and `test_every_method_forwards_to_the_raw_driver` stay unchanged (no eager `blit` or `framebuf` access).
- [ ] **Step 2: Run.** `.venv/bin/python -m pytest tests/test_steami_screen_gc9a01_mock.py -q` → the new tests FAIL (`AttributeError: draw_glyphs`).
- [ ] **Step 3: Implement.** Bind `blit`, `self._pal`, `MONO_HLSB` and `memoryview(fc[4])` to locals once per call. Each blit is `blit((mv[o:o + size], w, h, mono), x, y, b, pal)`, positional.
- [ ] **Step 4: Run.** `.venv/bin/python -m pytest tests/test_steami_screen_gc9a01_mock.py -q` → PASS. `make test-mock` → no failure. `test_adapter_does_not_import_the_driver` still passes.
- [ ] **Step 5: Commit.** `git add lib/steami_screen/steami_screen/gc9a01.py tests/test_steami_screen_gc9a01_mock.py`, message `feat(steami_screen): Draw Spleen glyphs on the GC9A01 adapter.`

### Task 6: Pixel text in Spleen 8x16, `text_height()`, `max_chars`

**Files:**
- Modify: `lib/steami_screen/steami_screen/device.py`:
  - L78-80 `max_chars`;
  - `text()` L667-669;
  - new `text_height`, `_tw`, `_draw`;
  - `from steami_screen import fonts` and `from steami_screen.fonts import TEXT, VALUE` at the top (`LABEL` is added in Task 7, its first use; importing it now fails F401).
- Test: `tests/test_steami_screen_spleen_mock.py`, `tests/test_steami_screen_scaling_mock.py` (L99, `RecordingDisplay` L216-243, `test_mock_widget_text_is_scaled_by_k` L284-296)

**Interfaces:**
- Consumes: `fonts.face`, `fonts.offset`, `fonts.advance`, `fonts.draw_runs` (Task 4); `display.draw_glyphs` (Task 5).
- Produces:
  - `Screen.text_height(self, scale=1) -> int` (Global Constraints).
  - `Screen.max_chars` → 16 / 30.
  - `Screen._tw(self, s, ink, f) -> int`: `len(s) * 8 * f` when k == 1, else `fonts.width(s, len(s), ink, f)`.
  - `Screen._draw(self, s, x, y, color, ink, f, fn=None) -> None`. Used when k > 1 only. `fn` is the `face()` pair judged by the caller on the whole text (Task 7's `_place` passes the one `_fit` judged, so a cut prefix keeps the face of the whole text). When `fn is None` it is computed here as `fonts.face(s, ink, f)`; if there is still no face, nothing is drawn (`if not fn: return`). It builds the entries and calls `self._d.draw_glyphs(fc, entries, n, bold, color)`, or, when the display has no `draw_glyphs`, `fonts.draw_runs(self._fill_rect, fc, entries, n, bold, color)`. The entries are built like this (the narrow offset is not fixed by a formula elsewhere):

```python
fc, n = fn
adv = fonts.advance(ink, f)
bold = 1 if ink == VALUE and fc[0] >= 12 else 0
entries = []
for ch in s:
    narrow = ink == VALUE and ch in ".:"
    entries.append((fonts.offset(fc, ch), x - (fc[0] // 4) * n if narrow else x, y))
    x += adv // 2 if narrow else adv
```

  - `text(s, (x, y), color, scale)`: when k > 1, `self._draw(text, x, y, color, TEXT, max(scale, 1) * k)`. When k == 1, unchanged.

- [ ] **Step 1: Write the failing tests.** The spleen file imports the shared fixtures and helpers of the scaling file (Global Constraints, "Lint rules that bite") and uses the faces as `sp.F8X16` etc. It gets a helper `spleen_pixels(fc, s, x, y, n)` that computes the expected pixels from `spleen.py` bytes directly (MSB left, n x n), not through `fonts`, for any face width (bpr 1 or 2). It also gets `counting(screen, raw)`, which wraps `raw.blit` and `screen._d._fill_rect_raw` and returns a dict of call counts; it must be applied before the first draw on that screen.
  - `test_mock_text_height_and_max_chars`:
    - 128: `[s.text_height(), s.text_height(2), s.text_height(0)] == [8, 16, 8]`, `max_chars == 16`;
    - 240: `[16, 32, 16]`, `max_chars == 30`.
    - Also edit `test_mock_k_and_u_at_128_and_240` L99 to `(16, 30)`.
  - `test_mock_pixel_text_matches_the_spleen_rows[scale]` for scale 1, 2, 3: on `panel(240)`, `s.text("Élève 12:3.5°Ÿ", at=(5, 30), color=(255, 255, 255), scale=scale)` gives `lit(raw) == {p: 5 for p in spleen_pixels(sp.F8X16, "Élève 12:3.5°Ÿ", 5, 30, scale) if 0 <= p[0] < 240 and 0 <= p[1] < 240}`. The ':' and '.' must be full-width 8x16 cells (primitives use the full sets, never the narrow window or bold, 5.3), and 'Ÿ' comes from slot 159.
    - scale 1: 342 pixels, box (5, 30, 115, 41);
    - scale 2: 1368 pixels, box (5, 30, 226, 53);
    - scale 3: the row runs past x 239 and is clipped.
  - Extend `test_mock_text_scale_0_counts_as_1` (scaling file) with the pixel text on 240: `text("Hi", at=(10, 20), scale=0)` has the same `lit` as `scale=1`, and it is not empty.
  - `test_mock_pixel_text_unknown_character_is_a_question_mark` (Review Focus 2): `lit` of `text("€5", at=(0, 0))` equals that of `text("?5", at=(0, 0))`.
  - `test_mock_pixel_text_clips_at_the_panel_edges` (Review Focus 3):
    - `text("Hello", at=(-5, 230), scale=2)` and `text("Hi", at=(235, -10), scale=3)` give `lit` equal to `spleen_pixels(...)` restricted to `0 ≤ x, y < 240`;
    - `text("A", at=(300, 300))` draws nothing;
    - nothing raises.
  - `test_mock_pixel_text_call_counts`:
    - `text("Hi", at=(0, 0))` → 2 blits, 0 fill_rect;
    - `scale=2` → 0 blits, 28 fill_rect (19 + 9 runs; fewer than 252 // 4).
  - `test_mock_draw_value_ink_is_narrow_and_bold`. Give `RecordingDisplay` a `draw_glyphs(fc, glyphs, n, bold, c)` that records `("glyphs", fc[0], fc[1], list(glyphs), n, bold)`. With o8 = offset of "8" and o. = offset of "." in `F16X32`:
    - `s._draw("8.8", 100, 50, WHITE, VALUE, 4)` → `("glyphs", 16, 32, [(o8, 100, 50), (o., 112, 50), (o8, 124, 50)], 1, 1)`;
    - f 8 → `[(o8, 100, 50), (o., 124, 50), (o8, 148, 50)]`, n 2, bold 1;
    - `s._draw("12:30 PM", 0, 0, WHITE, VALUE, 2)` → `F8X16`, bold 0, ':' at x 14, '3' at x 20;
    - `s._draw("a.b", 0, 0, WHITE, TEXT, 2)` → x 0, 8, 16.
  - Rename `test_mock_widget_text_is_scaled_by_k` to `test_mock_widget_text_routes_to_the_spleen_faces`. For now:
    - `[c[0] for c in d.calls[:4]] == ["scaled"] * 4`, with scales `[2, 2, 4, 4]` (title, "NE", "S" ×2, `value(42)` are unchanged until Tasks 7-8);
    - `d.calls[4:] == [("glyphs", 8, 16, [(o_x, 10, 20), (o_y, 18, 20)], 1, 0), ("glyphs", 8, 16, [(o_x, 10, 20), (o_y, 34, 20)], 3, 0)]`.
  - `test_mock_128_never_touches_spleen` (on `panel(128)` with `counting`): draw every widget plus `text` at every anchor and at (x, y) with scale 2. Then `"steami_screen.spleen" not in sys.modules` and blits == 0.
- [ ] **Step 2: Run.** `.venv/bin/python -m pytest tests/test_steami_screen_spleen_mock.py tests/test_steami_screen_scaling_mock.py -q` → the new and edited tests FAIL.
- [ ] **Step 3: Implement** the Produces list. Update the module docstring: on 240 the text is Spleen, one font per panel, `text(s, (x, y))` is 8x16 x scale (ASCII `x`, see Global Constraints), and strokes still use k. Also update the `text()` docstring.
- [ ] **Step 4: Run.** The same two files → PASS. `make test-mock` (the 128 golden unchanged) and `make lint` → clean.
- [ ] **Step 5: Commit.** `git add lib/steami_screen/steami_screen/device.py tests/test_steami_screen_spleen_mock.py tests/test_steami_screen_scaling_mock.py`, message `feat(steami_screen): Draw the 240 px pixel text in Spleen 8x16.`

### Task 7: The fitting kernel by ink, and the TEXT and LABEL widgets on 240

**Files:**
- Modify: `lib/steami_screen/steami_screen/device.py`:
  - `_at` L108-110, `_ink`/`_band`/`_fit`/`_put` L144-206 (plus the new `_place`), `_txt` L736-741;
  - `_value` L256-323 (only its calls, switched to the temporary `*8` names);
  - `text()` L648-666;
  - `subtitle` L325-362, `gauge` L418-419, `graph` L434-457, `menu` L493-515, `compass` L532, `watch` L585-591;
  - the import line gains `LABEL`: `from steami_screen.fonts import LABEL, TEXT, VALUE`.
- Test: `tests/test_steami_screen_scaling_mock.py`, `tests/test_steami_screen_spleen_mock.py`

**Interfaces:**
- Consumes: Task 4 helpers; `Screen._draw`, `Screen._tw`, `Screen.text_height` (Task 6).
- Produces:
  - `Screen._band(self, m, y, n) -> tuple | None`:
    - `(0, width - 1)` when `m == 0`;
    - else `self._chord(y + a*n, y + b*n + n - 1)` with `a, b = fonts.ink_rows(m)`.
  - `Screen._fit(self, s, y, ink, f, lo=0, hi=None, shrink=0, pad=0) -> (n, lo, hi, fn)`:
    - `fn = fonts.face(s, ink, f)` is judged once from the whole `s` and returned, so the drawing uses it; `(0, lo, hi, None)` when there is no face;
    - the masks come from one `fonts.masks(fc, s)` call and the widths from one `fonts.widths(s, ink, f)` call (no `width(s, n)` per n); the band is `_band(m, y, n_rep)`;
    - otherwise the existing loop is kept, including "no ink always fits".
  - `Screen._place(self, s, ax, y, color, ink, f, align, fit) -> (x, w)`: the existing alignment and clamp of `_put`, for a `fit = (n, lo, hi, fn)` already computed, with `w = fonts.width(s, n, ink, f)`. When n > 0 it calls `self._draw(s[:n], x, y, color, ink, f, fn)`: the face of the whole text, never one judged again from the prefix.
  - `Screen._put(self, s, ax, y, color, ink, f, align=1, lo=0, hi=None, shrink=0) -> (x, w)`: `self._place(s, ax, y, color, ink, f, align, self._fit(s, y, ink, f, lo, hi, shrink))`. It has 10 parameters besides `self` (the ruff limit): `pad` is gone from `_put`, because only `_value` passes one, and `_value` calls `_fit` and `_place` itself (Task 8).
  - `Screen._txt(self, s, x, y, c, f=1, alt="text", ink=TEXT)`: k > 1 → `_draw(s, x, y, c, ink, f)`; k == 1 → unchanged.
  - Temporary: the old `_ink`, `_band`, `_fit`, `_put` bodies are renamed `_ink8`, `_band8`, `_fit8`, `_put8`, unchanged except that inside them every call goes to the `*8` names (`_fit8` calls `self._ink8` and `self._band8`, `_put8` calls `self._fit8`). `_value` is edited to call `_fit8` and `_put8` (L288, L300, L313, L318, L321, L323) and keeps doing so until Task 8 deletes the `*8` helpers.

Widget changes (240 only; the k == 1 branches are untouched):

| Site | Change |
|---|---|
| `_at` cap | `min(h, STEAMI_TITLE_CAP_CELLS * fonts.advance(TEXT, k) // 2)` (52) |
| `text(at)` | `_at(at, self._tw(text, TEXT, f), f)`; each `_put` gets `TEXT, f` |
| `subtitle` | `_at("S", max(self._tw(l, TEXT, k) for l in lines), k)`; `m = fonts.masks(fonts.face(line, TEXT, k)[0], line)[-1] if line else 0`; inside `fits()`, `_band(m, y + i * line_h, 1)` and `self._tw(line, TEXT, k) <= c[1] - c[0] + 1` (replacing `len(line) * 8 * k`, or the block rises too far); `_put(line, cx, y, color, TEXT, k)` |
| `gauge` labels | `_put(t, px, py, GRAY, LABEL, k, 1, 0, None, k)` |
| `graph` value | `tw = self._tw(text, TEXT, k)`, `_txt(..., ink=TEXT)` |
| `graph` labels | inside the k > 1 branch: `fc = fonts.face(label, LABEL, k)[0]; a, b = fonts.ink_rows(fonts.masks(fc, label)[-1])` (device.py never names `F6X12` and never imports spleen at module level); `y = gy + u(2) - a` for the max, else `yp - k - u(2) - b`; `_txt(label, gx + k + u(2), y, DARK, k, ink=LABEL)` |
| `menu` | row test unchanged (192 px, 5 rows: comment "kept MicroPython difference: Arduino shows 6 rows with a bar clipped per scanline"); items `_put(text, x, iy, c, TEXT, k, 0, x, None, k)` |
| `compass` | `_txt(label, lx - self._tw(label, TEXT, k) // 2, ly - self.text_height() // 2, c, k)` (128 still gives `lx - 4, ly - 4`) |
| `watch` | `tw = self._tw(text, TEXT, k)`, y `ly - self.text_height() // 2` |

- [ ] **Step 1: Rewrite the tests to the Arduino goldens** (numbers from the spleen-map-arduino §4; ink boxes):
  - `test_mock_resolve_every_anchor_at_240`: the N-row tuples become `(16, 2, 37), (176, 2, 37), (208, 2, 37), (16, 4, 67), (16, 3, 52)`. The other lines are unchanged.
  - `HI_240`, in `ANCHORS` order:

    | Scale | N | NE | E | SE | S | SW | W | NW | CENTER |
    |---|---|---|---|---|---|---|---|---|---|
    | 1 | (112, 39, 125, 48) | (191, 39, 204, 48) | (202, 114, 215, 123) | (194, 189, 207, 198) | (112, 189, 125, 198) | (31, 189, 44, 198) | (22, 114, 35, 123) | (34, 39, 47, 48) | (112, 114, 125, 123) |
    | 2 | (104, 71, 131, 90) | (171, 71, 198, 90) | (171, 109, 198, 128) | (171, 145, 198, 164) | (104, 145, 131, 164) | (37, 145, 64, 164) | (37, 109, 64, 128) | (37, 71, 64, 90) | (104, 109, 131, 128) |

  - `TITLES_240`:

    | Title | GRAY ink box |
    |---|---|
    | "Distance" | (88, 39, 150, 48) |
    | "Temperature" | (76, 39, 162, 51) |
    | "Comfort" | (92, 39, 146, 48) |
    | "Battery" | (92, 39, 146, 51) |
    | "Mood" | (104, 39, 134, 48) |
    | "ABCDEFGHIJKLM" | (68, 39, 170, 48) |
    | "ABCDEFGHIJKLMNOPQRST" | (40, 39, 199, 50) |
    | "_" × 14 | (64, 51, 174, 51) |
    | "_" × 14 + "T" | (60, 39, 179, 51) |
    | "Températureéééé" | (60, 38, 178, 51) |
    | "ABCDEFGHIJKLMNOPQRSTUVW" | (32, 39, 206, 50) |
    | "_" × 22 | (32, 51, 206, 51) |

  - `test_mock_title_at_scale_2_sits_at_its_floor`: `text("ABCDEFGH", at="N", scale=2)` → `(56, 71, 181, 90)`.
  - `test_mock_lowercase_title_takes_its_width_from_its_inked_rows`:
    - `title("acemnorsuvwxz")` → `(68, 42, 170, 48)`;
    - `title(t)` with t = `"acemnorsuvwxzacemnorsuv"` (23 characters) has the same `lit` as `text(t[:22], at=(32, 37), color=GRAY)`.
  - `test_mock_long_title_draws_only_glyphs_inside_the_circle` (pixel version; `RecordingDisplay` no longer needed): `title("A very long title text")` gives the GRAY box `(32, 39, 206, 51)`. Its `lit` equals that of `text("A very long title text", at=(32, 37), color=GRAY)` (22 kept), and `not outside(raw, slack=0)`.
  - `test_mock_widget_text_routes_to_the_spleen_faces`: the first three records become `("glyphs", 8, 16, [...], 1, 0)` at (112, 37), (191, 37), and n 2 at (104, 141). The fourth (`value(42)`) is still `"scaled"`.
  - `SUBTITLES_240` (DARK ink box per line):

    | Lines | Boxes |
    |---|---|
    | ("VL53L1X ToF",) | (76, 204, 162, 213) |
    | ("WSEN-HIDS",) | (84, 204, 154, 213) |
    | ("SURPRISED",) | (84, 204, 154, 213) |
    | ("BME280",) | (96, 204, 142, 213) |
    | ("BQ27441",) | (92, 204, 146, 215) |
    | ("VL53L1X",) | (92, 204, 146, 213) |
    | ("Comfortable",) | (76, 204, 162, 213) |
    | ("Uncomfortable",) | (68, 204, 170, 213) |
    | ("20s window",) | (80, 204, 158, 213) |
    | ("3842 mV", "BQ27441") | (92, 179, 146, 188), (92, 199, 146, 210) |
    | ("Comfortable", "BME280") | (76, 179, 162, 188), (96, 199, 142, 208) |
    | ("Uncomfortable", "BME280") | (68, 179, 170, 188), (96, 199, 142, 208) |
    | ("Comfortable", "WSEN-HIDS") | (76, 179, 162, 188), (84, 199, 154, 208) |
    | ("WSEN-HIDS", "20s window") | (84, 179, 154, 188), (80, 199, 158, 208) |

  - `test_mock_gauge_ring_at_240`: GRAY box `(52, 170, 192, 177)` (6x12 "0" and "100"), with comment "Arduino kGaugeLabels". Ring rows 7..19 unchanged.
  - `test_mock_watch_numbers_at_240`: `(39, 37, 199, 200)`.
  - `test_mock_compass_at_240`: the N box is `(116, 7, 122, 16)` for every heading (the MicroPython rose does not turn).
  - `test_mock_menu_shows_five_rows_inside_the_circle`: numbers unchanged; the comment names the kept difference.
  - `test_mock_graph_value_and_labels_at_240`: WHITE `(112, 60, 126, 69)`.
  - `test_mock_graph_labels_clear_the_axes_at_240`: bands `[(74, 81), (107, 114), (156, 163)]`, for `max_val` 100 and 2000 ("2k", "1k" ink rows 1..8 too). The comment names the three labels as a kept difference.
  - New `test_mock_empty_texts_raise_nothing` (Review Focus 4), each on a fresh 240 panel:
    - `title("")`, `subtitle("", "x")`, `subtitle("")`, `menu([""])`, `text("", at="N")`, `text("   ", at="CENTER", scale=2)`, `graph([5], 0, 10)`;
    - nothing raises and `not outside(raw, slack=0)`.
  - New in the spleen file, `test_mock_cut_value_text_keeps_the_face_of_the_whole_text` (design 5.1, on `RecordingDisplay`): `s._put("12:30 PM", 0, 100, WHITE, VALUE, 4, 0, 0, 60)` keeps "12:3" (16 + 16 + 8 + 16 = 56 ≤ 61 px) and records `("glyphs", 8, 16, <4 entries>, 2, 0)`: the TEXT-ladder face of the whole text, never `("glyphs", 16, 32, ..., 1, 1)` judged from the all-digit prefix.
  - New in the spleen file, `test_mock_native_widget_text_is_one_blit_per_glyph`, with `counting` on 240:
    - `title("Distance")` → 8 blits, 0 fill_rect;
    - `subtitle("VL53L1X ToF")` → 11 blits;
    - `gauge(342, 0, 500)` → 4 blits.
- [ ] **Step 2: Run.** `.venv/bin/python -m pytest tests/test_steami_screen_scaling_mock.py tests/test_steami_screen_spleen_mock.py -q` → the rewritten tests FAIL. The value tests still PASS.
- [ ] **Step 3: Implement** the Produces list and the table. `device.py` keeps `CHAR_W = CHAR_H = 8` and its 128-unit constants.
- [ ] **Step 4: Run.** The same files → PASS (value tests unchanged). `make test-mock` (128 golden unchanged) and `make lint` → clean.
- [ ] **Step 5: Commit.** `git add lib/steami_screen/steami_screen/device.py tests/test_steami_screen_scaling_mock.py tests/test_steami_screen_spleen_mock.py`, message `feat(steami_screen): Fit the 240 px widget text in the Spleen faces.`

### Task 8: `value()` on 240: value faces, narrow '.' ':', bold, floor k

**Files:**
- Modify: `lib/steami_screen/steami_screen/device.py`: `_value` L256-323; delete `_ink8`, `_band8`, `_fit8`, `_put8` and the `framebuf` import of the 240 path.
- Test: `tests/test_steami_screen_scaling_mock.py` (L334-441), `tests/test_steami_screen_spleen_mock.py`

**Interfaces:**
- Consumes: `_fit`, `_place`, `_put`, `_draw`, `_tw` (Tasks 6-7), `fonts.face`, `fonts.width`.
- Produces: `_value(text, unit, at, label, color, scale, y_offset)`, with the same signature:
  - f runs from `max(scale, 1) * k` down to `k`. An f where `fonts.face(text, VALUE, f)` is `None` is skipped. The loop breaks on `fits or f == k`.
  - `vw = fonts.width(text, len(text), VALUE, f)`.
  - B6 at W/E: `max(vw, fonts.width("88.8", 4, VALUE, f))` (14f).
  - The value is fitted once: `fit = self._fit(text, y, VALUE, f, lo, hi, 0, pad)` (the loop's own fit at CENTER/N/S, computed once after the loop at W/E and the corners), then drawn with `self._place(text, ax, y, color, VALUE, f, align, fit)`. No second fit.
  - Label: `ly = y - self.u(4) - 12`, `fit = self._fit(label, ly, LABEL, k, lo, hi, sh)`. When `fit[0]` is 0, the lowering loop runs over `range(ly + 1, y - 12 + 1)` (kept difference) and keeps the row and the fit tuple of the first row with the most characters. The label is drawn with `self._place(label, ax, ly, GRAY, LABEL, k, align, fit)`, without fitting it again.
  - Unit: `_put(unit, ax, y + 8 * f, LIGHT, TEXT, k, align, lo, hi, sh)`.
  - The docstring says "down to k". Comments in ASCII ("label 6x12 at top - u(4) - 12").

- [ ] **Step 1: Rewrite the value tests to the Arduino goldens.** WHITE value, GRAY label, LIGHT unit ink boxes; the colour is WHITE unless named.
  - `test_mock_value_center_with_unit_and_offset`: `value(72, unit="%", y_offset=-12)` → WHITE `(106, 75, 134, 94)`, LIGHT `(117, 103, 122, 112)`.
  - `test_mock_value_center_default`:
    - `value(23.5)` → `(94, 110, 146, 129)`;
    - `value(8)` → `(114, 110, 126, 129)`, `count(raw, WHITE) == 146`.
  - New `test_mock_value_program_04_and_01`:
    - `value(342, unit="mm")` → `(98, 97, 142, 116)` and LIGHT `(112, 128, 126, 134)`;
    - `value(23.5, unit="°C")` → `(94, 97, 146, 116)` and LIGHT `(113, 124, 126, 134)`.
  - New `test_mock_value_at_n_and_s`:
    - `value(23.5, unit="°C", at="N")` → `(94, 73, 146, 92)`, LIGHT `(113, 100, 126, 110)`;
    - `at="S"` → `(94, 147, 146, 166)`, LIGHT `(113, 174, 126, 184)`.
  - `SIDES_240` (W, E), with unit `"C"`:

    | Text | W | E |
    |---|---|---|
    | "1" | (55, 97, 65, 116) | (175, 97, 185, 116) |
    | "8888" | (30, 97, 90, 116) | (150, 97, 210, 116) |
    | "123456" | (15, 97, 106, 116) | (135, 97, 226, 116) |
    | "12:34:56" | (20, 100, 101, 114) | (141, 100, 222, 114) |

  - New `test_mock_value_mockup_03`:
    - `value(23.5, "°C", "W", "TEMP")` → `(34, 97, 86, 116)`, GRAY `(51, 73, 73, 80)`, LIGHT `(52, 124, 65, 134)`;
    - `value(45.3, "%", "E", "HUM")` → `(154, 97, 206, 116)`, GRAY `(168, 73, 184, 80)`, LIGHT `(179, 125, 184, 134)`.
  - `test_mock_value_side_is_cut_at_scale_1`, renamed `test_mock_value_side_is_cut_at_factor_k`: `"Uncomfortable"` and `"ABCDEFGHIJKLMNO"` with `unit="C"`, `at="W"` → both `(7, 104, 109, 113)`.
  - `test_mock_value_center_cut_near_the_edge` → `(76, 11, 162, 20)`.
  - `test_mock_value_label_kept_when_the_value_falls_to_factor_1`, renamed `test_mock_value_floor_is_k_at_the_corners`:
    - `value(8, "C", "NE", "TEMP", scale=1)` → WHITE `(197, 39, 203, 48)`, GRAY `(159, 19, 181, 26)`, LIGHT `(197, 55, 203, 64)`;
    - `value(8, "C", "NW", "TEMP", scale=1)` (kept from the old parametrization): GRAY and WHITE boxes exist, `box(raw, GRAY)[3] < box(raw, WHITE)[1]`;
    - `value("Temperature", at="N", label="X", scale=1)` → WHITE top row 39, `box(raw, GRAY)[3] < 37`;
    - `not outside(raw, slack=0)` in each case.
  - `test_mock_value_label_row_unchanged_when_it_fits`: `value(8, "C", "NE", "TEMP")` → GRAY `(183, 49, 205, 56)`, WHITE `(189, 73, 201, 92)`, LIGHT `(191, 101, 197, 110)`.
  - New `test_mock_value_fit_floor_and_skipped_factors`:
    - `value("888888888888888", "°C", y_offset=-50, scale=4)` → `(76, 11, 162, 20)`;
    - `value("ABCDEFGHIJKLMNO", at="W", scale=4)` → `(3, 114, 113, 123)`;
    - `at="NE"` → `(85, 39, 203, 48)`;
    - `value(8888, at="W", scale=4)` → `(14, 104, 107, 133)` (f 7 skipped, 12x24 × 2).
  - New `test_mock_value_bold_stays_in_its_cells`:
    - `value("-88.8")`: `count(raw, WHITE) == 473`, every WHITE x in `[84, 156)`;
    - `scale=3`: 1176 pixels, x in `[66, 174)`.
  - New `test_mock_value_narrow_colon`: `value("12:30 PM", scale=1)` → `(91, 114, 148, 123)`, 228 pixels. WHITE pixels with `106 ≤ x ≤ 109` have x in `{107, 108}` and y in `117..123`.
  - New `test_mock_value_unknown_character`: `value("€5")` and `value("?5")` give the same `lit`: box `(104, 108, 133, 127)`, 236 pixels.
  - New `test_mock_value_face_follows_the_whole_text` (Review Focus 5), on `RecordingDisplay`, last record:
    - `value(float("nan"))` → `("glyphs", 8, 16, …3 entries, 2, 0)`;
    - `value(1e-05)` → 5 entries, n 2, bold 0;
    - `value(-0.5)` → `("glyphs", 16, 32, …4 entries, 1, 1)`.
  - New `test_mock_value_of_empty_text_raises_nothing` (Review Focus 4): `value("")` draws no WHITE pixel; `value("", unit="", label="")` and `value(" ")` raise nothing.
  - New `test_mock_value_label_never_enters_the_value_rows` (kept lowering): for `y_offset in range(-64, -39, 4)`, `value(8, "C", label="TEMP", y_offset=y_offset)`. When both boxes exist, `box(GRAY)[3] < box(WHITE)[1]`, and `not outside(raw, slack=0)`. At `y_offset=-40` (value top 16, label cell row 16 - 7 - 12 = -3, whose ink rows leave the circle, so nothing fits there) `box(raw, GRAY)` must not be `None`: the label was lowered, not dropped. This guards the kept "label lowered when no character fits".
  - New in the spleen file, `test_mock_value_label_draws_accents_in_6x12` (5.4, LABEL face): `value(8, label="ÉŸ")` on 240 → the GRAY pixels equal `spleen_pixels(sp.F6X12, "ÉŸ", 114, 85, 1)`: 36 pixels, box (114, 85, 124, 93) (value top 104, label cell top 104 - 19 = 85, centred on x 120; É inks row 0, Ÿ is the slot-159 Y).
  - `test_mock_widget_text_routes_to_the_spleen_faces`: the fourth record becomes `("glyphs", 16, 32, [(o4, 104, 104), (o2, 120, 104)], 1, 1)`.
  - `test_mock_value_label_and_unit_stay_in_their_half`: comment only, in ASCII ("label 6x12 at top - u(4) - 12").
  - New in the spleen file, `test_mock_program_04_text_is_31_blits` (with `counting`):
    - `gauge(342, 0, 500)`, `title("Distance")`, `value(342, "mm")`, `subtitle("VL53L1X ToF")` → 31 blits in total;
    - the fill_rect count equals that of `gauge(342, 0, 500)` alone on a fresh panel.
- [ ] **Step 2: Run.** `.venv/bin/python -m pytest tests/test_steami_screen_scaling_mock.py tests/test_steami_screen_spleen_mock.py -q` → the rewritten value tests FAIL.
- [ ] **Step 3: Implement** the Produces list, and delete the `*8` helpers. `grep -n "_fit8\|_put8\|_ink8\|_band8\|import framebuf" lib/steami_screen/steami_screen/device.py` → no output.
- [ ] **Step 4: Run.** The same files → PASS. `make test-mock` and `make lint` → clean.
- [ ] **Step 5: Commit.** `git add lib/steami_screen/steami_screen/device.py tests/test_steami_screen_scaling_mock.py tests/test_steami_screen_spleen_mock.py`, message `feat(steami_screen): Fit 240 px values in the Spleen value faces.`

### Task 9: 128 px: fold accents, draw the degree sign, one new golden entry

**Files:**
- Modify: `lib/steami_screen/steami_screen/device.py`:
  - `_txt` (k == 1 branch);
  - `value()` 128 path L245-254;
  - `menu()` L515;
  - new `_text8`, `_degree8`.
- Modify: `tests/test_steami_screen_golden_mock.py` (docstring L7-10, `SCRIPTS`), `tests/golden/steami_screen_128.json` (regenerated)
- Test: `tests/test_steami_screen_spleen_mock.py`

**Interfaces:**
- Consumes: `fonts.fold8`, `fonts.DEGREE8`, `fonts.draw_runs` (Task 4).
- Produces:
  - `Screen._text8(self, s, x, y, c, f, alt) -> None`. It splits `s` at `"°"` first, then folds each segment with `fonts.fold8` (so a literal `"\x7f"` in the text stays a framebuf checkerboard, as in v0.30, and is never drawn as a degree).
    - Each folded segment is drawn as today: `alt is None` or `f > 1` → `_draw_scaled_text(seg, x, y, c, f)`; else `getattr(self._d, alt, self._d.text)(seg, x, y, c)`.
    - Each `"°"` goes to `_degree8`, and the pen advances 8f per character (`len` of the segment, plus 8f per degree).
    - A string without `"°"` makes exactly one call, as before.
  - `Screen._degree8(self, x, y, c, f) -> None`: `fonts.draw_runs(self._fill_rect, fonts.DEGREE8, ((0, x, y),), f, 0, c)`.
  - Routing on 128:
    - `_txt` → `_text8(s, x, y, c, f, alt)`;
    - `value()`: label `_text8(label, lx, y - CHAR_H - 4, GRAY, 1, "text")`, value `_text8(text, x, y, color, scale, None)`, unit unchanged through `_txt`;
    - `menu()`: `_text8(text, x, iy, c, 1, "text")`.

- [ ] **Step 1: Write the failing tests** (a local `Rec128` display: width = height = 128, recording `text`, `fill_rect`, `draw_scaled_text`, `pixel`, `line`, `rect`, `fill`, `show` with colours as given):
  - `test_mock_128_folds_accents_to_one_cell`: `title("Été")` records `("text", "Ete", 52, 20, GRAY)`.
  - `test_mock_128_degree_is_the_arduino_glyph`:
    - `text("°", at=(10, 20))` records `[("fill_rect", 12, 20, 2, 1, W), ("fill_rect", 11, 21, 1, 1, W), ("fill_rect", 14, 21, 1, 1, W), ("fill_rect", 11, 22, 1, 1, W), ("fill_rect", 14, 22, 1, 1, W), ("fill_rect", 12, 23, 2, 1, W)]`;
    - `scale=2` records `(14, 20, 4, 2), (12, 22, 2, 2), (18, 22, 2, 2), (12, 24, 2, 2), (18, 24, 2, 2), (14, 26, 4, 2)`.
  - `test_mock_128_text_splits_at_the_degree`: `text("23°C", at=(0, 0))` records `("text", "23", 0, 0, W)`, then the six degree runs at x 16, then `("text", "C", 24, 0, W)`.
  - `test_mock_128_leaves_other_characters_to_framebuf` (Review Focus 2): `text("€", at=(0, 0))` records `("text", "€", 0, 0, W)`, and `text("a\x7fb\n", at=(0, 0))` records exactly one call, `("text", "a\x7fb\n", 0, 0, W)` (no degree runs).
  - Extend `test_mock_128_never_touches_spleen` with `title("Été")`, `value(21.5, unit="°C", label="Températ")`, `menu(["Réglages"])`.
  - Golden: add the entry `"accents": lambda s: (s.title("Été"), s.subtitle("élève", "Ÿ"), s.text("23°C", at="NE"), s.value("Été", unit="°C"), s.value(21.5, unit="°C", label="Températ"), s.menu(["Réglages", "Données"], selected=0), s.text("°", at=(3, 100), scale=2))`. Extend the docstring: "The accents entry was added when accented letters were folded to one 8x8 cell (they were two checkerboards, 16 px, for one counted cell) and '°' drawn with the Arduino 8x8 degree glyph (it was two checkerboards); no other entry changed."
- [ ] **Step 2: Run.** `.venv/bin/python -m pytest tests/test_steami_screen_spleen_mock.py tests/test_steami_screen_golden_mock.py -q` → the new tests FAIL, and `test_mock_golden_covers_every_script` FAILS.
- [ ] **Step 3: Implement** the Produces list.
- [ ] **Step 4: Regenerate the golden and check that only the new key was added.** `STEAMI_GOLDEN_WRITE=1 .venv/bin/python -m pytest tests/test_steami_screen_golden_mock.py -q`, then `git diff --numstat tests/golden/steami_screen_128.json`: only added lines, and the removed count is 0 (or 1, if the previous last entry's closing `]` gained a comma). `git diff tests/golden/steami_screen_128.json | grep '^-[^-]'` shows at most that one line.
- [ ] **Step 5: Run.** `make test-mock` and `make lint` → clean.
- [ ] **Step 6: Commit.** `git add lib/steami_screen/steami_screen/device.py tests/test_steami_screen_golden_mock.py tests/golden/steami_screen_128.json tests/test_steami_screen_spleen_mock.py`, message `feat(steami_screen): Fold accents and draw the degree sign on 128 px.`

### Task 10: V1c hardware scenario additions (written now, run by the controller in Task 13)

**Files:**
- Modify: `tests/scenarios/steami_screen_v1c.yaml` (append tests)

**Interfaces:**
- Consumes: the firmware of Task 12 (frozen `steami_screen.spleen`); `screen._d._raw.pixel(x, y)` reads back palette indexes (WHITE 5, GRAY 3).

- [ ] **Step 1: Append four `hardware_script` tests** (`expect_true: true`, `mode: [hardware]`):
  - "Spleen is frozen and blitted read-only":
    - no file-system copy: `"steami_screen" not in os.listdir("/flash")`, and the same for `/flash/lib` when it exists (a frozen module's `__file__` is the relative `"steami_screen/spleen.py"`, like a copy imported from cwd `/flash`, so `__file__` proves nothing);
    - the table is read in place from flash: `0x08000000 <= uctypes.addressof(spleen.F8X16[4]) < 0x08084000` (also proves the bytes were not copied to the heap);
    - `framebuf.FrameBuffer(spleen.F8X16[4], 8, 16, framebuf.MONO_HLSB)` raises `TypeError`;
    - on a `GS4_HMSB` 8x16 `bytearray(64)` FrameBuffer, blitting `(memoryview(F8X16[4])[528:544], 8, 16, MONO_HLSB)` at (0, 0) with key 0 and a palette over `bytearray([5])` lights 44 pixels of index 5.
  - "Accents and degree are drawn":
    - after `title("Été")`, some x in 108..115 at row 37 reads 3 (the accent, row 0 of 'É');
    - after `clear()` and `text("23°C", (10, 150), WHITE, 2)`, (46, 152) reads 5 and (42, 150) reads 0.
  - "max_chars and text_height": `screen.max_chars == 30 and screen.text_height() == 16 and screen.text_height(2) == 32`.
  - "Widget text timing" (design 8.1: title, value with unit and label, subtitle and gauge labels of programs 01 and 04, and a 15-character `text(s, (x, y), c, 2)`). The same script runs on the old firmware in Task 13 Step 1, so it touches the private `_put` through a signature check:
    - warm-up, not timed: `screen.title("x"); screen.value(1, "x", label="x"); screen.text("0", (0, 0)); screen.clear()` (pays the lazy `import steami_screen.spleen`, the palette FrameBuffer and the first lookups);
    - each entry is timed 3 times, each run after `screen.clear()` and `gc.collect()` (not timed), as `t0 = time.ticks_us(); call(); dt = time.ticks_diff(time.ticks_us(), t0)`, and the minimum of the 3 is kept;
    - entries, program 04: `title("Distance")`, `value(342, "mm")`, `subtitle("VL53L1X ToF")`, `gauge(342, 0, 500)` (whole widget, arc included), and the two gauge labels alone: `"0"` at (55, 169) and `"500"` at (185, 169) (the points `gauge()` computes at k = 2), drawn with `screen._put(t, x, 169, GRAY, 1, 2, 1, 0, None, 2)` (LABEL is 1) when `hasattr(screen, "text_height")`, else with the v0.30 signature `screen._put(t, x, 169, GRAY, 2, 1, 0, None, 2)`;
    - program 01: `title("Temperature")`, `value(23.5, "°C")`, `subtitle("BME280")`; mockup 03: `value(23.5, "°C", "W", "TEMP")`;
    - pixel text: `text("ABCDEFGHIJKLMNO", (0, 100), WHITE, 2)`;
    - `print` each as `name us`;
    - `result` is True when every widget text entry (titles, values, subtitles, the two gauge labels) is below 10 000 us. The whole `gauge(...)` (arc-bound, 270 to 560 ms) and the pixel text are reported only, and compared with the baseline in Task 13.
- [ ] **Step 2: Run.** `.venv/bin/python -m pytest tests/ -q -k steami_screen_v1c` → the new tests are collected and SKIPPED (no `--port`). `make test-mock` → clean.
- [ ] **Step 3: Commit.** `git add tests/scenarios/steami_screen_v1c.yaml`, message `test(steami_screen): Check the Spleen fonts and their timing on a V1c.`

### Task 11: Documentation

**Files:**
- Modify:
  - `lib/steami_screen/README.md` (Text section L102-116, Properties L224-231, GC9A01 section L249-269, new "Fonts and licence" section);
  - `lib/gc9a01/README.md` L116;
  - `lib/steami_screen/examples/gauge_demo.py` L51-52 (comment only).

- [ ] **Step 1: `lib/steami_screen/README.md`:**
  - Fonts: 8x8 on 128 px. On 240 px, Spleen 2.1.0, with the face table of Global Constraints: TEXT 8x16, LABEL 6x12, values 8x16/12x24/16x32 (bold on 12x24/16x32, narrow '.' ':').
  - `text(s, (x, y), c, scale)` is 8x16 × scale on 240 px. It is 16 px tall at scale 1: a visible change from v0.30.
  - Accents: drawn on 240 px; on 128 px folded to the base letter, and '°' drawn as an 8x8 degree. Other characters (control characters, "€", emoji): one '?' cell on 240 px; on 128 px unchanged from v0.30 (framebuf's checkerboard per UTF-8 byte).
  - The kept MicroPython differences (list of the spec).
  - Properties: `screen.max_chars   # 16 on 128 px, 30 on 240 px` and `screen.text_height(scale=1)   # 8 * scale on 128 px, 16 * scale on 240 px`.
  - A "Fonts and licence" section with the Spleen copyright line and the full BSD-2 notice, copied from `spleen.py` lines 15-40, plus the generator and commit (`scripts/gen-spleen-fonts.py --micropython`, arduino-steami-lib `3aae3af`).
- [ ] **Step 2: `lib/gc9a01/README.md` L116** →
  - `` `blit(fb, x, y, key=-1, palette=None)` — copy a FrameBuffer, or a read-only `(buffer, w, h, format)` tuple; ``
  - `` with a palette each source pixel is mapped through it before the key test; pixels equal to `key` are skipped ``.
- [ ] **Step 3: `gauge_demo.py` L51-52 comment** (ASCII only, RUF003) → "Sized from the glyphs it erases: the CENTER text is Spleen 8x16 on 240 px (8x8 on 128 px), up to 7 characters ("1234 mm", 56 x 16 on 240 px), inside a box 7 * 8 * k wide and 8k + 2 tall." The code is unchanged.
- [ ] **Step 4: Run.** `.venv/bin/python -m pytest tests/test_examples.py -q` → PASS. `make lint` → clean.
- [ ] **Step 5: Commit.** `git add lib/steami_screen/README.md lib/gc9a01/README.md lib/steami_screen/examples/gauge_demo.py`, message `docs(steami_screen): Document the Spleen fonts, text_height() and accents.`

---

## Firmware (fork `steamicc/micropython-steami`, separate PR, merged before the lib PR)

### Task 12: Move the file system 16 KB up

Paths:
- `FW=/tmp/claude-1000/-home-nedjar-sandbox-wiki-steami/fd048878-c715-498a-8954-e4ba541f26c4/scratchpad/fw-rebase` (existing clone)
- `FWW=/tmp/claude-1000/-home-nedjar-sandbox-wiki-steami/fd048878-c715-498a-8954-e4ba541f26c4/scratchpad/fw-spleen` (new worktree)
- `LIB=/tmp/claude-1000/-home-nedjar-sandbox-wiki-steami/fd048878-c715-498a-8954-e4ba541f26c4/scratchpad/wt-spleen`
- `LIBV=/tmp/claude-1000/-home-nedjar-sandbox-wiki-steami/fd048878-c715-498a-8954-e4ba541f26c4/scratchpad/lib-v0.30.2`
- `B=$FWW/ports/stm32/build-STEAM32_WB55RG`

**Files (in `$FWW`):**
- Create: `ports/stm32/boards/STEAM32_WB55RG/stm32wb55xg_steami.ld`
- Modify: `ports/stm32/boards/STEAM32_WB55RG/mpconfigboard.mk` L10 and L14
- Modify: `ports/stm32/boards/STEAM32_WB55RG/rfcore_firmware.py` L111 (comment) and L117

Do not touch:
- `boards/stm32wb55xg.ld` (shared with NUCLEO_WB55 and USBDONGLE_WB55);
- the `NUCLEO_WB55` copy of `rfcore_firmware.py`;
- any C file.

- [ ] **Step 1: Create the worktree.**
  - `git -C $FW fetch origin stm32-steami-rev1d-final`;
  - `git -C $FW worktree add -b steami-flash-fs-16k $FWW origin/stm32-steami-rev1d-final`.
  - `git -C $FWW log --oneline -1` shows the origin head (`7791e85d5` or newer).
- [ ] **Step 2: Fetch the submodules and build `mpy-cross`.**
  - `make -C $FWW/ports/stm32 BOARD=STEAM32_WB55RG submodules`;
  - `make -C $FWW/mpy-cross -j8`.
- [ ] **Step 3: Baseline build (origin layout, lib v0.30.2).**
  - `mkdir -p $LIBV && git -C $LIB archive v0.30.2 | tar -x -C $LIBV` (a plain export: no worktree is registered in the lib repository);
  - `rm -rf $FWW/lib/micropython-steami-lib && ln -s $LIBV $FWW/lib/micropython-steami-lib`;
  - clean rebuild: `rm -rf $B/frozen_mpy $B/frozen_content.c $B/firmware.elf && make -C $FWW/ports/stm32 BOARD=STEAM32_WB55RG -j8 && arm-none-eabi-size $B/firmware.elf`. Every build of this task uses this clean form: `tools/makemanifest.py` recompiles a frozen `.mpy` only when its source is newer than the cached `$B/frozen_mpy/<path>.mpy`, and `firmware.elf` depends only on the objects (not on the linker script), so after a symlink swap or a linker-script edit a plain `make` can reuse stale `.mpy` files or skip the link.
  - Expected: it links, with text+data about 515 808 B. Record text, data, text+data, and margin = 524 288 - (text+data) (about 8 480 B). `grep -c draw_glyphs $B/frozen_content.c` and `grep -c text_height $B/frozen_content.c` → 0 (the v0.30.2 code). Record `ls -l $B/frozen_mpy/steami_screen/`.
- [ ] **Step 4: Origin layout with the Spleen lib.**
  - `ln -sfn $LIB $FWW/lib/micropython-steami-lib`;
  - the clean rebuild of Step 3 (`rm -rf $B/frozen_mpy $B/frozen_content.c $B/firmware.elf`, then `make`).
  - `grep -c draw_glyphs $B/frozen_content.c` and `grep -c text_height $B/frozen_content.c` → ≥ 1 each (the new device.py and adapter were compiled, not the cached v0.30.2 ones).
  - Record either the ld error "region `FLASH' overflowed by N bytes" or the size and margin. It shows the need for the move.
  - Then `rm -rf $LIBV`: the export is no longer needed, and the next builds clear `$B/frozen_mpy` anyway.
- [ ] **Step 5: Write the linker script.** Copy `$FWW/ports/stm32/boards/stm32wb55xg.ld` to the new path. Change only:
  - the header comment: "STeaMi copy of stm32wb55xg.ld: the filesystem is moved up 16 KB to give the application 528 KB (frozen Spleen fonts); keep FLASH_FS below the BLE_HCILayer radio stack at 0x080E0000";
  - the three MEMORY lines of Global Constraints, with comments `pages 0-131`, `pages 8-131`, `pages 132-195`.

  Then append:

```
/* Build-time layout checks */
_steami_radio_stack_start = 0x080E0000; /* BLE_HCILayer v1.20.0 */
ASSERT(ORIGIN(FLASH) + LENGTH(FLASH) == ORIGIN(FLASH_FS), "FLASH must end where FLASH_FS starts")
ASSERT(ORIGIN(FLASH_APP) + LENGTH(FLASH_APP) == ORIGIN(FLASH_FS), "FLASH_APP must end where FLASH_FS starts")
ASSERT(ORIGIN(FLASH_FS) + LENGTH(FLASH_FS) <= _steami_radio_stack_start, "FLASH_FS overlaps the BLE_HCILayer radio stack at 0x080E0000")
```

- [ ] **Step 6: `mpconfigboard.mk`.** L10 and L14: replace `boards/stm32wb55xg.ld` with `boards/STEAM32_WB55RG/stm32wb55xg_steami.ld`. Keep `boards/common_bl.ld` / `boards/common_basic.ld` and both `TEXT0_ADDR`. L28-29 comment: "... fit in the 528 KB application flash (see stm32wb55xg_steami.ld)".
- [ ] **Step 7: `rfcore_firmware.py`.** L117 → `STAGING_AREA_START = 0x80C4000`. L111 comment → `(see boards/STEAM32_WB55RG/stm32wb55xg_steami.ld)`. The staging window below the radio stack shrinks from 128 KB to 0x080E0000 - 0x080C4000 = 114 688 B. Check that the radio-stack image the board uses still fits: BLE_HCILayer v1.20.0 occupies 80 KB from 0x080E0000 (spleen-map-firmware); if its `.bin` is at hand, record its size and confirm it is ≤ 114 688 B. Say in the commit body that the staging window is now 112 KB, and that a stack image larger than that is installed with STM32CubeProgrammer or EasyFlash, as the V1c stack was.
- [ ] **Step 8: Build after the move (Spleen lib).**
  - `rm -rf $B/frozen_mpy $B/frozen_content.c $B/firmware.elf && make -C $FWW/ports/stm32 BOARD=STEAM32_WB55RG -j8 && arm-none-eabi-size $B/firmware.elf`.
  - Expected: it links, and no ASSERT fires. `grep -c "steami_screen/spleen" $B/frozen_content.c`, `grep -c draw_glyphs $B/frozen_content.c` and `grep -c text_height $B/frozen_content.c` → ≥ 1 each. Record text+data, margin = 540 672 - (text+data), and `ls -l $B/frozen_mpy/steami_screen/`.
  - Expected sizes (spleen.mpy about 5.7 KB with this fork's `mpy-cross -O3`, fonts.py about 1.5-2.5 KB, device.py and the adapter about 1-2 KB more): text+data grows by about 9-11 KB from Step 3, and the margin is about 14-16 KB. Stop and report to the controller if the growth exceeds 13 KB or the margin falls below 8 KB (stale code paths, a table copied instead of frozen).
  - `grep -E "_micropy_hw_internal_flash_storage_(start|end)" $B/firmware.map` shows 0x08084000 and 0x080c4000.
  - Keep `$B/firmware.bin`, `.hex` and `.elf` for Task 13.
- [ ] **Step 9: Check that the radio-stack ASSERT fires.** Copy `$B/firmware.bin`, `.hex` and `.elf` of Step 8 aside first. Edit the FLASH_FS line to `LENGTH = 512K`, run `rm -f $B/firmware.elf` (the elf rule has no linker-script prerequisite, so without it make would not relink and the ASSERT would never be evaluated), then `make -C $FWW/ports/stm32 BOARD=STEAM32_WB55RG -j8 > <scratch>/assert.log 2>&1; echo $?`. The printed status must be non-zero, and `grep "FLASH_FS overlaps the BLE_HCILayer radio stack" <scratch>/assert.log` must match. Restore `256K`, run `rm -f $B/firmware.elf` again, rebuild, and check that `arm-none-eabi-size` matches Step 8 exactly.
- [ ] **Step 10: mboot (note only).** The mboot build already fails to link (pre-existing; FLASH_APP is too small even at 496K). Do not fix it. Say so in the commit body.
- [ ] **Step 11: Put the submodule back before committing.** Git refuses to work with a symlink at a submodule path.
  - `rm $FWW/lib/micropython-steami-lib && git -C $FWW submodule update --init lib/micropython-steami-lib`;
  - `git -C $FWW status --short` lists only the three board files.
- [ ] **Step 12: Commit (no push).**
  - Match the fork's subject style (`git -C $FW log --format=%s -5 origin/stm32-steami-rev1d-final`), for example `feat: Move the STeaMi filesystem up 16 KB for the frozen fonts.`
  - Body:
    - FLASH 528K / FLASH_APP 496K / FLASH_FS 0x08084000 256K, ending at 0x080C4000, 112 KB below BLE_HCILayer v1.20.0 at 0x080E0000;
    - the ASSERTs;
    - the `STAGING_AREA_START` change and why: "otherwise a radio-stack update would erase the last 16 KB of the filesystem", and the staging-window note of Step 7 (112 KB);
    - the sizes of Steps 3, 4 and 8 (text+data and margin, before and after);
    - "The update reformats the filesystem: files stored on the board are lost";
    - the mboot note.
  - No attribution lines, never "[skip ci]".
- [ ] **Step 13: Report to the controller:**
  - the branch, commit hash and sizes table;
  - the path of the firmware files;
  - the release note text: "This firmware moves the MicroPython filesystem: the first boot reformats it and every file stored on the board is lost. Copy your files off the board before updating."

  The push and the PR to `steamicc/micropython-steami` (base `stm32-steami-rev1d-final`) happen only after the maintainer approves them. That is a controller step.

## Controller steps and delivery

### Task 13: Hardware verification on a V1c (controller)

- [ ] **Step 1: Baseline timing on the current firmware** (v0.30.x lib frozen), before flashing. Run the timing script of Task 10's "Widget text timing" test with `mpremote run` (warm-up, `gc.collect()`, minimum of 3; it picks the v0.30 `_put` signature by itself), and record every entry in µs.
- [ ] **Step 2: Save any files** on the board's filesystem that must survive; the update erases them.
- [ ] **Step 3: Flash** the Task 12 Step 8 firmware (Spleen lib, new layout) with the usual DAPLink procedure.
- [ ] **Step 4: Check the move:**
  - the first boot shows a fresh filesystem (`os.listdir("/flash")`);
  - writing then reading back a small file works;
  - `import bluetooth; bluetooth.BLE().active(True)` returns `True` (the BLE_HCILayer stack at 0x080E0000 still starts).
- [ ] **Step 5: Run** `.venv/bin/python -m pytest tests/ -v -k steami_screen_v1c --port /dev/ttyACM0 -s` from `$LIB`. Expected: all pass, including the four Task 10 tests. Record the printed timings.
- [ ] **Step 6: Compare** the Step 1 and Step 5 timings. Every widget entry (programs 01 and 04 titles, values and subtitles, mockup 03's value, the two gauge labels, and the whole `gauge(342, 0, 500)`) must be ≤ its baseline, and every widget text entry must be < 10 ms (the Task 10 `result`). The pixel text `text(..., 2)` is reported with its baseline for information, not as an acceptance. If a check fails, stop and send the numbers back to the builder (the glyph-mask and spleen-module caches are already in place; profile `_fit` and `_draw` next).
- [ ] **Step 7: Photos** of program 04 (`gauge(342, 0, 500)`, `title("Distance")`, `value(342, "mm")`, `subtitle("VL53L1X ToF")`) and of an accent sample (`title("Été")`, `text("23°C", (10, 150), WHITE, 2)`), with the webcam `/dev/video4` (60 warm-up frames), for the PR.

### Task 14: Pull requests

- [ ] **Step 1: Final checks** in `$LIB`:
  - `make test-mock` → all pass; `make lint` → clean;
  - `git log --oneline v0.30.2..` shows the commits of Tasks 0-11 (Task 0 commits the plan and the design note; commit any later plan edit the same way, by name);
  - `git status --short` is empty (`.venv/` is ignored).
- [ ] **Step 2: Fork PR** (after the maintainer's approval, controller): push `steami-flash-fs-16k` and open a PR to `steamicc/micropython-steami`, base `stm32-steami-rev1d-final`. The body holds:
  - the Task 12 sizes;
  - the reformat warning;
  - the mboot note;
  - a link to the lib PR, as a full GitHub URL;
  - the issue as `steamicc/micropython-steami-lib#461` with its full URL (https://github.com/steamicc/micropython-steami-lib/issues/461): a bare `micropython-steami-lib#461` does not link from the fork.
- [ ] **Step 3: Lib PR.** Push `feat/steami-screen-spleen`, then `gh pr create --repo steamicc/micropython-steami-lib --base main`. Title: `feat(steami_screen): Draw the V1c text with the Spleen fonts.` The body holds:
  - "Closes #461";
  - what changes on 240 px and on 128 px;
  - the kept MicroPython differences;
  - the visible change (`text(s, (x, y))` 16 px tall at scale 1);
  - `text_height()` and `max_chars` 30;
  - the firmware sizes and the before/after timing table;
  - the photos;
  - the reformat warning: "This firmware moves the MicroPython filesystem: the first boot reformats it and every file stored on the board is lost. Copy your files off the board before updating.";
  - "Merge after <fork PR URL>: the release build overflows the flash without it".

  Do not merge before the fork PR is merged.
- [ ] **Step 4: Release notes** (controller, right after `release.yml` publishes the first lib release built on the new layout, vX.Y.0). The notes come from `@semantic-release/release-notes-generator`, which keeps only commit subjects, so they never carry the warning on their own:
  - `gh release view vX.Y.0 --repo steamicc/micropython-steami-lib --json body -q .body > notes.md`;
  - put the reformat warning above, in bold, at the top of `notes.md`;
  - `gh release edit vX.Y.0 --repo steamicc/micropython-steami-lib --notes-file notes.md` (immutable releases lock the tag and the assets, not the notes).

  Do not use a `BREAKING CHANGE` footer for this: it would force a major version.
