# AAL (Agent Annotation Language) in AxiomPy

Documentation for domain annotations, inject-on-edit hooks, and CI validation.

| Document | Purpose |
|----------|---------|
| [HLD.md](./HLD.md) | Executive narrative, onboarding journey, FAQs |
| [spec.md](./spec.md) | Normative grammar, placement, CLI contracts |
| [deployment.md](./deployment.md) | Install, CI, upgrade runbooks |
| [examples.md](./examples.md) | Annotated code examples |
| [implementation.md](./implementation.md) | Implementation backlog and phases |
| [axiompy-mapping.md](./axiompy-mapping.md) | Spec placeholders → AxiomPy names |
| [design-review.md](./design-review.md) | Design grill Q&A (archive) |

## Quick start

```bash
pip install axiompy
axiompy-skills install --project --hooks
axiompy-skills bootstrap suggest
axiompy-skills bootstrap apply --level file --apply
axiompy-skills verify-domains --strict
```

Branch: `varona/aal-v1.3-merge`
