"""S4: algorithmic models for verifiable AI reasoning (iteration 4, development).

Modules (one owner each):
  analytic   -- the formal paper's analytic index-set calculus (bands, parity/weight classes, gate one-sets,
                LSB/MSB orderings and the bit-reversal involution, Dec, support-local evaluation of KNOWN mechanisms)
  hcode      -- CGH-1: fully charged hierarchical/analytic mechanism code (ordered templates, modules, shared rules)
  mechspace  -- support-schema representation of the complete compatible-mechanism set V(D) (no materialization)
  workspace  -- one semantic API over three backends (B generic SAT/explicit, C flat index, D index-set calculus)
  checking   -- propose / check / counterexample / revise / commit gate bound to claim+assumptions
  tasks      -- S4 world families, evidence designs, claims, leakage audits
  evaluator  -- the only holder of hidden mechanisms; reference verdicts and scoring
  prior      -- codec-induced model averaging (offline secondary)
  offline    -- family/cost map, fixed-request replay, S4-B active-investigation prototype, known-mechanism panel
  pilot      -- bounded local LLM pilot harness
"""
