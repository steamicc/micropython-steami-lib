# V1c screen (GC9A01) in MicroPython — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One MicroPython program draws on the STeaMi screen whatever the release: SSD1327 128×128 on V1a/V1b, GC9A01 240×240 on V1c.

**Architecture:**
- A `gc9a01` driver keeps a 16-colour GS4 frame and sends it as RGB565 in strips.
- `steami_screen` gets a `GC9A01Display` adapter and the agreed scaling rule: 128 px units ×15/8, and glyph/stroke factor k = 1 or 2.
- `steami.Screen` picks the adapter for the detected release, with E30/E31 messages.
- The firmware freezes `gc9a01` in place of `senml`. If that is not enough, the filesystem moves up 16 KB.

**Tech Stack:** MicroPython 1.29 (`framebuf`, `machine.SPI`), STM32WB55RG, firmware fork `steamicc/micropython-steami` (branch `stm32-steami-rev1d-final`). Tests are mock tests on CPython with pytest (`make test-mock` runs `pytest tests/ -k mock`).

**Spec:** `docs/superpowers/specs/2026-11-26-steami-screen-gc9a01-design.md`

**Arduino reference** (read only):
- `git -C /home/nedjar/sandbox/arduino-steami-lib show origin/main:<path>`
- driver: `lib/gc9a01/src/SteamiGC9A01.cpp`
- layout: `lib/steami_board/src/SteamiScreen.h`, `SteamiDisplay.cpp`
- design: `docs/superpowers/specs/2026-11-25-steami-display-design.md` (section 5.8)
- screen tests and goldens: `tests/native/test_steami_screen/`

## Global Constraints

- **V1c pins:** SPI1 (`SPI(1)`, "SPIINT"): SCK PA1, MOSI PB5. Plus `Pin("CS_DISPLAY")` (PD0), `Pin("DATA_COMMAND_DISPLAY")` (PB4) and `Pin("RST_DISPLAY")` (PA12). No backlight pin.
- **SPI and frame:**
  - SPI mode 0 at 16 MHz.
  - GC9A01 colour data is RGB565, high byte first.
  - Each `spi.write()` must send at most 65 535 bytes.
- **Frame:** `framebuf.GS4_HMSB`, 240 × 240 / 2 = 28 800 bytes. Each pixel is a palette index 0–15.
- **Palette** (index: RGB), exactly:
  - 0 BLACK (0,0,0)
  - 1 GRID_DARK (51,51,51)
  - 2 DARK (102,102,102)
  - 3 GRAY (153,153,153)
  - 4 LIGHT (187,187,187)
  - 5 WHITE (255,255,255)
  - 6 GREEN (119,255,119)
  - 7 RED (255,85,85)
  - 8 BLUE (85,85,255)
  - 9 YELLOW (255,255,85)
  - 10 CYAN (85,255,255)
  - 11 MAGENTA (255,85,255)
  - 12 ORANGE (255,165,0)
  - 13 DARK_GREEN (0,128,0)
  - 14 DARK_RED (128,0,0)
  - 15 DARK_BLUE (0,0,128)

  Any other RGB tuple maps to the nearest entry (squared RGB distance). Legacy int colours keep the meaning `colors.py` gives them (grey4).
- **Init sequence** (`kInitSequence`, including MADCTL for the V1c orientation, COLMOD 0x05 and INVON) and the reset timing are copied from `SteamiGC9A01.cpp`. Panel RAM is cleared and sent before DISPON.
- **Scaling:**
  - k = (width + 64) // 128, so 1 at 128 px and 2 at 240 px;
  - layout uses 128 px units scaled by width/128;
  - glyphs (text and faces) and strokes use factor k;
  - when k = 2, follow the Arduino design section 5.8, except where it marks a MicroPython difference.
- **API units (as Arduino):**
  - primitives (`line`, `circle`, `rect`, `pixel`) and `text(x, y)` take real pixels;
  - `text(at=...)` and widget text are scaled by k;
  - `y_offset` is in 128 px units, and `arc_width` in real pixels;
  - `width`, `height`, `center` and `radius` report real pixels.
