# Why phases?

## The problem phases solve

An Odoo module migration has roughly these kinds of work:

1. **Mechanical**: rename a tag, bump a version, fix a decorator. Boring, high-volume, easy to verify.
2. **Semantic**: understand what a method does and adapt it to new APIs. Slow, needs judgment.
3. **Data-shape**: write SQL / ORM to migrate production data. Irreversible if wrong.
4. **Verification**: prove the whole thing works. Takes a DB copy and time.

If you ask an AI to do all four at once, in one chat, the output is nearly always wrong — not because the AI can't do any individual step, but because:

- Context fills up and the model loses track of what's been decided.
- Mechanical fixes and semantic decisions get mixed and reviewing a PR becomes a nightmare.
- No gate catches when the plan drifted from what the module actually needs.
- "I'll add tests later" → tests never happen.

## What phases buy you

**Small context per phase.** The AI only sees what it needs for the step it's on. Fresh context per Phase 3 task keeps quality uniform from task 1 to task 50.

**Human gates at the expensive inflection points.** The cost of catching a wrong decision grows exponentially with how late you catch it. Reviewing `research.md` takes 10 minutes; re-doing Phase 3 because research was wrong takes days. The gates exist at exactly the points where a bad decision compounds.

**Mechanical work is quarantined.** By running `odoo-module-migrator` first and committing alone, the hand-edit diff is reviewable. Without that separation, the mechanical churn drowns the semantic changes and you can't tell which is which in review.

**Tests are never "later".** They're scheduled in Phase 2 as explicit tasks before the code they protect is touched. This is the one rule that, if you break it, the whole recipe falls over.

**Verification is its own phase, not an afterthought.** Phase 4 is the only phase where a real production data copy gets touched. Separating it makes the blast radius visible.

## What phases don't solve

- A module with zero tests is still a module with zero tests. Phases force you to add them, but writing the right tests still needs human judgement.
- An AI that doesn't know Odoo internals will produce wrong plans faster. Give it access to OpenUpgrade and the version deltas doc or it will flail.
- Dependencies between modules. If module A depends on module B and you migrate A first, you're stuck. The recipe handles one module — dependency ordering is on you.
