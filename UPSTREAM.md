# Upstream provenance

**Upstream:** CausalBool, https://github.com/albertoHdzE/CausalBool, pinned revision `376a11ddf25063d49dc8f6cd98bbb3baf2e1cc43` (owner: Alberto Hernández Espinosa; pre-sprint work).

## Licensing and redistribution

The reviewed upstream root has **no top-level LICENSE**. Nested third-party licenses (e.g. `doc/Tesis-UNAM/LICENSE`) do not license the monorepo. Therefore **no upstream code is copied, vendored or relicensed here.** CausalGuard contains an original *compatible implementation* of the index-family method and imports upstream only at test time from a user-supplied checkout:

- `scripts/fetch_upstream.sh <dir>` clones the pinned revision; set `CAUSALBOOL_ROOT=<dir>`.
- `src/causalguard/upstream_adapter.py` verifies the revision and the SHA-256 of every pinned file before importing.
- `tests/test_upstream_parity.py` (marker `upstream`) is skipped, and reported as skipped, without a checkout.

Unresolved question for the owner (does not block this release): whether to add an explicit license to the upstream repository. Nothing here depends on the answer.

## Upstream owners consulted (read, not copied)

| File | SHA-256 | Used for |
|---|---|---|
| `GOVERNANCE/GLOSSARY.md` | c3d04021…b3e | definitions: connected inputs, free coordinates, sumandos = fillings of a schema's own don't-cares (incl. connected inputs); Rule 110 counterexample |
| `GOVERNANCE/ORDERING.md` | 808c2810…07 | LSB-first canonical order (node i = bit i); MSB/LSB transport hazard |
| `GOVERNANCE/DESCRIPTION_LENGTHS.md` | d8619dd1…7 | five description-length variants A–E; the in-degree field requirement for decodability |
| `index-deconvolution/src/causalbool.py` | 856cd0f2…100 | forward method; parity of repertoires (LUT/TRUE/FALSE gates) |
| `index-deconvolution/src/deconvolution.py` | 4e49c064…bb | `minimal_dnf` (Quine–McCluskey + greedy cover); parity of covers |
| `src/description_lengths.py` | 9edabfa4…a4e | Variant E `schema_normal_form_length` (a floating log2 *proxy*, not an archive length) |
| `papers/method/manuscript_formal/method_paper.tex` | 04ea352c…366 | Dec(L,S) operator, gate-family one-set formulae, Rule 110 remark |

## Measured parity (tests/test_upstream_parity.py, 2026-11-09)

- Repertoires: 150 random networks (n ≤ 7, in-degree ≤ 3) — identical next-state rows for every state.
- Horizon convention: upstream `evolve_network(net, x, steps)` returns `steps` rows (= steps−1 updates); CausalGuard `horizon` counts updates. Pinned by a test.
- Covers: 400 random local tables (k ≤ 6): both covers reproduce the on-set exactly; our exact minimum cover uses the same number of clauses on 318 tables and fewer on 82 (upstream uses a greedy cover). Rule 110: both 3 clauses.

## Description-length relation

Upstream Variant E (`D_schema`) is a real-valued log2 *formula*. CausalGuard's `index` codec is an executable bitstring with integer field widths, a polarity bit and archive framing (docs/CODEC.md); its lengths are not Variant E values and are never reported under that name. BDM/CTM, entropy and upstream Variants A–E are not used.
