/*
This query takes SANDAGs GIS team Land Use and Dwelling Unit (LUDU) point layer
and aggregates dwelling units to the MGRA level by structure type. Note that 
the choice of LUDU layer is determined by the input @year parameter.
*/

SET NOCOUNT ON;
-- Initialize parameters and return table ------------------------------------
DECLARE @run_id integer = :run_id;
DECLARE @year integer = :year;
DECLARE @mgra_version nvarchar(10) = :mgra_version;
DECLARE @gis_server nvarchar(20) = :gis_server;

-- Build the expected return table MGRA x Structure Type
DROP TABLE IF EXISTS [#tt_shell];
SELECT 
    [mgra],
    [structure_type]
INTO [#tt_shell]
FROM [inputs].[mgra]
CROSS JOIN (
    SELECT [structure_type] FROM (
        VALUES
            ('Single Family - Detached'),
            ('Single Family - Multiple Unit'),
            ('Multifamily'),
            ('Mobile Home')
    ) AS [tt] ([structure_type])
) AS [structure_type]
WHERE [run_id] = @run_id


-- Get SANDAG GIS team LUDU dataset ------------------------------------------
-- Use the year parameter to select the LUDU point table of interest
DECLARE @tbl nvarchar(25) = 
    CASE WHEN @year = 2010 THEN 'LUDU2010_CENPOINTS'
         WHEN @year = 2020 THEN 'LUDU2020_CENSUSPOINTS'
         ELSE CONCAT('LUDU', @year, 'POINTS')
         END

-- Build the OPENQUERY to the GIS server to get the LUDU point table of interest
-- Note the statement stores results in a temporary table for later use
DROP TABLE IF EXISTS [#ludu];
CREATE TABLE [#ludu] (
    [id] INT IDENTITY(1,1) NOT NULL,
    [lu] INT NOT NULL,
    [du] INT NOT NULL,
    [Shape] geometry NOT NULL,
    CONSTRAINT [pk_tt_ludu] PRIMARY KEY ([id])
)

-- Create spatial index for later spatial join
-- Bounding box coordinates from SANDAG GIS team
-- Identical to spatial index on LUDU point layers in GIS database
CREATE SPATIAL INDEX [sidx_tt_ludu] ON [#ludu]
([Shape]) USING GEOMETRY_AUTO_GRID 
WITH (BOUNDING_BOX = (
    6151635.98006938, 
    1775442.36347014, 
    6613401.66775663, 
    2129306.52024172), 
    CELLS_PER_OBJECT = 8
)

DECLARE @qry nvarchar(max) = '
    INSERT INTO [#ludu]
    SELECT *
    FROM OPENQUERY([' + @gis_server + '], ''
        SELECT
            CASE WHEN [overrides].[lu] IS NOT NULL THEN [overrides].[lu] ELSE [ludu].[lu] END AS [lu],
            CASE WHEN [overrides].[du] IS NOT NULL THEN [overrides].[du] ELSE [ludu].[du] END AS [du],
            [Shape]
        FROM [GeoDepot].[sde].[' + @tbl +'] AS [ludu]
        LEFT OUTER JOIN (
            SELECT
                [LCkey],
                [lu],
                [du]
            FROM [SPACECORE].[gis].[LUDU_OVERRIDE_TABLE]
            WHERE [year] = ' + CONVERT(nvarchar, @year) + '
        ) AS [overrides]
            ON [ludu].[LCkey] = [overrides].[LCKey]
        WHERE CASE WHEN [overrides].[du] IS NOT NULL THEN [overrides].[du] ELSE [ludu].[du] END > 0
    '')
'
EXEC sp_executesql @qry;


-- Aggregate LUDU dwelling units to MGRAs by structure type ------------------
with [hs] AS (
    SELECT
        [mgra],
        CASE
            WHEN [lu] BETWEEN 1000 AND 1119
                OR [lu] BETWEEN 2201 AND 2301
                OR [lu] BETWEEN 4101 AND 4120
                OR [lu] BETWEEN 6101 AND 6109
                OR [lu] BETWEEN 6701 AND 6703
                OR [lu] BETWEEN 7200 AND 7211
                OR [lu] BETWEEN 7601 AND 7609
                OR [lu] BETWEEN 8000 AND 8003
                THEN 'Single Family - Detached'
            WHEN [lu] BETWEEN 1120 AND 1199
                OR [lu] BETWEEN 2000 AND 2105
                OR [lu] BETWEEN 5000 AND 6003
                OR [lu] BETWEEN 6501 AND 6509
                OR [lu] BETWEEN 6805 AND 6809
                THEN 'Single Family - Multiple Unit'
            WHEN [lu] BETWEEN 1200 AND 1299
                OR [lu] BETWEEN 1401 AND 1409
                OR [lu] BETWEEN 1501 AND 1503
                OR [lu] BETWEEN 9700 AND 9709
                THEN 'Multifamily'
            WHEN [lu] = 1300 THEN 'Mobile Home'
            ELSE CONVERT(nvarchar, [lu])
        END AS [structure_type],
        [du]
    FROM [inputs].[mgra]
    INNER JOIN [#ludu]
        ON [mgra].[Shape].STIntersects([#ludu].[Shape]) = 1
    WHERE [run_id] = @run_id
)

-- Get results into Python
SELECT
    @run_id AS [run_id],
    @year AS [year],
    [#tt_shell].[mgra],
    [tract],
    [city],
    [#tt_shell].[structure_type],
    ISNULL(SUM([du]), 0) AS [value]
FROM [#tt_shell]
LEFT OUTER JOIN [hs]
    ON [#tt_shell].[mgra] = [hs].[mgra]
    AND [#tt_shell].[structure_type] = [hs].[structure_type]
LEFT OUTER JOIN (
    SELECT
        [mgra],
        CASE
            WHEN @year BETWEEN 2010 AND 2019 THEN [2010_census_tract]
            WHEN @year BETWEEN 2020 AND 2029 THEN [2020_census_tract]
            ELSE NULL
        END AS [tract],
        CASE 
            WHEN @mgra_version = 'mgra15' THEN [cities_2020] 
            ELSE NULL 
        END AS [city]
    FROM [inputs].[mgra]
    WHERE [run_id] = @run_id
) AS [mgra_xref]
    ON [#tt_shell].[mgra] = [mgra_xref].[mgra]
GROUP BY
    [#tt_shell].[mgra],
    [tract],
    [city],
    [#tt_shell].[structure_type]