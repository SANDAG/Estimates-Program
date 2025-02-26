## Setup

Clone the repository and ensure an installation of [Miniconda/Anaconda](https://docs.conda.io/projects/miniconda/en/latest/) exists. Use the **environment.yml** file in the root directory of the project to [create the Python virtual environment](https://docs.conda.io/projects/conda/en/4.6.1/user-guide/tasks/manage-environments.html#creating-an-environment-from-an-environment-yml-file) needed to run the project.

Set the configuration file **config.yml** parameters specific to the run in the project root directory.

### Configuration File Settings

```yaml
run:
  enabled: true  # enable standard run mode
  start_year: 2020  # first year to run
  end_year: 2023  # last year to run
  version: 0.0.0-dev  # software version
  comments: >-  # run-specific comments
    This is an example run using comments
    that span a multi-line string.

debug:
  enabled: false  # enable debug mode
  run_id: null  # existing production database id to use
  year: null  # year to run
```

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