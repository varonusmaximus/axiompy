---
name: object
description: Cloud object and blob storage — S3, GCS, Azure. Use when editing axiompy.io.object.
---

# Object storage domain (axiompy)

Shared packages load separately. This skill is **blob/object-store-only** guidance.

## Scope

`axiompy/io/object.py`.

## APIs

- Object storage factory — enum dispatch across S3, GCS, Azure Blob.
- `create_mock()` for unit tests.

## Sidecars (auto-included)

`blob-stores.md` — keys, streaming, provider errors.

## Pointers

- `axiompy/io/README.md` — Object Storage section.
- Install: `pip install "axiompy[storage]"` or `"axiompy[io]"`.
