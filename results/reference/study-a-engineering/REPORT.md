# Study A engineering projection-sensitivity check

**Boundary:** Synthetic paired projection-sensitivity engineering check only; not a confirmatory detector result, model result, prevalence estimate, or novelty claim.

Parents: **5**  
Isolated synthetic forks: **26**  
Confirmatory status: **NOT_YET_RUN**

| Evidence policy | Forks | Projection sensitive | Projection insensitive | Faithful-parent changes |
|---|---:|---:|---:|---:|
| `T` | 26 | 0 | 26 | 0 |
| `L+T` | 26 | 12 | 14 | 0 |
| `M+T` | 26 | 7 | 19 | 0 |
| `P+T*` | 26 | 15 | 11 | 0 |
| `W` | 26 | 26 | 0 | 0 |

`P+T*` is an engineering causal-evidence proxy, not a faithful Proof of Execution reproduction. These counts show only whether a paired change is present in a projection; they do not show that a blinded detector found it.

## Mutation-family matrix

| Family | Forks | T | L+T | M+T | P+T* | W |
|---|---:|---:|---:|---:|---:|---:|
| M1 | 4 | 0 | 0 | 0 | 4 | 4 |
| M2 | 5 | 0 | 5 | 0 | 0 | 5 |
| M3 | 5 | 0 | 5 | 0 | 0 | 5 |
| M4 | 1 | 0 | 1 | 1 | 1 | 1 |
| M5 | 1 | 0 | 1 | 1 | 1 | 1 |
| M6 | 1 | 0 | 0 | 0 | 0 | 1 |
| M7 | 4 | 0 | 0 | 0 | 4 | 4 |
| M8 | 5 | 0 | 0 | 5 | 5 | 5 |

## Gates that remain

- faithful strongest-baseline reproduction or justified equivalent
- independent mutation-isolation audit
- public preregistration with frozen power and stopping rules
- detector implementations blinded to mutation labels
- two-reviewer human study
- E2B and AgentENV runtime conformance

Report SHA-256: `f891ac53e2212051fc8287194f9a380adb214f6ed52113e3e7d1f04ee80ceb34`
