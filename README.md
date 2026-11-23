# GTA VI name recovery

Recovering the original names behind the 32-bit hashes in GTA VI's metadata files (Xbox build 1.0.2.1), for modding tools.

**Site:** https://asm512.github.io/gta6-name-recovery/ (progress, method, and a searchable list of every recovered name)

## Where it stands

As of 2026-11-22: **13,839 of 26,286 hashed names (52.6%)** recovered. These are the struct, field and enum names in the `PSIN` metadata of `common.rpf`, `script.rpf`, `data.rpf`, `levels.rpf` and `packs.rpf`. The last two were added on 2026-11-22 and brought 4,794 names nobody had looked for yet, which is why the percentage dipped from 54.1% while the count rose by 2,214. The live numbers are in [`data/progress.json`](data/progress.json); every name with its hash, kind and method is in [`data/names.tsv`](data/names.tsv).

Names come from public name lists of earlier RAGE games, the game's own text, automatic word combinations, a probability-ranked cracker, and candidates judged by a language model.

## Caveats

- Names from name lists or game text are reliable (about 1 chance collision in 200,000 per name).
- Automatically built names carry a measured chance rate of a few percent.
- Model-judged names were tested by hiding 1,500 known names and running them through the same cracker and judges: of 196 names the judges accepted, 195 were right and 1 was wrong. Scaled to the lines judged in the real rounds this suggests about 2% of the judged names are wrong, but one wrong pick is thin evidence: anything from well under 1% to about 11% is consistent with the test. The hidden names come from older games and may be easier than the unknown ones. Each name's method is listed so you can tell them apart.
- 100% is not reachable from 32-bit hashes alone; the realistic ceiling without the game executable is estimated at 60 to 70%.

## Tools

The scripts that did the work are in [`tools/`](tools/), with the steps described in [`tools/README.md`](tools/README.md). They need your own copy of the game and keep everything they extract in a folder outside this repository.

## Disclaimer

This repository holds no game files, extracted assets, executables or keys: only hashes, the names recovered for them, and text and code written for this project. The tools read a copy of the game that you supply; nothing from it is distributed here, and nothing derived from it should be added in a pull request.

This is independent interoperability research for modding tools. It is not affiliated with, endorsed by or connected to Rockstar Games or Take-Two Interactive. Grand Theft Auto and related names are trademarks of Take-Two Interactive Software; they are used here only to say what the work is about. Recovered names are best guesses of varying reliability (see Caveats) and everything is provided as is, without warranty.

Name lists from [alexguirre/rage-parser-dumps](https://github.com/alexguirre/rage-parser-dumps) (MIT) and other community projects are credited on the site.

The site is plain HTML, CSS and JavaScript served from the repository root; to view it locally, run `python -m http.server` in this folder and open http://localhost:8000.

Licence: MIT.
