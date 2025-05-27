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
    [comments] NVARCHAR(MAX) NULL,
    [loaded] BIT NOT NULL,
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

CREATE TABLE [inputs].[controls_city] (
    [run_id] INT NOT NULL,
    [year] INT NOT NULL,
    [city]  NVARCHAR(15) NOT NULL,
    [metric] NVARCHAR(100) NOT NULL,
    [value] FLOAT NOT NULL, 
    INDEX [ccsi_inputs_controls_city] CLUSTERED COLUMNSTORE,
    CONSTRAINT [ixuq_inputs_controls_city] UNIQUE ([run_id], [year], [city], [metric]) WITH (DATA_COMPRESSION = PAGE),
    CONSTRAINT [fk_inputs_controls_city_run_id] FOREIGN KEY ([run_id]) REFERENCES [metadata].[run] ([run_id]),
    CONSTRAINT [chk_non_negative_inputs_controls_city] CHECK ([value] >= 0)
)

CREATE TABLE [inputs].[mgra] (
    [run_id] INT NOT NULL,
    [mgra] INT NOT NULL,
    [2010_census_tract] NVARCHAR(11) NOT NULL,
    [2020_census_tract] NVARCHAR(11) NOT NULL,
    [cities_2020] NVARCHAR(15) NOT NULL,
    [shape] geometry NOT NULL,
    CONSTRAINT [pk_inputs_mgra] PRIMARY KEY ([run_id], [mgra]),
    CONSTRAINT [fk_inputs_mgra_run_id] FOREIGN KEY ([run_id]) REFERENCES [metadata].[run] ([run_id])
    -- No non-negative CHECK here as these values are directly pulled from [GeoDepot]
) WITH (DATA_COMPRESSION = PAGE)

CREATE TABLE [inputs].[special_mgras] (
    [id] INT IDENTITY(1,1),
    [mgra15] INT NOT NULL,
    [start_year] INT NOT NULL,
    [end_year] INT NOT NULL,
    [pop_type] nvarchar(75) NOT NULL,
    [sex] NVARCHAR(6) NULL,
    [min_age] INT NULL,
    [max_age] INT NULL,
    [comment] NVARCHAR(max) NOT NULL
) WITH (DATA_COMPRESSION = PAGE)

INSERT INTO [inputs].[special_mgras] VALUES
    (619, 2017, 2024, 'Group Quarters - Institutional Correctional Facilities', 'Male', 18, NULL, 'CAI Boston Avenue'),
    (751, 2010, 2024, 'Group Quarters - Institutional Correctional Facilities', NULL, 18, NULL, 'Metropolitan Correctional Center, San Diego (MCC San Diego)'),
    (1625, 2010, 2024, 'Group Quarters - Institutional Correctional Facilities', NULL, 18, NULL, 'Western Region Detention Facility'),
    (1729, 2010, 2024, 'Group Quarters - Institutional Correctional Facilities', 'Male', 18, NULL, 'San Diego Central Jail'),
    (5994, 2010, 2024, 'Group Quarters - Institutional Correctional Facilities', 'Female', 18, NULL, 'Las Colinas Detention Facility'),
    (7474, 2010, 2024, 'Group Quarters - Institutional Correctional Facilities', 'Male', 18, NULL, 'Richard J. Donovan Correctional Facility (RJD)'),
    (7569, 2010, 2024, 'Group Quarters - Institutional Correctional Facilities', NULL, 10, 18, 'Kearney Mesa Juvenile Detention Facility'),
    (8155, 2010, 2024, 'Group Quarters - Institutional Correctional Facilities', 'Male', 18, NULL, 'South Bay Detention Facility'),
    (9413, 2019, 2024, 'Group Quarters - Institutional Correctional Facilities', NULL, 18, NULL, 'Otay Mesa Detention Center'),
    (9596, 2010, 2024, 'Group Quarters - Institutional Correctional Facilities', 'Male', 18, NULL, 'Richard J. Donovan Correctional Facility (RJD)'),
    (9632, 2010, 2024, 'Group Quarters - Institutional Correctional Facilities', 'Male', 18, NULL, 'Richard J. Donovan Correctional Facility (RJD)'),
    (10112, 2010, 2024, 'Group Quarters - Institutional Correctional Facilities', 'Male', 10, NULL, 'Includes the Rock Mountain Detention Facility (RMDF), 
        George Bailey Detention Facility (GBDF), East Mesa Reentry Facility (EMRF), and the East Mesa
        Juvenile Detention Facility (EMJDF). Note that the EMJDF is a juvenile facility that allows women.
        The determination was made that juveniles would be allowed in this MGRA but women would not due
        to the facility being majority male and all other facilities being male only.'),
    (18741, 2010, 2024, 'Group Quarters - Institutional Correctional Facilities', 'Male', 18, NULL, 'Vista Detention Facility (VDF) operates as both a male and
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