- **Round screen:** when k = 2 only, widgets keep their text inside the circle (Arduino truncation, title-row floor and cap, menu limited to the circle).
- **SSD1327 output must stay pixel-identical** (k = 1, layout unchanged).
- **Messages:** E30 means "unknown board, no screen" and E31 means "not enough RAM". Texts are copied from Arduino `SteamiDisplay.cpp`, adapted like the other `steami` messages (Python class names, no `#define`). E31 detail: `not enough RAM for the screen (N bytes in one block). Call begin() on the Screen first in the program.`
- **Firmware:**
  - drop `senml` and freeze `gc9a01`; no LTO, and no change to the RAM ISR list;
  - fallback if it does not fit: `FLASH_FS` moves from 0x08080000 to 0x08084000 (still 256 KB), and the application flash grows by 16 KB.
- **Repo conventions** (CONTRIBUTING.md):
  - layout `lib/<pkg>/{manifest.py, README.md, <pkg>/, examples/}`;
  - `const()` in `const.py`, snake_case, `ruff check` clean, `ruff format` on new files;
  - no `print()` except in `steami/board.py`;
  - test files contain "mock".
- **Commits:**
  - Conventional Commits, subject ends with a period, header ≤ 78 characters;
  - scopes `gc9a01`, `steami_screen`, `steami`, `tests`, `docs`, `tooling`;
  - no attribution lines, never "[skip ci]".

## Review Focus

1. **A title or text longer than the circle on a V1c** (e.g. a 20-character title) is truncated inside the round screen, with no exception. Tested in Task 5.
2. **A colour outside the palette** (e.g. (200, 100, 50)), or a legacy int grey, maps to a palette entry with no exception. Tested in Task 3.
3. **Drawing partly or fully outside the panel** (negative coordinates, x > 240) is clipped with no exception, and `show()` still sends exactly one full frame. Tested in Task 2.
4. **A `Screen()` created when the heap cannot give 28 800 bytes in one block** reports E31. Its drawing calls do nothing, and the program keeps running. Tested in Task 6.
5. **`show()` called before any drawing, or many times in a row**, sends a black frame or the same frame, and does not resend the init sequence. Tested in Task 2.

---

### Task 1: Freeze today's SSD1327 output as a golden reference

**Files:**
- Create: `tests/test_steami_screen_golden_mock.py`
- Create: `tests/golden/steami_screen_128.json`

**Interfaces:**
- Produces:
  - `record_calls(widget_name) -> list` replays one scripted call of each `Screen` widget (title, value, subtitle, bar, gauge, graph, menu, compass, watch, each face, text with each `at`, line, circle, rect, pixel, clear) on the recording `FakeDisplay` of `tests/scenarios/steami_screen.yaml`, 128×128 with `fill_rect`/`rect`;
  - the JSON file `{widget_name: [call tuples]}`.

- [ ] **Step 1: Write the golden test.** `test_mock_ssd1327_output_unchanged[<widget>]` compares `record_calls(widget)` with the JSON entry. The script, with its fixed arguments, lives in the test module.
- [ ] **Step 2: Generate the JSON from the current `main` code** with a one-off helper flag (`STEAMI_GOLDEN_WRITE=1`), then check it in.
- [ ] **Step 3: Run.** `python3 -m pytest tests/test_steami_screen_golden_mock.py -q` → PASS on unchanged code.
- [ ] **Step 4: Commit.** `test(steami_screen): Record the 128 px drawing calls as a golden reference.`

### Task 2: The `gc9a01` driver

**Files:**
- Create: `lib/gc9a01/manifest.py`, `lib/gc9a01/README.md`, `lib/gc9a01/gc9a01/__init__.py`, `const.py`, `device.py`, `lib/gc9a01/examples/palette.py`
- Modify: `tests/fake_machine/framebuf_stub.py` (add `fill_rect`, `rect`, `blit` with a palette and RGB565 support, if the driver uses them)
- Create: `tests/fake_machine/spi.py` (`FakeSPI` recording `write()` buffers, `init()` arguments and the D/C level at each write)
- Test: `tests/test_gc9a01_mock.py`
- Keep: `lib/gc9a01/.not-frozen` (removed in Task 9)

