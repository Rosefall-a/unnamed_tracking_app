# Setup configuration architecture

src/backend/src/core/setup_config.py owns setup-page discovery and environment
precedence. Runtime configuration in core/config.py deliberately remains separate.

## Environment tree

A variable is interpreted as:

    PAGE__OBJECT__FIELD
    |    |       |
    |    |       +-- field
    |    +---------- named object
    +--------------- setup page

For example:

    OIDC__AUTHENTIK__CLIENT_ID
    OIDC__AUTHENTIK__SECURITY__REQUIRE_EMAIL_VERIFIED

The parser creates a nested tree and coerces true/false to booleans and numeric
values to integers.

## Adding a setup page

Register it in default_setup_configuration():

1. Choose a stable uppercase page key.
2. Give it a user-facing label and description.
3. Add the corresponding frontend page/model.
4. Read overrides through SetupConfiguration.overrides_for().
5. Apply the overrides immediately before validation and persistence.
6. Document the variables under /docs.

Do not add ad-hoc os.getenv() calls to individual setup routes. Centralising the
tree makes precedence predictable and lets the setup UI explain which values are
environment-controlled.

## Adding a provider field

For a named provider, use PAGE__PROVIDER__FIELD. Nested namespaces are supported,
so security settings can use:

    OIDC__AUTHENTIK__SECURITY__REQUIRE_EMAIL_VERIFIED=false

Environment values always win over form values. This is important for immutable or
centrally managed deployments.

## Setup mode

SETUP_MODE is a runtime switch for the interactive surface. false, off, disabled,
and 0 disable the interactive page. It should not be used as an alternative to
defining required environment values.

## Testing

Add unit tests for tree parsing, boolean/integer coercion, recursive merge,
environment-over-form precedence, and setup mode parsing. Keep those tests
independent of Vue and database state so new setup pages can be validated cheaply.
