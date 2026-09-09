-- Extensions that bio_store and voice_store require before their models can be
-- migrated. Split out of analytics-init.sql so that a cluster without
-- TimescaleDB or pgvector still bootstraps cleanly and the rest of the system
-- runs — the D4 and D6 domains are simply absent, which coverage
-- renormalisation already handles correctly.
--
-- Apply with:  make db-extensions
--
-- TimescaleDB additionally requires `shared_preload_libraries = 'timescaledb'`
-- and a cluster restart; CREATE EXTENSION alone fails, because the extension
-- installs planner hooks that can only be registered at startup. local_pg.sh
-- writes that setting when it initialises the analytics cluster.
--
-- Neither extension is installed on the identity cluster. Zone 3 stores no time
-- series and no embeddings, and every preloaded library is more code running
-- inside the enclave.

\set ON_ERROR_STOP on

\connect bio_store
-- NFR-S3: hypertables on ts with 7-day chunks and space partitioning by
-- subject_token, plus continuous aggregates so trend reads never scan raw
-- samples.
CREATE EXTENSION IF NOT EXISTS timescaledb;

\connect voice_store
-- Retrieval and Phase-1 similarity work only. There is no audio and no
-- transcript in this database, and no export endpoint that reaches it.
CREATE EXTENSION IF NOT EXISTS vector;