**Interfaces:**
- Produces:
  - `GC9A01(spi, dc, cs, rst=None, width=240, height=240)`. The constructor allocates the frame and touches no pin or bus.
  - `init()`: reset, init sequence, clear, DISPON.
  - `fill(i)`, `pixel(x, y, i=None)`, `fill_rect(x, y, w, h, i)`, `rect(x, y, w, h, i)`, `line(x1, y1, x2, y2, i)`, `text(s, x, y, i)`, `blit(fb, x, y, key=-1)`.
  - `show()` sends the whole frame.
  - `const.PALETTE`: tuple of 16 RGB tuples, in the order of the global constraints.
  - `const.PALETTE_RGB565`: the 16 RGB565 words, byte-swapped for the panel if the conversion needs it.

- [ ] **Step 1: Write the failing tests:**
  - `init()` writes `kInitSequence` in Arduino order, with D/C low for commands and high for data. It ends with clear, then DISPON.
  - `show()` sends CASET (0..239), RASET (0..239), RAMWR, then 115 200 bytes of RGB565, high byte first. Palette index 5 (WHITE) becomes `0xFF 0xFF`, and index 7 (RED (255,85,85)) becomes the RGB565 of (255,85,85), high byte first.
  - Every `write()` is ≤ 65 535 bytes.
  - Review Focus 3: drawing at x = -10 or x = 300 raises nothing, and `show()` still sends 115 200 bytes.
  - Review Focus 5: `show()` with nothing drawn sends 115 200 zero bytes. Two `show()` calls send the init sequence only once (from `init()`).
- [ ] **Step 2: Run them, expect failures.** `python3 -m pytest tests/test_gc9a01_mock.py -q` → FAIL (no module).
- [ ] **Step 3: Implement `device.py` and `const.py`.** `show()` converts in strips through a small reused RGB565 strip buffer. `framebuf.blit` with a palette FrameBuffer is the fast route on MicroPython; the strip height is the builder's call. The SPI is set up once per `show()`, mode 0 at 16 MHz, and CS is held low for the frame. Write the README (wiring, palette, memory: 28 800 B frame plus the strip) and the example.
- [ ] **Step 4: Run.** The test file passes, `make test-mock` shows no regression, and `ruff check` is clean.
- [ ] **Step 5: Commit.** `feat(gc9a01): Add a 16-colour GC9A01 driver for the V1c screen.`

### Task 3: `GC9A01Display` adapter in `steami_screen`

**Files:**
- Create: `lib/steami_screen/steami_screen/gc9a01.py`
- Modify: `lib/steami_screen/steami_screen/__init__.py` (export `GC9A01Display`), `lib/steami_screen/README.md`
- Test: `tests/test_steami_screen_gc9a01_mock.py`

**Interfaces:**
- Consumes: `GC9A01` (Task 2).
- Produces:
  - `GC9A01Display(raw)` with `width = height = 240`;
  - `fill`, `pixel`, `text`, `line`, `fill_rect`, `rect` and `show`, all taking RGB tuples or legacy ints;
  - `draw_scaled_text(text, x, y, color, scale)`;
  - `rgb_to_index(color) -> int`, a module function with a small cache.

- [ ] **Step 1: Write the failing tests:**
  - each named colour maps to its exact index;
  - Review Focus 2: (200, 100, 50) maps to its nearest entry by squared distance (assert the computed index), and the int 15 maps to WHITE's index;
  - `draw_scaled_text("A", 0, 0, WHITE, 2)` sets a 16×16 block of pixels matching the 8×8 glyph doubled (compare to the glyph bits);
  - every method forwards to the raw driver.
