from alembic import context
from cloud.config import Settings
from cloud.db import metadata,engine_for
settings=Settings.env();settings.validate()
if context.is_offline_mode():
    context.configure(url=settings.database_url,target_metadata=metadata,literal_binds=True)
    with context.begin_transaction(): context.run_migrations()
else:
    with engine_for(settings).connect() as connection:
        context.configure(connection=connection,target_metadata=metadata)
        with context.begin_transaction(): context.run_migrations()
