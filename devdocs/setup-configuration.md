# Setup configuration architecture

core/setup_config.py owns setup-page discovery, environment-tree parsing, type coercion, sanitisation, and environment precedence. Runtime Pydantic settings remain separate.

Variables use PAGE__OBJECT__FIELD. Named-provider fields can use deeper namespaces.

Environment values always win over browser/setup-form values for fields controlled by the environment.

SETUP_MODE controls only the interactive setup surface. false, off, disabled, and 0 disable the page; environment configuration continues to work.

Each setup page should register a stable namespace, consume overrides immediately before validation/persistence, expose only controlled field names to the frontend, and document its variables.

Tests should cover tree parsing, boolean/integer coercion, recursive merge, environment-over-form precedence, sanitisation, and setup-mode parsing.
