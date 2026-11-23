# GTA VI name recovery

Recovering the original names behind the 32-bit hashes in GTA VI's metadata (Xbox build 1.0.2.1), for modding tools.

**Site:** https://asm512.github.io/gta6-name-recovery/ (progress, method, and a searchable list of every recovered name)

## Where it stands

As of 2026-11-23: **48,681 of 116,739 hashed names (41.7%)** recovered. The total is every struct, field and enum name the game's metadata parser knows, read from the tables in the executable and from the metadata files in the game's archives.

| Kind | Recovered | Total |
| --- | --- | --- |
| Fields | 28,484 | 52,070 |
| Enum values | 15,242 | 46,101 |
| Structs | 4,103 | 15,070 |
| Enums | 852 | 3,498 |

Of the 25,781 names that occur in the data files scanned so far, 14,078 (54.6%) are recovered. The live numbers are in [`data/progress.json`](data/progress.json); every name with its hash, kind and method is in [`data/names.tsv`](data/names.tsv).

## How

1. **The list of hashes.** The executable holds a table of every struct and enum with the hash, type and default value of each field. The names were stripped when the game was built.
2. **Names that exist as text.** Public name lists from earlier RAGE games, and text in the game's own files, are hashed and matched.
3. **Search.** A cracker recombines the words of known names, most probable first, and measures chance matches with random decoy hashes. Narrower searches use the known field names of one struct, or the prefix the known values of one enum share.
4. **Judging.** Where a search leaves several candidates, a language model (Claude Opus 5.5, Claude Fable 5.2) reads them with the type, owner struct, default value and sibling names, and accepts only names that fit.

## How reliable

Each name carries its method, so you can filter.

- **name list, game text** (33,461 names): the text exists elsewhere. About one in 4,000 is expected to be a chance collision.
- **cracked** (10,468): accepted automatically where decoys show few chance matches. About 3 to 4% are expected to be chance matches.
- **judged** (4,752): picked by a language model. In holdout tests on hidden known names the judges accepted 364 names and got 363 right; scaled to the real judging that suggests 1 to 2% wrong, with a wide margin.

100% is not reachable from 32-bit hashes alone: a long or unusual name fits many texts, and nothing says which one is right.

## Tools

The scripts that did the work are in [`tools/`](tools/), with the steps described in [`tools/README.md`](tools/README.md). They need your own copy of the game and keep everything they extract in a folder outside this repository.

## Disclaimer

This repository holds no game files, executables, extracted assets or keys: only hashes, the names recovered for them, and text and code written for this project. The tools read a copy of the game that you supply; nothing from it is distributed here, and nothing derived from it should be added in a pull request.

This is independent interoperability research for modding tools. It is not affiliated with, endorsed by or connected to Rockstar Games or Take-Two Interactive. Grand Theft Auto and related names are trademarks of Take-Two Interactive Software; they are used here only to say what the work is about. Recovered names are best guesses of varying reliability and everything is provided as is, without warranty.

Name lists from [alexguirre/rage-parser-dumps](https://github.com/alexguirre/rage-parser-dumps) (MIT) and other community projects are credited on the site.

The site is plain HTML, CSS and JavaScript served from the repository root; to view it locally, run `python -m http.server` in this folder and open http://localhost:8000.

Licence: MIT.
