"""Independent reverse-unit-propagation (RUP/DRUP) refutation checker.

Checks a DRUP proof emitted by a SAT solver (e.g. Glucose via PySAT
``with_proof=True``): every added lemma must be implied by unit propagation
from the current clause database, and the empty clause must follow.  RAT
steps are NOT supported (rejected), so a passing check is a genuine
refutation certificate of the given CNF.  Written independently of the
solver; deletion steps are honoured.
"""
from __future__ import annotations


def check_rup_refutation(clauses: list[list[int]], proof: list[str], budget: int = 2_000_000,
                         honor_deletions: bool = False) -> tuple[bool, dict]:
    """Check that ``proof`` derives the empty clause by reverse unit propagation.

    Deletion steps are IGNORED by default: every clause kept in the database is either an
    input clause or a lemma already verified to be implied by the inputs, so checking
    against the larger database is still sound (deletions exist only for speed).  Solvers
    with in-processing (e.g. Glucose simplification) delete input clauses that a later lemma's
    RUP check can need; honouring those deletions makes a pure-RUP checker incomplete."""
    db: list[list[int]] = []
    alive: list[bool] = []
    watches: dict[int, list[int]] = {}
    units: list[int] = []
    index: dict[tuple, list[int]] = {}
    work = [0]

    def add(c: list[int]) -> None:
        c = list(dict.fromkeys(c))
        cid = len(db)
        db.append(c)
        alive.append(True)
        index.setdefault(tuple(sorted(c)), []).append(cid)
        if len(c) == 1:
            units.append(cid)
        for lit in c[:2]:
            watches.setdefault(lit, []).append(cid)

    def propagate(assign: dict[int, bool], trail: list[int]) -> bool:
        """Return True on conflict. Simple watched-literal propagation."""
        def val(l):
            v = assign.get(abs(l))
            if v is None:
                return None
            return v if l > 0 else not v

        # top-level units first
        for cid in units:
            if not alive[cid]:
                continue
            l = db[cid][0]
            v = val(l)
            if v is False:
                return True
            if v is None:
                assign[abs(l)] = l > 0
                trail.append(l)
        qi = 0
        while qi < len(trail):
            l = trail[qi]
            qi += 1
            falsified = -l
            wl = watches.get(falsified, [])
            keep = []
            conflict = False
            for _k, cid in enumerate(wl):
                work[0] += 1
                if work[0] > budget:
                    raise ResourceWarning("proof check budget")
                if not alive[cid]:
                    continue
                c = db[cid]
                if conflict:
                    keep.append(cid)
                    continue
                # make c[1] the falsified watch
                if c[0] == falsified and len(c) > 1:
                    c[0], c[1] = c[1], c[0]
                if val(c[0]) is True:
                    keep.append(cid)
                    continue
                moved = False
                for t in range(2, len(c)):
                    if val(c[t]) is not False:
                        c[1], c[t] = c[t], c[1]
                        watches.setdefault(c[1], []).append(cid)
                        moved = True
                        break
                if moved:
                    continue
                keep.append(cid)
                v0 = val(c[0])
                if v0 is False or len(c) == 1 and c[0] == falsified:
                    conflict = True
                elif v0 is None:
                    assign[abs(c[0])] = c[0] > 0
                    trail.append(c[0])
            watches[falsified] = keep
            if conflict:
                return True
        return False

    for c in clauses:
        if not c:
            return True, {"lemmas": 0, "note": "empty input clause"}
        add(c)
    lemmas = 0
    try:
        for line in proof:
            toks = line.split()
            if not toks:
                continue
            if toks[0] == "d":
                if not honor_deletions:
                    continue
                lits = [int(t) for t in toks[1:] if t != "0"]
                ids = index.get(tuple(sorted(dict.fromkeys(lits))), [])
                for cid in ids:
                    if alive[cid]:
                        alive[cid] = False
                        break
                continue
            lits = [int(t) for t in toks if t != "0"]
            assign: dict[int, bool] = {}
            trail: list[int] = []
            for l in lits:
                assign[abs(l)] = l < 0
                trail.append(-l)
            if not propagate(assign, trail):
                return False, {"lemmas": lemmas, "failed_lemma": line}
            lemmas += 1
            if not lits:
                return True, {"lemmas": lemmas, "work": work[0]}
            add(lits)
        # proof may end without explicit empty clause: check top-level conflict
        if propagate({}, []):
            return True, {"lemmas": lemmas, "work": work[0]}
        return False, {"lemmas": lemmas, "reason": "no refutation derived"}
    except ResourceWarning:
        return False, {"lemmas": lemmas, "reason": "budget exhausted"}
