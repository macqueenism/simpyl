import os
import click
import time
import datetime

from sqlalchemy import create_engine

import migrations_config as config

CURRENT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

SEPARATOR = '@'

DEFAULT_MIGRATION_FILE = """

def upgrade(connection):
    connection.execute(\"\"\" \"\"\")


def downgrade(connection):
    connection.execute(\"\"\" \"\"\")

"""
ENGINE = create_engine(config.DB_URI)


@click.group()
def migrate():
    pass


@click.command()
@click.argument('schema')
@click.argument('name')
def create(schema, name):
    timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y%m%d%H%M%S')
    filename = f'{timestamp}{SEPARATOR}{schema}{SEPARATOR}{name}.py'
    click.echo(f'Creating new migration file {filename}')
    os_path = os.path.join(CURRENT_DIRECTORY, 'versions', filename)
    with open(os_path, 'w') as f:
        f.write(DEFAULT_MIGRATION_FILE)


@click.command()
@click.argument('schema')
@click.option('--all', 'run_all', flag_value='all')
def upgrade(schema, run_all):
    if run_all or not schema_exists(schema) or not migrations_table_exists(schema):
        click.echo(f'running all migrations for {schema}')
        run_migrations(schema, migration_files_for_schema(schema))

    last_migration = get_last_run_migration(schema)
    click.echo(f'Current version of {schema} is {last_migration}')
    run_migrations(schema, get_migration_files_for_schema_older_than(schema, last_migration))


@click.command()
@click.argument('schema')
@click.option('--all', 'run_all', flag_value='all')
@click.option('--to', 'timestamp', help='downgrade to a certain timestamp')
def downgrade(schema, run_all, timestamp):
    if not schema_exists(schema):
        click.echo('schema not found')
        return
    if run_all:
        files = migration_files_for_schema(schema)
        run_migrations(schema, list(reversed(files)), upgrade=False)
    if timestamp:
        click.echo(f'running downgrade on all migrations for {schema} older than {timestamp}')
        files = get_migration_files_for_schema_older_than(schema, timestamp)
        run_migrations(schema, list(reversed(files)), upgrade=False)
    if not run_all or timestamp:
        click.echo('please use the --all or --to flag to specify the type of downgrade')


migrate.add_command(create)
migrate.add_command(upgrade)
migrate.add_command(downgrade)


def get_migration_files_for_schema_older_than(schema, timestamp):
    return [m for m in migration_files_for_schema(schema) if get_timestamp_from_filename(m) > timestamp]


def get_last_run_migration(schema):
    return get_single_row_result(ENGINE.execute(f"""
        SELECT timestamp FROM {schema}.migrations
        ORDER BY timestamp DESC
        LIMIT 1;
    """))


def run_migrations(schema, migrations_to_run, upgrade=True):
    mode = 'upgrade' if upgrade else 'downgrade'
    mode_sign = '+' if upgrade else '-'
    for migration_file in migrations_to_run:
        migration_module = import_migration_from_filename(migration_file)
        click.echo(f' {mode_sign}  {migration_file}')
        getattr(migration_module, mode)(ENGINE)
        update_migrations_table(migration_file, upgrade)

    click.echo(f'completed {mode} for {schema}')


def get_migration_filename_parts(migration_filename):
    filename_parts = str.split(migration_filename, SEPARATOR)
    return filename_parts[0], filename_parts[1], filename_parts[2][:-3]


def get_timestamp_from_filename(migration_filename):
    timestamp, _, _ = get_migration_filename_parts(migration_filename)
    return timestamp


def update_migrations_table(migration_filename, upgrade=True):
    timestamp, schema, name = get_migration_filename_parts(migration_filename)
    if upgrade:
        ENGINE.execute(f"""
            INSERT INTO {schema}.migrations VALUES ('{timestamp}', '{name}');
        """)
    else:
        if schema_exists(schema):
            ENGINE.execute(f"""
                DELETE FROM {schema}.migrations
                WHERE
                    {schema}.migrations.timestamp = '{timestamp}' AND
                    {schema}.migrations.name = '{name}';
            """)


def import_migration_from_filename(filename):
    if '.py' in filename:
        filename = filename[:-3]
    migrations_module = __import__(f'versions.{filename}')
    migration = getattr(migrations_module, filename)
    return migration


def migration_files_for_schema(schema):
    for _, _, files in os.walk(f'{CURRENT_DIRECTORY}/versions'):
        return [
            filename
            for filename in files
            if f'{SEPARATOR}{schema}{SEPARATOR}' in filename
        ]


def schema_exists(schema):
    result = ENGINE.execute(f"""
        SELECT EXISTS(
            SELECT 1
            FROM information_schema.schemata
            WHERE
                schema_name = '{schema}'
        );
    """)
    return get_single_row_result(result)


def migrations_table_exists(schema):
    result = ENGINE.execute(f"""
        SELECT EXISTS(
            SELECT 1
            FROM information_schema.tables
            WHERE
                table_schema = '{schema}' AND
                table_name = 'migrations'
        );
    """)
    return get_single_row_result(result)


def get_single_row_result(result):
    for r in result:
        return r[0]

if __name__ == '__main__':
    migrate()
