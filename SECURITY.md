# Security and disclosure boundary

This repository contains only synthetic people, organizations, policies and
records. It does not contain customer data, customer facts, Gradia
credentials, private Gradia server code, model-provider keys or production
traces.

The authenticated integration accepts credentials only through process
environment variables. It never prints or writes them. Public result bundles
must pass `gradia-universe verify-public` before release; that command refuses
known secret shapes, absolute local paths and non-synthetic provenance.

Live-panel response bytes are retained only inside the Git-ignored
`results/local/<run-id>/private-provider-responses/` directory with local-only
file permissions. Treat that directory as sensitive research material: it may
contain provider metadata and exact model output. It is not a public artifact,
must not be uploaded automatically and requires a separate rights/disclosure
review before any projection leaves the machine.

The SHA-256 chain in this sample is tamper-evident, not an identity signature.
Release identity should be supplied by the hosting platform's signed release
attestation. Do not describe a hash-only receipt as cryptographically signed.

Report a vulnerability privately to security@gradiahq.com. Do not open a public
issue containing credentials, private records or an exploitable production
path.
