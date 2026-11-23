# Tools

The scripts that produced [`data/names.tsv`](../data/names.tsv). They are research tools: run from a terminal, one step at a time, with a person reading the output between steps.

**You need your own copy of the game.** Nothing from it is included here, and the tools never write into the game folder or into this repository (except `export_site.py`, which writes the published results to `data/`). Extracted files and everything derived from them go to a work folder outside the repo.

## Setup

| Variable | Meaning | Default |
| --- | --- | --- |
| `GTA6_GAME_DIR` | folder that holds the game archives (`common.rpf`, `data.rpf`, ...) | none, required by the scan tools |
| `NAME_RECOVERY_WORK` | work folder for extracted and derived data | `../<repo name>-work` next to this repo |
| `PERCYSTAR_NAMES_DIR` | folder of name lists, one name per line in `.txt` files | `%LOCALAPPDATA%/PercyStar/names` |
| `NAME_RECOVERY_CRACK_EXE` | the built cracker | `<work>/bin/crack` |

Python 3.10 or newer, no packages. The cracker is one Rust file without dependencies:

```
rustc -C opt-level=3 -C target-cpu=native tools/crack/crack.rs -o <work>/bin/crack.exe
```

The public name lists are not redistributed here. Clone them into `<work>/lists/<owner>_<repo>` (for example `alexguirre_rage-parser-dumps`, `dexyfex_CodeWalker`); `match_lists.py` reads whichever are present.

## Steps

1. **Collect the hashes**
   - `extract_psin.py common.rpf script.rpf data.rpf` extracts every PSIN metadata file from the small archives.
   - `schema_scan.py --all levels.rpf packs.rpf` walks the large archives and keeps only the schema; `schema_scan.py --report` prints the totals.
   - `build_targets.py [--scan]` writes the table of every hashed struct, field and enum name.
   - `build_index.py` records which struct owns which field, with one sample value each (the context a judge reads).
2. **Names that exist as text**
   - `match_lists.py` tests every identifier of the public lists; `scan_match.py` does the same for the hashes the scan added.
   - `harvest_all.py` (which runs `harvest.py` per piece) tests identifier-like text found anywhere in the game files; `harvest_accept.py` then separates real names from the chance matches such a large scan produces.
3. **Crack**
   - `prep.py` learns, per kind of name, which words open, continue and end the known names.
   - `run_all.py <tag>` runs the cracker per kind and keeps hits only below the score where random decoy hashes start to match.
   - `job.py`, `topics.py`, `run_topics.py` do the same with a vocabulary written for one topic; `sprep.py` and `srun.py` with the words of one struct.
4. **Judge**
   - `pool.py <tag> <lines per file> <cracker output> ...` writes judge files: each unresolved name with its best candidates, type, owner struct, a sample value and the known sibling names.
   - A language model reads each file with the instructions in [`briefs/`](briefs/) and writes the names it accepts to a `.out` file next to it.
   - `merge.py [--save]` checks every accepted name (it must hash to its target and must have been offered) and adds it to the accepted set.
   - `next_round.py <round tag> <judge tag>` relearns the word lists from the larger known set and repeats steps 3 and 4.
5. **Measure and publish**
   - `holdout_struct.py` and `holdout_judged.py` hide known names, search for them like unknown ones and count right and wrong answers.
   - `export_site.py` writes `data/names.tsv` and `data/progress.json`; `progress_page.py` serves a live progress page on localhost while jobs run.

`common.py` holds the paths and the hash function, `psin_format.py` a minimal reader for the file format, `struct_context.py` prints one struct with everything known about it.

## The hash

Struct, field and enum value names are hashed with Jenkins one-at-a-time (joaat) over the name exactly as written, upper and lower case kept. Values stored in the data (model names and the like) use the same hash over the lower-cased text.
