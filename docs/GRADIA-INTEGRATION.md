# Gradia integration: use the product without publishing it

This repository is an external consumer of Gradia. It must never import the
private server package or copy private implementation code. Integration occurs
through versioned HTTP contracts and exported evidence bundles.

## Identity separation

The complete workflow uses three identities:

1. a human author creates the synthetic scenario edition;
2. a different qualified human reviews that exact edition digest; and
3. a project-scoped service account submits runner evidence and deterministic
   recomputation requests.

The browser cannot mint runner evidence. A service account cannot freeze the
human measurement construct or approve its own scenario.

## Safe conformance check

```bash
gradia-universe gradia-contract --base-url "$GRADIA_BASE_URL"
```

This read-only check proves:

- live health is 200;
- live OpenAPI contains the required scenario, occurrence, operator-event and
  trajectory-materialization paths; and
- anonymous project scenario access is 401.

It does not claim an authenticated end-to-end run.

## Authenticated synthetic workflow

The release harness will drive these stages against a dedicated synthetic
project—not a customer project:

1. create/freeze the spec and environment through Gradia's ordinary factory;
2. attach the one synthetic task and five canonical scenario editions;
3. approve editions with the separate reviewer identity;
4. execute matched control/treatment cells with exact model/scaffold/seed pins;
5. collect occurrence and scenario-control evidence;
6. upload the canonical trajectory evidence asset;
7. create the evidence edition as a project-scoped service account;
8. materialize and recompute the human-frozen detectors;
9. export a public-redacted bundle; and
10. replay the public bundle locally and require the digests to agree.

## Governed Explorer release

The canonical bundle and its authorization are separate immutable artifacts.
This avoids a circular claim where inserting “approved” into a reviewed bundle
changes the bytes after approval.

1. Register `release/public-universe-bundle.json` in Gradia's Research Release
   workflow with artifact kind `public_universe_bundle` and the SHA-256 of its
   exact file bytes (including its one canonical trailing newline).
2. Attach exactly one certificate evidence reference plus the rights basis,
   contributors and intended audience.
3. Complete contributor and any required legal/redaction reviews against that
   digest.
4. Complete every evidence-backed release check and authorize the exact public
   destination `/universes/<slug>`.
5. In the decision history, download the signed Explorer receipt. It is served
   by
   `GET /v1/research-release-decisions/{decision_id}/public-universe-release-receipt`.
6. Place the unchanged bundle and receipt together under the release slug. The
   Explorer recomputes the bundle body digest, denominators and references,
   hashes the exact file bytes against the signed `artifact_sha256`, verifies
   the detached Ed25519 signature, and requires its public key to be deployment
   trusted.

The endpoint only projects an already-clear human decision. It cannot turn a
hold, failed checklist, missing approval, non-Universe artifact, ambiguous
destination, missing certificate or tampered row into a release receipt.

## Credential boundary

Credentials are environment-only and purpose-scoped. The client must never
print the `Authorization` header, serialize a token, accept it on a command line
or publish a raw server response before redaction. CI public replay remains
keyless. Authenticated production evidence is generated only in a protected
job with a synthetic project allowlist and a hard budget cap.

## Current status

The keyless replay and read-only live contract client are implemented. Full
authenticated author/reviewer/runner orchestration remains gated on a dedicated
synthetic Gradia project, two human identities and production promotion of the
AA3 trajectory endpoints. That boundary is intentional and should not be
described as complete before exact live receipts exist.
