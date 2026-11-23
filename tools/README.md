# Tools

The scripts that produced [`data/names.tsv`](../data/names.tsv). They are research tools: run from a terminal, one step at a time, with a person reading the output between steps.

**You need your own copy of the game.** Nothing from it is included here, and the tools never write into the game folder or into this repository (except `export_site.py`, which writes the published results to `data/`). Extracted files and everything derived from them go to a work folder outside the repo.

## Setup

| Variable | Meaning | Default |
| --- | --- | --- |
| `GTA6_GAME_DIR` | folder that holds the game archives and executable | none, required by the tools that read the game |
| `NAME_RECOVERY_WORK` | work folder for extracted and derived data | `../<repo name>-work` next to this repo |
| `PERCYSTAR_NAMES_DIR` | folder of name lists, one name per line in `.txt` files | `%LOCALAPPDATA%/PercyStar/names` |
| `NAME_RECOVERY_CRACK_EXE` | the built cracker | `<work>/bin/crack` |
| `ANTHROPIC_API_KEY` | credential for `judge_api.py` | none; never stored by the tools |

Python 3.10 or newer. Only `judge_api.py` needs a package (`pip install anthropic`). The cracker is one Rust file without dependencies:

```
rustc -C opt-level=3 -C target-cpu=native tools/crack/crack.rs -o <work>/bin/crack.exe
```

The public name lists are not redistributed here. Clone them into `<work>/lists/<owner>_<repo>` (for example `alexguirre_rage-parser-dumps`, `dexyfex_CodeWalker`); `match_lists.py` reads whichever are present.

## Steps

1. **Collect the hashes**
   - `exe_tables.py` reads the parser tables of the executable: every struct and enum with the hash, type, offset and default of each member.
   - `extract_psin.py common.rpf script.rpf data.rpf` extracts the metadata files from the small archives; `schema_scan.py --all levels.rpf packs.rpf` walks the large ones and keeps only the schema.
   - `build_targets.py --scan --exe` writes the table of every hashed name. `build_index.py` records which struct owns which field, with a sample or default value each: the context a judge reads.
2. **Names that exist as text**
   - `match_lists.py` collects every identifier of the public lists; `scan_match.py --save` keeps those that hash to a wanted name.
   - `harvest_all.py` (which runs `harvest.py` per piece) tests identifier-like text found anywhere in the game files; `harvest_accept.py` separates real names from the chance matches such a large scan produces.
3. **Search**
   - `prep.py` learns, per kind of name, which words open, continue and end the known names. `run_all.py <tag>` runs the cracker per kind and keeps hits only below the score where random decoy hashes start to match.
   - `sprep.py` and `srun.py` search the missing fields of one struct with the words of its known fields; `erun.py` searches the missing values of one enum behind the prefix its known values share. `job.py`, `topics.py` and `run_topics.py` do the same with a vocabulary written for one topic.
   - Where a job has few wanted names, as these narrow searches do, the cracker does not try the last word at all: it runs each wanted hash backwards through every last word once and looks up each shorter combination. The hits and decoy scores are the same as trying every combination; a typical job runs about 30 times faster.
4. **Judge**
   - `pool.py <tag> <lines per file> <cracker output> ...` writes judge files: each unresolved name with its best candidates, type, owner struct, value, the type it refers to and the known sibling names.
   - `judge_api.py <folder> <prefix>` sends each file to a Claude model and writes the accepted names to a `.out` file next to it, with token use and cost per file. The instructions it gives are in the script; [`briefs/`](briefs/) holds the same instructions for use with an agent.
   - `merge.py [--save]` checks every accepted name (it must hash to its target and must have been offered) and adds it to the accepted set. `next_round.py <round tag> <judge tag>` relearns the word lists from the larger known set and repeats steps 3 and 4.
   - `rounds.py <first cycle number>` runs steps 3 and 4 unattended, cycle after cycle, until a cycle adds few names or the judging cost reaches a cap. A narrow search's own pick is left out when a judge has already turned that candidate down.
5. **Measure and publish**
   - `holdout_judged.py` and `holdout_struct.py` hide known names, search for them like unknown ones and count right and wrong answers.
   - `export_site.py` writes `data/names.tsv` and `data/progress.json`; `progress_page.py` serves a live progress page on localhost while jobs run.

`common.py` holds the paths and the hash function, `psin_format.py` a minimal reader for the metadata file format, `struct_context.py` prints one struct with everything known about it.

## The hash

Struct, field and enum value names are hashed with Jenkins one-at-a-time (joaat) over the name exactly as written, upper and lower case kept. Values stored in the data (model names and the like) use the same hash over the lower-cased text.
