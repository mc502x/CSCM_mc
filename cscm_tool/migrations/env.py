import logging
from logging.config import fileConfig

from alembic import context
from flask import current_app

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
# disable_existing_loggers=False: running a migration must not silence the
# application's own loggers (app/logging_config.py).
fileConfig(config.config_file_name, disable_existing_loggers=False)
logger = logging.getLogger("alembic.env")


def get_engine():
    return current_app.extensions["migrate"].db.engine


def get_engine_url():
    try:
        return get_engine().url.render_as_string(hide_password=False).replace("%", "%%")
    except AttributeError:
        return str(get_engine().url).replace("%", "%%")


# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
config.set_main_option("sqlalchemy.url", get_engine_url())
target_db = current_app.extensions["migrate"].db

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_metadata():
    if hasattr(target_db, "metadatas"):
        return target_db.metadatas[None]
    return target_db.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=get_metadata(), literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    # this callback is used to prevent an auto-migration from being generated
    # when there are no changes to the schema
    # reference: http://alembic.zzzcomputing.com/en/latest/cookbook.html
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, "autogenerate", False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info("No changes in schema detected.")

    conf_args = current_app.extensions["migrate"].configure_args
    if conf_args.get("process_revision_directives") is None:
        conf_args["process_revision_directives"] = process_revision_directives

    connectable = get_engine()

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=get_metadata(), **conf_args)

        # A table rebuild (CREATE new, copy, DROP old - the only way SQLite can widen a CHECK) must
        # run with foreign-key enforcement off, otherwise the DROP trips over the rows that other
        # tables still reference. The pragma is a no-op inside a transaction, so it is set on the
        # driver connection before one begins (SQLite's documented procedure, "Making Other Kinds
        # Of Table Schema Changes"); the check below proves nothing was left dangling.
        raw = connection.connection.dbapi_connection if _is_sqlite(connection) else None
        before = 0
        if raw is not None:
            raw.execute("PRAGMA foreign_keys = OFF")
            before = len(raw.execute("PRAGMA foreign_key_check").fetchall())
        try:
            with context.begin_transaction():
                context.run_migrations()
                if raw is not None:
                    broken = raw.execute("PRAGMA foreign_key_check").fetchall()
                    if len(broken) > before:  # violations that were already there are not ours
                        raise RuntimeError(
                            f"the migration left {len(broken) - before} new foreign key "
                            f"violation(s), first: {tuple(broken[0])}"
                        )
        finally:
            if raw is not None:
                raw.execute("PRAGMA foreign_keys = ON")


def _is_sqlite(connection) -> bool:
    return connection.dialect.name == "sqlite"


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