- [ ] **Step 2: Run them, expect failures.**
- [ ] **Step 3: Implement the adapter.** Scaled text draws each glyph through an 8×8 MONO_HLSB buffer, as `SSD1327Display` does, with `scale × scale` `fill_rect` blocks.
- [ ] **Step 4: Run.** The file passes, the golden test of Task 1 still passes, and `make test-mock` shows no regression.
- [ ] **Step 5: Commit.** `feat(steami_screen): Add the GC9A01Display adapter.` (refs #368)

### Task 4: Firmware fit check (local only)

**Files:** none in this repo. Work in the controller's firmware clone. Never push in this task.

- [ ] **Step 1:** In the firmware clone (branch from `stm32-steami-rev1d-final`), remove `require("senml")` from `ports/stm32/boards/STEAM32_WB55RG/manifest.py` and add `require("gc9a01", library="micropython-steami-lib")`. Point `lib/micropython-steami-lib` at this worktree for the build only.
- [ ] **Step 2:** Run `make BOARD=STEAM32_WB55RG MICROPY_USE_COMPILER_PLUGIN=none`. Record `arm-none-eabi-size` and the margin against 524 288 bytes, and add a reserve estimate for Tasks 5–6: today's `steami_screen` device code grows, and `steami/screen.py` is new.
- [ ] **Step 3:** If the margin left after that reserve is below 2 KB, apply the fallback:
  - in the board's linker script (or a board-specific copy), `FLASH_APP` and `FLASH` grow by 16 KB and `FLASH_FS` starts at 0x08084000 with 256 KB;
  - check the storage settings derived from `_micropy_hw_internal_flash_storage_*`;
  - rebuild, then check with `nm` that the RAM ISR functions (`LPUART1_IRQHandler`, `uart_irq_handler`, `SysTick_Handler`, `dma_idle_handler`, `FLASH_PageErase`, `FLASH_WaitForLastOperation`) are still at 0x2000xxxx.
- [ ] **Step 4:** Write the numbers and the decision in the task report. The fork PR comes in Task 9.

### Task 5: Scaling rule and round-screen fitting in `steami_screen.Screen`

**Files:**
- Modify: `lib/steami_screen/steami_screen/device.py`, `const.py`
- Test: `tests/test_steami_screen_scaling_mock.py`, and the golden test of Task 1 (must stay green)

**Interfaces:**
- Produces:
  - `Screen.k` (property);
  - `Screen.u(v) -> int` (128-unit to real pixels);
  - widget signatures unchanged.

- [ ] **Step 1: Write the failing tests** with a recording 240×240 fake display:
  - `k` is 1 at 128 and 2 at 240;
  - for each widget, the positions and sizes at 240 equal the Arduino design section 5.8 values. Take the expected numbers from Arduino `tests/native/test_steami_screen` and its goldens wherever they exist; otherwise compute them from the section 5.8 formulas, with a comment citing the formula;
  - text from `title`, `value` and `text(at=...)` is drawn with scale k;
  - Review Focus 1: `title("A very long title text")` at 240 draws only characters whose glyph boxes lie inside the circle at the title row, and raises nothing.
- [ ] **Step 2: Run them, expect failures.** The golden test (Task 1) still passes.
- [ ] **Step 3: Implement the rule and the k = 2 fitting rules in `device.py`.** The 128 px code path must be unchanged.
- [ ] **Step 4: Run.** The scaling tests pass, and the golden test stays green.
- [ ] **Step 5: Commit.** `feat(steami_screen): Scale widgets to the 240 px round screen.`

### Task 6: `steami.Screen` and `Steami.display()`

**Files:**
- Create: `lib/steami/steami/screen.py`
- Modify: `lib/steami/steami/const.py`, `board.py`, `__init__.py`, `README.md`
- Test: `tests/test_steami_screen_class_mock.py`

**Interfaces:**
- Consumes: `GC9A01`, `GC9A01Display`, `SSD1327Display` and `ssd1327.WS_OLED_128X128_SPI`.
- Produces, in `const.py`:
  - `Function.SCREEN = "screen"`;
  - `Chip.SSD1327 = "SSD1327"` and `Chip.GC9A01 = "GC9A01"`;
  - a screen route: V1a/V1b → SSD1327, V1c → GC9A01, unknown → none;
  - `E_SCREEN_UNKNOWN_BOARD = "E30"` and `E_NO_MEMORY = "E31"`.
- Produces, elsewhere:
  - `Steami.display()` returns the shared adapter or `None`;
  - `class Screen`, with the common form (`begin`, `is_available`, `status`, `error`, `chip`) and the full `steami_screen.Screen` drawing API;
  - `Status.NO_MEMORY`;
  - `from steami import Screen` loads lazily.

- [ ] **Step 1: Write the failing tests:**
  - on a V1c (forced): `Screen().chip() == "GC9A01"` and `width == 240`;
  - on V1a/V1b: `"SSD1327"` and 128;
  - on an unknown release: `begin() is False`, E30 once, and drawing calls raise nothing;
  - Review Focus 4: a frame allocation that raises `MemoryError` gives `Status.NO_MEMORY`, E31 with the exact text, drawing calls that do nothing, and no exception;
  - `Steami.display()` returns the same adapter object twice;
  - creating `Screen()` touches no pin and no bus.
- [ ] **Step 2: Run them, expect failures.**
- [ ] **Step 3: Implement it.**
  - The shared adapter is built in `board.py` on first `display()`. Catch `MemoryError` only around the frame allocation; this is the exception to the T12 rule that `MemoryError` propagates.
  - `Screen` reaches the `steami_screen.Screen` API by subclassing or forwarding (builder's call).
  - Update the `steami` README: the screen section, the routing table, and E30/E31.
- [ ] **Step 4: Run.** `make test-mock` and `ruff check` are clean.
- [ ] **Step 5: Commit.** `feat(steami): Add Screen, the board screen for every release.`

### Task 7: Examples on `steami.Screen`

**Files:**
- Modify: the eight `lib/steami_screen/examples/*.py`
- Test: `tests/test_examples.py` (existing)

- [ ] **Step 1:** Switch each example to `from steami import Screen` / `screen = Screen()`. Adjust hard-coded sizes to real-pixel units, so that the examples look right on 128 and 240 (e.g. the 56×10 blanking rectangle of `gauge_demo.py` becomes computed from `screen.k`).
- [ ] **Step 2: Run.** `python3 -m pytest tests/test_examples.py -q` passes, and `ruff check` is clean.
- [ ] **Step 3: Commit.** `docs(steami_screen): Run the examples on every release with steami.Screen.`

### Task 8: Validation on the V1c

**Files:**
- Create: `tests/scenarios/steami_screen_v1c.yaml` (hardware only)

- [ ] **Step 1: Write the scenario.** It draws each widget through `steami.Screen()` on the V1c, calls `show()`, and checks that nothing raises and that `chip() == "GC9A01"`.
- [ ] **Step 2: Get the board.** The controller grants the slot. Flash the release firmware, and copy `gc9a01`, the changed `steami_screen` and `steami` to the filesystem root (frozen copies shadow `/flash/lib`).
- [ ] **Step 3: Run the scenario and gather the evidence:**
  - run it with `--port /dev/ttyACM0`;
  - photograph the screen with the webcam for the title, gauge, compass and face widgets (`ffmpeg` on `/dev/video4`, with 60 warm-up frames);
  - measure the `show()` time;
  - measure `gc.mem_free()` with the BLE beacon sample running plus a `Screen()` (the anti-goal: they must coexist).
- [ ] **Step 4: Put battery_status back, release the board, commit the scenario.** `test(steami_screen): Add the V1c screen hardware scenario.`

### Task 9: Freeze `gc9a01` in the firmware (outward: the controller asks the user first)

- [ ] **Step 1:** Open a fork PR with the Task 4 manifest change: `senml` removed, `gc9a01` added, and the filesystem move if Task 4 needed it, with its warning about the reformat. The commit carries `Signed-off-by` (the upstream rule) and is checked with `tools/verifygitlog.py`.
- [ ] **Step 2:** Once it is merged, open a lib PR that removes `lib/gc9a01/.not-frozen`, as a `fix` commit. Check that `tests/test_frozen_manifest.py` passes.
- [ ] **Step 3:** After the release, check that its firmware contains `gc9a01/device.py`, and tell wiki-steami-30 the version.
