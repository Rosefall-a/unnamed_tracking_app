# OIDC setup architecture

OIDC uses the declarative setup configuration tree from PR #192.

Each named provider owns its credentials, enabled state, login visibility, ordering, autostart policy, presentation, user matching, new-user policy, and verified-email policy.

Do not collapse named providers into one global configuration.

The require_verified_email policy defaults to false. The callback only rejects an unverified identity when that provider explicitly enables the policy.

OIDC login creates the same server-side session type used by password login. Session credentials are hashed at rest and logout revokes the matching database session.

Environment-controlled provider fields are applied before validation and save and remain authoritative over setup-form values.

Regression coverage should include multiple providers, presentation and ordering, user matching, new-user policy, verified-email policy, environment overrides, and session logout/revocation.
