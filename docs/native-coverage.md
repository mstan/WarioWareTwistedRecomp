# Native coverage experiments

These tools target **WarioWare: Twisted! USA revision 0**, SHA-1
`f0102d0d6f7596fe853d5d0a94682718278e083a`. Supply your own ROM and matching
retail BIOS, regenerate the cartridge **and BIOS** code, then build the desktop
executable. BIOS generation uses `gba_recompile --bios PATH --config
gbarecomp/bios/gba_bios.toml --out gbarecomp/src/runtime/generated_bios`.
The experiments use the existing BIOS boot HLE policy.

`tools/coverage_session.py` starts a muted, hidden, command-driven test process
with runtime recompilation disabled. Every session gets a new output directory
and disposable save. Its `Session` class exposes frame stepping, active-low GBA
buttons, memory capture and save states. Normal launches keep their normal
audio settings; this helper sets the dummy audio driver only in its child.

```powershell
python tools/coverage_session.py --output build-coverage/boot-native --frames 900
python tools/coverage_session.py --output build-coverage/boot-reference --frames 900 --interpreter
```

The raw engine counters describe *fallback dispatch*, so forced interpreter
runs can misleadingly print `FULLY_STATIC`. The helper labels its reference
checkpoints `FORCED_INTERPRETER`; those counters never establish native
coverage. Native coverage requires zero dispatch misses and zero interpreted
instructions, with healing disabled. A successful build alone establishes
neither coverage nor execution correctness.

## Jump to individual microgames

Work entirely in ignored `build-coverage/` directories. Keep the phone's save
and normal installation separate. Snapshots contain ROM-derived data and
private save information: **do not commit or publish them**.

1. Reach Modes, choose Spindex, select a character, then enter its individual
   microgame selector. Start with gyro test offset `0` after calibration.
   `Session.checkpoint()` saves a `.state` file at any paused checkpoint.
2. If entries are locked, apply `unlock` to a **copy** of an earlier Modes or
   Spindex character-selector snapshot, then enter the individual selector.
   Unlocking an already-rendered wheel requires leaving and re-entering it.
3. Use `capture` to press A and snapshot the queued normal launch, then
   `prepare` to create one audited RAM-only cheat for each of the 223 IDs.

```powershell
python tools/microgame_coverage.py unlock --snapshot build-coverage/modes.state --output build-coverage/unlocked.state
# Navigate from unlocked.state to a microgame selector; capture selector.state.
python tools/microgame_coverage.py capture --snapshot build-coverage/selector.state --output build-coverage/queued
python tools/microgame_coverage.py prepare --snapshot build-coverage/queued/queued.state --output build-coverage/cases
python tools/microgame_coverage.py run --cases build-coverage/cases --output build-coverage/reference --backend interpreter
python tools/microgame_coverage.py run --cases build-coverage/cases --output build-coverage/native --backend native
python tools/microgame_coverage.py compare --reference build-coverage/reference --candidate build-coverage/native --output build-coverage/comparison.json
```

`--executable PATH` selects a retained baseline executable. `--bios PATH`
selects the BIOS (default `gbarecomp/bios/gba_bios.bin`). `run` also accepts
`--frames`, `--limit`, `--gyro` (`0`, a signed constant, or `sweep`), `--port`,
`--jobs` (default 4), `--resume`, and `--require-static`. Resume checks the
executable, config and case-manifest hashes plus the selected inputs. The
default is 600 frames per game with a deterministic
gyro triangle wave and alternating 60-frame neutral/A-button periods. Each
case starts a fresh process because gyro/GPIO external state is not currently
serialized. Parallel jobs use consecutive ports starting at `--port`; separate
runs need disjoint port ranges.

The bot exercises game logic; it does **not** solve every game, guarantee a win,
or cover all difficulty levels, random variations, souvenirs or Story paths.
Compare memory and screenshots as well as counters. This is differential
testing against the framework's interpreter, not an independent hardware oracle.
Retain the earlier native executable and run it with `--backend native
--executable PATH` too: differences already present between the old native
backend and the forced interpreter must be distinguished from new regressions.

## Evidence behind the cheats and metadata

- The world map at `0x08930188` and descriptors reached through `0x08930A48`
  supply ten Spindex lists containing exactly 223 distinct game IDs.
  `0x08016F44` selects a descriptor; `0x08017334` reads its ID list.
- The catalog at `0x0892A1D8` uses 24-byte records, indexed by game ID at
  `0x080173B8`. The first word points to four callback/argument pairs. The task
  dispatcher at `0x0800B310` consumes callbacks at offsets `0/8/16/24`.
  `game.toml` annotates these actual records with `[[jump_table]]`, including
  leaf callbacks that conservative compiler-prologue discovery misses.
- `0x080149B8` stores a delayed menu callback at local object `+0x290` and its
  argument at `+0x294`. `capture` requires the queued callback `0x08017089`.
  `prepare` changes only its game-ID argument and the category/slot bytes at
  `0x03003BA2/0x03003BA3`; the original loader initializes the selected game.
- Unlocking preserves all other record bits: the 16 world-record flag bytes
  at EWRAM `0x24 + 8*i` gain bits `0/1`; the 0x600 sparse record flag bytes at
  `0xA4` gain bits `0/2`. The latter are the seen/cleared getters and setters
  at `0x080008A4/0x080008C8` and `0x0800091C/0x08000940`. These are **record
  slots**, not 1536 distinct microgames. Scores and global flags are preserved.
- Snapshot patching checks the ROM identity and complete v2 section framing,
  permits only EWRAM/IWRAM writes, and refuses in-place modification. Each
  output has an adjacent JSON audit of source/output hashes and before/after
  bytes. CPU, ROM and device state are unchanged by the cheat itself.

The additional RAM-code mappings cover the IRQ dispatcher, two decompressors,
division helper and three audio images. The two overlapping stack placements
of the SRAM reader use per-entry `source_addr` mappings, backed by the observed
halfword-copy writer at `0x0813005A`. Cartridge generation retains portable
generated C++ under the existing framework interface.

## Recorded desktop result (2026-10-17)

The [machine-readable report](../tests/native-coverage-2026-10-17.json)
records 223 microgames at 600 frames each, with verified loaded callback
records, **zero dispatch misses, zero interpreted instructions and zero runtime
recompilation**. The original corpus used 3,885,180,166 interpreted instructions
on the same cases. Cold boot, Story playback and Spindex navigation also pass
their sampled routes without interpreter fallback.

All five memory regions and screenshots match the original native build for
221 cases. The other two (IDs 186 and 308) match the forced interpreter exactly.
205 cases match the interpreter in full; 18 native/interpreter differences
already present in the original native corpus remain unqualified. These
results establish coverage for the sampled routes, not universal backend
equivalence or every possible playthrough.

## Platform limit

Android currently still forces the interpreter in `src/main.cpp`. Desktop
coverage qualification does not establish Android execution correctness or
improve the installed Android release's CPU backend. Remove that restriction
only after native Android gameplay has been qualified separately.
The expanded generated corpus also passes an Android ARM64 build check.
