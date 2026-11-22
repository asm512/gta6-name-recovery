# GTA VI name recovery

Recovering the original names behind the 32-bit hashes in GTA VI's metadata files (Xbox build 1.0.2.1), for modding tools.

**Site:** https://asm512.github.io/gta6-name-recovery/ (progress, method, and a searchable list of every recovered name)

## Where it stands

As of 2026-11-22: **11,625 of 21,492 hashed names (54.1%)** recovered. These are the struct, field and enum names in the `PSIN` metadata of `common.rpf`, `script.rpf` and `data.rpf`, not the whole game. The live numbers are in [`data/progress.json`](data/progress.json); every name with its hash, kind and method is in [`data/names.tsv`](data/names.tsv).

Names come from public name lists of earlier RAGE games, the game's own text, automatic word combinations, a probability-ranked cracker, and candidates judged by a language model.

## Caveats

- Names from name lists or game text are reliable (about 1 chance collision in 200,000 per name).
- Automatically built names carry a measured chance rate of a few percent.
- The error rate of model-judged names has **not been measured yet** (estimated at a few percent; a held-out test is planned). Each name's method is listed so you can tell them apart.
- 100% is not reachable from 32-bit hashes alone; the realistic ceiling without the game executable is estimated at 60 to 70%.

## Contents and legal

This repository holds no game files, extracted assets or keys: only hashes, names, text and the code of the site. It is independent interoperability research, not affiliated with Rockstar Games or Take-Two Interactive. Name lists from [alexguirre/rage-parser-dumps](https://github.com/alexguirre/rage-parser-dumps) (MIT) and other community projects are credited on the site.

The site is plain HTML, CSS and JavaScript served from the repository root; to view it locally, run `python -m http.server` in this folder and open http://localhost:8000.

Licence: MIT.
