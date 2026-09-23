# Setup configuration architecture

core/setup_config.py owns setup-page discovery, environment-tree parsing, type coercion, sanitisation, and environment precedence.

Variables use PAGE__OBJECT__FIELD. Named-provider fields can use deeper namespaces.

Environment values always win over browser/setup-form values for fields controlled by the environment. The frontend receives only a sanitized tree describing which fields are environment-controlled.

SETUP_MODE controls the interactive setup surface. false, off, disabled, and 0 disable the page; environment configuration continues to work.

Each setup page should register a stable namespace, consume overrides immediately before validation and persistence, expose only controlled field names to the frontend, and document every variable.

Tests should cover tree parsing, boolean/integer coercion, recursive merge, environment-over-form precedence, sanitisation, and setup-mode parsing.

The deployment backup system is a consumer of the setup configuration architecture, not a replacement for it. Backup encryption and environment precedence are separate security boundaries.
