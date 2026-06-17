# AAL Examples (v1.3)

Compact syntax, domain registry, inject-on-edit. See [AAL-v1.3.0.md](./AAL-v1.3.0.md) for the full spec.

---

## 1. File-level — security module

Place `# @!code-review` at the **top of the file** (file default). Function-level annotations override when needed (§2).

```python
# @!code-review

import bcrypt

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()
```

**On edit:** hook resolves `security` → reads `.cursor/skills/security/*.md` → injects into agent context → write proceeds.

---

## 2. Function-level — mixed concerns in one file

```python
# @!general

def healthcheck() -> str:
    return "ok"

# @!code-review
def hash_password(plain: str) -> str:
    ...

# @!design-patterns
def archive_old_sessions(conn, before: date) -> int:
    ...
```

Editing `hash_password` injects **security** skills only. Renaming the function to `hash_user_password` does **not** remove the annotation — it stays on the line above the function.

---

## 3. Multi-domain

```python
# @!code-review,storage

def rotate_keys_and_purge(conn) -> None:
    ...
```

Inject loads skills from **both** domains (all files listed under each in `domains.yaml`).

---

## 4. TypeScript

```typescript
// @!code-review

export function getProfile(id: string) { ... }

// @!code-review
export function verifyToken(token: string): Claims {
  ...
}
```

---

## 5. Go

```go
// @!design-patterns

func ListOrders(ctx context.Context, userID string) ([]Order, error) {
    ...
}

// @!design-patterns
func MigrateSchema(ctx context.Context, db *sql.DB) error {
    ...
}
```

---

## 6. Directory default (optional)

**`src/auth/.aal-dir.yaml`**

```yaml
domain: security
```

**`src/auth/token.py`** — no file-level annotation needed:

```python
def hash_password(plain: str) -> str:
    ...
```

Inherits `@!code-review` from directory config.

---

## 7. Registry example

**`.cursor/domains.yaml`**

```yaml
domains:
  security:
    summary: "Auth, crypto, secrets"
    skills:
      - .cursor/skills/security/core.md
      - .cursor/skills/security/jwt.md
  storage:
    skills:
      - .cursor/skills/storage/sql.md
```

---

## 8. Expected CLI output

```bash
$ aal explain src/auth/token.py --line 12
```

```text
AAL profile: src/auth/token.py (line 12)
  effective: @!code-review (line 11)
  enforcement: inject
  skills:
    - .cursor/skills/security/core.md
    - .cursor/skills/security/jwt.md
```

```bash
$ aal impact security
```

```text
Files referencing domain 'security':
  - src/auth/token.py
  - src/auth/session.py
```

---

## 9. Skill override (company rules)

Bundled `.cursor/skills/security/core.md` is replaced on `axiompy-skills upgrade`. Company rules live in:

**`.cursor/skills/security/core.override.md`**

```markdown
---
aal: skill-override
domain: security
target: core.md
mode: append
---

## Supersedes
### Encryption
Use company KMS only — no local key files.

## Adds
- All JWT keys must come from Vault.
```

Commit the override file. `axiompy-skills upgrade` preserves it; inject merges bundled + override.

---

## 10. Bootstrap and CI flow

```bash
pip install axiompy
aal install --hooks --setup-pre-commit
echo "axiompy==1.3.0" >> requirements-dev.txt
git add .cursor/ .cursor/ .github/ requirements-dev.txt
git commit -m "chore: bootstrap AAL"

aal init src/auth/token.py --domain code-review
aal verify-domains --strict
```

CI (every PR):

```bash
pip install -r requirements-dev.txt
aal doctor --strict
aal verify-domains --strict
```

No freeze. No hashes. Commit `.cursor/` and `.cursor/` — CI validates the checked-out tree.

---

## Appendix A — Advanced guards (optional)

Not required for most repos. See spec §3.

```python
# @!design-patterns,load=none

# @!guard when=keyword:migration then=read:storage
def run_migration(conn) -> None:
    ...
```

---

## Appendix B — Long headers (`scan_entire_file`)

Default `scan_entire_file: true` in `.cursor/aal.yaml` scans the whole file — a license block plus many imports does not hide annotations:

```python
# Copyright ...
# ... 40 lines of imports ...

# @!code-review
def hash_password(plain: str) -> str:
    ...
```

Function-level `# @!code-review` above `hash_password` is always found. Only if `scan_entire_file: false` can a **file-level** annotation placed after line 50 be missed — `verify-domains --strict` should warn.
