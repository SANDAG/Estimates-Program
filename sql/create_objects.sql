CREATE SCHEMA [metadata]
GO

CREATE TABLE [metadata].[run] (
    [run_id] INT NOT NULL,
    [series] INT NOT NULL,
    [start_year] INT NOT NULL,
    [end_year] INT NOT NULL,
    [user] NVARCHAR(100) NOT NULL, 
    [start_date] DATETIME NOT NULL,
    [end_date] DATETIME NULL,
    [version] NVARCHAR(50) NOT NULL,
    [comments] NVARCHAR(MAX) NULL,
    [complete] BIT NOT NULL,
    CONSTRAINT [pk_metadata_run] PRIMARY KEY ([run_id])
) WITH (DATA_COMPRESSION = PAGE)
GO


CREATE SCHEMA [inputs]
GO

CREATE TABLE [inputs].[controls_ase] (
    [run_id] INT NOT NULL,
    [year] INT NOT NULL,
    [pop_type] NVARCHAR(75) NOT NULL,
    [age_group] NVARCHAR(15) NOT NULL,
    [sex] NVARCHAR(6) NOT NULL,
    [ethnicity] NVARCHAR(50) NOT NULL,
    [value] INT NOT NULL,
    INDEX [ccsi_inputs_controls_ase] CLUSTERED COLUMNSTORE,
    CONSTRAINT [ixuq_inputs_controls_ase] UNIQUE ([run_id], [year], [pop_type], [age_group], [sex], [ethnicity]) WITH (DATA_COMPRESSION = PAGE),
    CONSTRAINT [fk_inputs_controls_ase_run_id] FOREIGN KEY ([run_id]) REFERENCES [metadata].[run] ([run_id]),
    CONSTRAINT [chk_non_negative_inputs_controls_ase] CHECK ([value] >= 0)
)
GO

CREATE TABLE [inputs].[controls_jobs] (
    [run_id] INT NOT NULL,
    [year] INT NOT NULL,
    [industry_code] NVARCHAR(5) NOT NULL,
    [metric] NVARCHAR(4) NOT NULL,
    [value] INT NOT NULL,
    INDEX [ccsi_inputs_controls_jobs] CLUSTERED COLUMNSTORE,
    CONSTRAINT [ixuq_inputs_controls_jobs] UNIQUE ([run_id], [year], [industry_code], [metric]) WITH (DATA_COMPRESSION = PAGE),
    CONSTRAINT [fk_inputs_controls_jobs_run_id] FOREIGN KEY ([run_id]) REFERENCES [metadata].[run] ([run_id]),
    CONSTRAINT [chk_non_negative_inputs_controls_jobs] CHECK ([value] >= 0)
)
GO

CREATE TABLE [inputs].[controls_tract] (
    [run_id] INT NOT NULL,
    [year] INT NOT NULL,
    [tract]  NVARCHAR(11) NOT NULL,
    [metric] NVARCHAR(100) NOT NULL,
    [value] FLOAT NOT NULL, 
    INDEX [ccsi_inputs_controls_tract] CLUSTERED COLUMNSTORE,
    CONSTRAINT [ixuq_inputs_controls_tract] UNIQUE ([run_id], [year], [tract], [metric]) WITH (DATA_COMPRESSION = PAGE),
    CONSTRAINT [fk_inputs_controls_tract_run_id] FOREIGN KEY ([run_id]) REFERENCES [metadata].[run] ([run_id]),
    CONSTRAINT [chk_non_negative_inputs_controls_tract] CHECK ([value] >= 0)
)
GO

CREATE TABLE [inputs].[controls_jurisdiction] (
    [run_id] INT NOT NULL,
    [year] INT NOT NULL,
    [jurisdiction]  NVARCHAR(31) NOT NULL,
    [metric] NVARCHAR(100) NOT NULL,
    [value] FLOAT NOT NULL, 
    INDEX [ccsi_inputs_controls_jurisdiction] CLUSTERED COLUMNSTORE,
    CONSTRAINT [ixuq_inputs_controls_jurisdiction] UNIQUE ([run_id], [year], [jurisdiction], [metric]) WITH (DATA_COMPRESSION = PAGE),
    CONSTRAINT [fk_inputs_controls_jurisdiction_run_id] FOREIGN KEY ([run_id]) REFERENCES [metadata].[run] ([run_id]),
    CONSTRAINT [chk_non_negative_inputs_controls_jurisdiction] CHECK ([value] >= 0)
)
GO

CREATE TABLE [inputs].[mgra] (
    [run_id] INT NOT NULL,
    [mgra] INT NOT NULL,
    [shape] geometry NOT NULL,
    CONSTRAINT [pk_inputs_mgra] PRIMARY KEY ([run_id], [mgra]),
    CONSTRAINT [fk_inputs_mgra_run_id] FOREIGN KEY ([run_id]) REFERENCES [metadata].[run] ([run_id])
    -- No non-negative CHECK here as these values are directly pulled from [GeoDepot]
) WITH (DATA_COMPRESSION = PAGE)
GO

