REVOKE ALL ON DATABASE manobal_core FROM PUBLIC;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'core_app') THEN
        CREATE ROLE core_app
            LOGIN
            PASSWORD 'core_app_dev_only'
            NOSUPERUSER
            NOCREATEDB
            NOCREATEROLE
            NOINHERIT;
    END IF;
END
$$;

GRANT CONNECT ON DATABASE manobal_core TO core_app;
GRANT USAGE ON SCHEMA public TO core_app;
ALTER DEFAULT PRIVILEGES FOR ROLE core_owner IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO core_app;
ALTER DEFAULT PRIVILEGES FOR ROLE core_owner IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO core_app;
ALTER DEFAULT PRIVILEGES FOR ROLE core_owner IN SCHEMA public
    GRANT EXECUTE ON FUNCTIONS TO core_app;
