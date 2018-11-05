#### I know it's been done but..

# Simpyl: Simple Python Migrations

A basic migration tool for postgres and python 3. It's 'simple' because you write the SQL, no magic and very little help. Enjoy.

## Setup

Clone this repository and run the following:

```bash
$ virtualenv -p python3 virtualenv
$ virtualenv/bin/activate && pip install -r requirements.txt
```

Then set the `DB_URI` value in `migrations_config.py`.
Other configurable values in the `migrations_config.py` include:
- `SEPARATOR`: change the character used to separate the parts of migration file names, defaults to '-'


## Usage

### Create migration files

The tool requires a specific format of migration file so use the create function to add one for the specific schema

```bash
$ python migrate.py create <schema_name> <name_of_migration>
```

**The first migration for a given schema must:**
1. Create the schema
2. Create a migration table

For example:

```python
def upgrade(connection):
    connection.execute("""
        CREATE SCHEMA users;
        CREATE TABLE users.migrations (
            timestamp varchar(14),
            name varchar(245)
        );
    """)


def downgrade(connection):
    connection.execute("""
        DROP TABLE IF EXISTS users.migrations;
        DROP SCHEMA IF EXISTS users;
    """)
```

### Running an upgrade on a schema

Upgrade the schema to the most current version found in the migrations folder.
This will run all the migrations for that schema in order, adding the version to the
migrations table in that schema's database.

```bash
$ python migrate.py upgrade <schema>
```


Upgrade the schema by running all the migrations from start to finish for a given
schema. This is useful when a schema does not exist for example.

```bash
$ python migrate.py upgrade <schema> --all
```


### Running all migration files for all schemas

Run all the migrations in your migrations directory if you're setting up
a fresh database from scratch. Saves you having to run migrations for each of
your schemas. Note this does not take into account migrations that have already
been run.

```bash
$ python migrate.py upgrade-all
```


### Running a downgrade

Downgrade the current migration version to a specific version.
Note this uses only the time stamp part of the migration filename.

```bash
$ python migrate.py downgrade <schema> --to <timestamp>
```

Downgrade all for a schema:
```bash
$ python migrate.py downgrade <schema> --all
```

## Running postgres

There's a docker-compose file with a postgres service if you want to
try out the migration tool on a dummy db.

```
$ docker-compose up
```

and `ctrl+c` when you're done.