CREATE TABLE [inputs].[special_mgras] (
    [id] INT IDENTITY(1,1),
    [series] INT NOT NULL,
    [mgra] INT NOT NULL,
    [start_year] INT NOT NULL,
    [end_year] INT NOT NULL,
    [pop_type] nvarchar(75) NOT NULL,
    [sex] NVARCHAR(6) NULL,
    [min_age] INT NULL,
    [max_age] INT NULL,
    [comment] NVARCHAR(max) NOT NULL,
    CONSTRAINT [pk_inputs_special_mgras] PRIMARY KEY ([id]),
    CONSTRAINT [ixuq_inputs_special_mgras] UNIQUE ([series], [mgra], [start_year], [end_year], [pop_type], [sex], [min_age], [max_age]),
    CONSTRAINT [chk_valid_sex_special_mgras] CHECK ([sex] IN ('Male', 'Female'))
) WITH (DATA_COMPRESSION = PAGE)

INSERT INTO [inputs].[special_mgras] (
    [series],
    [mgra],
    [start_year],
    [end_year],
    [pop_type],
    [sex],
    [min_age],
    [max_age],
    [comment]
) VALUES
    (15, 619, 2017, 2024, 'Group Quarters - Institutional Correctional Facilities', 'Male', 18, NULL, 'CAI Boston Avenue'),
    (15, 751, 2010, 2024, 'Group Quarters - Institutional Correctional Facilities', NULL, 18, NULL, 'Metropolitan Correctional Center, San Diego (MCC San Diego)'),
    (15, 1625, 2010, 2024, 'Group Quarters - Institutional Correctional Facilities', NULL, 18, NULL, 'Western Region Detention Facility'),
    (15, 1729, 2010, 2024, 'Group Quarters - Institutional Correctional Facilities', 'Male', 18, NULL, 'San Diego Central Jail'),
    (15, 5994, 2010, 2024, 'Group Quarters - Institutional Correctional Facilities', 'Female', 18, NULL, 'Las Colinas Detention Facility'),
    (15, 7474, 2010, 2024, 'Group Quarters - Institutional Correctional Facilities', 'Male', 18, NULL, 'Richard J. Donovan Correctional Facility (RJD)'),
    (15, 7569, 2010, 2024, 'Group Quarters - Institutional Correctional Facilities', NULL, 10, 18, 'Kearney Mesa Juvenile Detention Facility'),
    (15, 8155, 2010, 2024, 'Group Quarters - Institutional Correctional Facilities', 'Male', 18, NULL, 'South Bay Detention Facility'),
    (15, 9413, 2019, 2024, 'Group Quarters - Institutional Correctional Facilities', NULL, 18, NULL, 'Otay Mesa Detention Center'),
    (15, 9596, 2010, 2024, 'Group Quarters - Institutional Correctional Facilities', 'Male', 18, NULL, 'Richard J. Donovan Correctional Facility (RJD)'),
    (15, 9632, 2010, 2024, 'Group Quarters - Institutional Correctional Facilities', 'Male', 18, NULL, 'Richard J. Donovan Correctional Facility (RJD)'),
    (15, 10112, 2010, 2024, 'Group Quarters - Institutional Correctional Facilities', 'Male', 10, NULL, 'Includes the Rock Mountain Detention Facility (RMDF), 
        George Bailey Detention Facility (GBDF), East Mesa Reentry Facility (EMRF), and the East Mesa
        Juvenile Detention Facility (EMJDF). Note that the EMJDF is a juvenile facility that allows women.
        The determination was made that juveniles would be allowed in this MGRA but women would not due
        to the facility being majority male and all other facilities being male only.'),
    (15, 18741, 2010, 2024, 'Group Quarters - Institutional Correctional Facilities', 'Male', 18, NULL, 'Vista Detention Facility (VDF) operates as both a male and
        female facility intake facility but the majority of housed inmates are male as women are
        transferred to the Las Colinas Detention Facility.')
GO


CREATE SCHEMA [outputs]
GO

CREATE TABLE [outputs].[ase] (
    [run_id] INT NOT NULL,
    [year] INT NOT NULL,
    [mgra] INT NOT NULL,
    [pop_type] NVARCHAR(75) NOT NULL,
    [age_group] NVARCHAR(15) NOT NULL,
    [sex] NVARCHAR(6) NOT NULL,
    [ethnicity] NVARCHAR(50) NOT NULL,
    [value] INT NOT NULL,
    INDEX [ccsi_outputs_ase] CLUSTERED COLUMNSTORE,
    CONSTRAINT [ixuq_outputs_ase] UNIQUE ([run_id], [year], [mgra], [pop_type], [age_group], [sex], [ethnicity]) WITH (DATA_COMPRESSION = PAGE),
    CONSTRAINT [fk_outputs_ase_run_id] FOREIGN KEY ([run_id]) REFERENCES [metadata].[run] ([run_id]),
    CONSTRAINT [fk_outputs_ase_mgra] FOREIGN KEY ([run_id], [mgra]) REFERENCES [inputs].[mgra] ([run_id], [mgra]),
    CONSTRAINT [chk_non_negative_outputs_ase] CHECK ([value] >= 0)
)
GO

-- For purposes of data insertion speed, only non-zero ASE data is inserted into
-- [outputs].[ase]. In case you want the full table with zeros, you can use the below
-- function
CREATE FUNCTION [outputs].[fn_ase_with_zeros](
    @run_id INTEGER
)
RETURNS @ase_with_zeros TABLE (
        [run_id] INTEGER NOT NULL,
        [year] INTEGER NOT NULL,
        [mgra] INTEGER NOT NULL,
        [pop_type] NVARCHAR(75) NOT NULL,
        [age_group] NVARCHAR(15) NOT NULL,
        [sex] NVARCHAR(6) NOT NULL,
        [ethnicity] NVARCHAR(50) NOT NULL,
        [value] INTEGER NOT NULL
    )
AS
BEGIN
    INSERT INTO @ase_with_zeros
    SELECT
        [shell].[run_id],
        [shell].[year],
        [shell].[mgra],
        [shell].[pop_type],
        [shell].[age_group],
        [shell].[sex],
        [shell].[ethnicity],
        ISNULL([ase].[value], 0) AS [value]
    FROM (
            SELECT
                [run_id].[run_id],
                [year].[year],
                [mgra].[mgra],
                [pop_type].[pop_type],
                [age_group].[age_group],
                [sex].[sex],
                [ethnicity].[ethnicity]
            FROM (VALUES(@run_id)) AS [run_id]([run_id])
            CROSS JOIN (
                SELECT DISTINCT [year]
                FROM [outputs].[ase]
                WHERE [run_id] = @run_id
            ) AS [year]
            CROSS JOIN (
                SELECT DISTINCT [mgra]
                FROM [inputs].[mgra]
                WHERE [run_id] = @run_id
            ) AS [mgra]
            CROSS JOIN (
                SELECT DISTINCT [pop_type]
                FROM [outputs].[ase]
                WHERE [run_id] = @run_id
            ) AS [pop_type]
            CROSS JOIN (
                SELECT DISTINCT [age_group]
                FROM [outputs].[ase]
                WHERE [run_id] = @run_id
            ) AS [age_group]
            CROSS JOIN (
                SELECT DISTINCT [sex]
                FROM [outputs].[ase]
                WHERE [run_id] = @run_id
            ) AS [sex]
            CROSS JOIN (
                SELECT DISTINCT [ethnicity]
                FROM [outputs].[ase]
                WHERE [run_id] = @run_id
            ) AS [ethnicity]
        ) AS [shell]
    LEFT JOIN [outputs].[ase]
        ON [shell].[run_id] = [ase].[run_id]
        AND [shell].[year] = [ase].[year]
        AND [shell].[mgra] = [ase].[mgra]
        AND [shell].[pop_type] = [ase].[pop_type]
        AND [shell].[age_group] = [ase].[age_group]
        AND [shell].[sex] = [ase].[sex]
        AND [shell].[ethnicity] = [ase].[ethnicity]
    RETURN;
END
GO

CREATE TABLE [outputs].[gq] (
    [run_id] INT NOT NULL,
    [year] INT NOT NULL,
    [mgra] INT NOT NULL,
    [gq_type] NVARCHAR(75) NOT NULL,
    [value] INT NOT NULL, 
    INDEX [ccsi_outputs_gq] CLUSTERED COLUMNSTORE,
    CONSTRAINT [ixuq_outputs_gq] UNIQUE ([run_id], [year], [mgra], [gq_type]) WITH (DATA_COMPRESSION = PAGE),
    CONSTRAINT [fk_outputs_gq_run_id] FOREIGN KEY ([run_id]) REFERENCES [metadata].[run] ([run_id]),
    CONSTRAINT [fk_outputs_gq_mgra] FOREIGN KEY ([run_id], [mgra]) REFERENCES [inputs].[mgra] ([run_id], [mgra]),
    CONSTRAINT [chk_non_negative_outputs_gq] CHECK ([value] >= 0)
)
GO

CREATE TABLE [outputs].[hh] (
    [run_id] INT NOT NULL,
    [year] INT NOT NULL,
    [mgra] INT NOT NULL,
    [structure_type] NVARCHAR(35) NOT NULL,
    [value] INT NOT NULL, 
    INDEX [ccsi_outputs_hh] CLUSTERED COLUMNSTORE,
    CONSTRAINT [ixuq_outputs_hh] UNIQUE ([run_id], [year], [mgra], [structure_type]) WITH (DATA_COMPRESSION = PAGE),
    CONSTRAINT [fk_outputs_hh_run_id] FOREIGN KEY ([run_id]) REFERENCES [metadata].[run] ([run_id]),
    CONSTRAINT [fk_outputs_hh_mgra] FOREIGN KEY ([run_id], [mgra]) REFERENCES [inputs].[mgra] ([run_id], [mgra]),
    CONSTRAINT [chk_non_negative_outputs_hh] CHECK ([value] >= 0)
)
GO

CREATE TABLE [outputs].[hh_characteristics] (
    [run_id] INT NOT NULL,
    [year] INT NOT NULL,
    [mgra] INT NOT NULL,
    [metric] NVARCHAR(100) NOT NULL,
    [value] INT NOT NULL, 
    INDEX [ccsi_outputs_hh_characteristics] CLUSTERED COLUMNSTORE,
    CONSTRAINT [ixuq_outputs_hh_characteristics] UNIQUE ([run_id], [year], [mgra], [metric]) WITH (DATA_COMPRESSION = PAGE),
    CONSTRAINT [fk_outputs_hh_characteristics_run_id] FOREIGN KEY ([run_id]) REFERENCES [metadata].[run] ([run_id]),
    CONSTRAINT [fk_outputs_hh_characteristics_mgra] FOREIGN KEY ([run_id], [mgra]) REFERENCES [inputs].[mgra] ([run_id], [mgra]),
    CONSTRAINT [chk_non_negative_outputs_hh_characteristics] CHECK ([value] >= 0)
)
GO

CREATE TABLE [outputs].[hs] (
    [run_id] INT NOT NULL,
    [year] INT NOT NULL,
    [mgra] INT NOT NULL,
    [structure_type] NVARCHAR(35) NOT NULL,
    [value] INT NOT NULL, 
    INDEX [ccsi_outputs_hs] CLUSTERED COLUMNSTORE,
    CONSTRAINT [ixuq_outputs_hs] UNIQUE ([run_id], [year], [mgra], [structure_type]) WITH (DATA_COMPRESSION = PAGE),
    CONSTRAINT [fk_outputs_hs_run_id] FOREIGN KEY ([run_id]) REFERENCES [metadata].[run] ([run_id]),
    CONSTRAINT [fk_outputs_hs_mgra] FOREIGN KEY ([run_id], [mgra]) REFERENCES [inputs].[mgra] ([run_id], [mgra]),
    CONSTRAINT [chk_non_negative_outputs_hs] CHECK ([value] >= 0)
)
GO

CREATE TABLE [outputs].[hhp] (
    [run_id] INT NOT NULL,
    [year] INT NOT NULL,
    [mgra] INT NOT NULL,
    [value] INT NOT NULL,
    INDEX [ccsi_outputs_hh] CLUSTERED COLUMNSTORE,
    CONSTRAINT [ixuq_outputs_hhp] UNIQUE ([run_id], [year], [mgra]) WITH (DATA_COMPRESSION = PAGE),
    CONSTRAINT [fk_outputs_hhp_run_id] FOREIGN KEY ([run_id]) REFERENCES [metadata].[run] ([run_id]),
    CONSTRAINT [fk_outputs_hhp_mgra] FOREIGN KEY ([run_id], [mgra]) REFERENCES [inputs].[mgra] ([run_id], [mgra]),
    CONSTRAINT [chk_non_negative_outputs_hhp] CHECK ([value] >= 0)
)
GO

CREATE TABLE [outputs].[jobs] (
    [run_id] INT NOT NULL,
    [year] INT NOT NULL,
    [mgra] INT NOT NULL, 
    [industry_code] NVARCHAR(5) NOT NULL,
    [value] INT NOT NULL,
    INDEX [ccsi_outputs_jobs] CLUSTERED COLUMNSTORE,
    CONSTRAINT [ixuq_outputs_jobs] UNIQUE ([run_id], [year], [mgra], [industry_code]) WITH (DATA_COMPRESSION = PAGE),
    CONSTRAINT [fk_outputs_jobs_run_id] FOREIGN KEY ([run_id]) REFERENCES [metadata].[run] ([run_id]),
    CONSTRAINT [fk_outputs_jobs_mgra] FOREIGN KEY ([run_id], [mgra]) REFERENCES [inputs].[mgra] ([run_id], [mgra]),
    CONSTRAINT [chk_non_negative_outputs_jobs] CHECK ([value] >= 0)
)
GO
