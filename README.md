### Configuration of Private Data in secrets.yml
In order to avoid exposing certain data to the public this repository uses a secrets file to store sensitive configurations in addition to a standard configuration file. This file is stored in the root directory of the repository as `secrets.yml` and is included in the `.gitignore` intentionally to avoid it ever being committed to the repository.

The `secrets.yml` should mirror the following structure.

```yaml
sql:
  estimates:
    server: <SqlInstanceName>  # SQL instance containing estimates database
    database: <SqlDatabaseName>  # database within SQL instance containing SQL build objects
  gis:
    server: <SqlInstanceName>  # SQL instance containing GIS database
    database: <SqlDatabaseName>  # database within instance containing GIS datasets (GQ/LUDU)
```