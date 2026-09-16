REVOKE ALL ON DATABASE manobal_vault FROM PUBLIC;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vault_app') THEN
        CREATE ROLE vault_app
            LOGIN
            PASSWORD 'vault_app_dev_only'
            NOSUPERUSER
            NOCREATEDB
            NOCREATEROLE
            NOINHERIT;
    END IF;
END
$$;

GRANT CONNECT ON DATABASE manobal_vault TO vault_app;
GRANT USAGE ON SCHEMA public TO vault_app;
ALTER DEFAULT PRIVILEGES FOR ROLE vault_owner IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO vault_app;
ALTER DEFAULT PRIVILEGES FOR ROLE vault_owner IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO vault_app;
ALTER DEFAULT PRIVILEGES FOR ROLE vault_owner IN SCHEMA public
    GRANT EXECUTE ON FUNCTIONS TO vault_app;
