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
GO


CREATE SCHEMA [outputs]
GO

CREATE TABLE [outputs].[hs] (
    [run_id] INT NOT NULL,
    [year] INT NOT NULL,
    [mgra] INT NOT NULL,
    [structure_type] NVARCHAR(35) NOT NULL,
    [hs] INT NOT NULL, 
    INDEX [ccsi_outputs_hs] CLUSTERED COLUMNSTORE,
    CONSTRAINT [ixuq_outputs_hs] UNIQUE ([run_id], [year], [mgra], [structure_type]) WITH (DATA_COMPRESSION = PAGE),
    CONSTRAINT [fk_outputs_hs_run_id] FOREIGN KEY ([run_id]) REFERENCES [metadata].[run] ([run_id]),
    CONSTRAINT [fk_outputs_hs_mgra] FOREIGN KEY ([run_id], [mgra]) REFERENCES [inputs].[mgra] ([run_id], [mgra])
)
GO