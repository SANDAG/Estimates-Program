CREATE SCHEMA [metadata]
GO

CREATE TABLE [metadata].[run] (
    [run_id] INT NOT NULL,
    [mgra] nvarchar(10) NOT NULL,
    [start_year] INT NOT NULL,
    [end_year] INT NOT NULL,
    [user] NVARCHAR(100) NOT NULL, 
    [date] DATETIME NOT NULL,
    [version] NVARCHAR(50) NOT NULL,
    [comments] NVARCHAR(200) NULL,
    [loaded] BIT NOT NULL,
    CONSTRAINT [pk_metadata_run] PRIMARY KEY ([run_id])
) WITH (DATA_COMPRESSION = PAGE)
GO


CREATE SCHEMA [inputs]
GO

CREATE TABLE [inputs].[mgra] (
    [run_id] INT NOT NULL,
    [mgra] INT NOT NULL,
    [2020_census_tract] NVARCHAR(11) NOT NULL,
    [cities_2020] NVARCHAR(15) NOT NULL,
    [shape] geometry NOT NULL,
    CONSTRAINT [pk_inputs_mgra] PRIMARY KEY ([run_id], [mgra]),
    CONSTRAINT [fk_inputs_mgra_run_id] FOREIGN KEY ([run_id]) REFERENCES [metadata].[run] ([run_id])
) WITH (DATA_COMPRESSION = PAGE)