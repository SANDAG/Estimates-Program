/*
For an input MGRA alias from the [GeoAnalyst].[geography].[geography] table,
return the MGRA zones, their shapes, and the one-to-many cross references to
the following geographies:
    [2010_census_blockgroup]
    [2020_census_blockgroup]
    [2010_census_tract]
    [2020_census_tract]
    [puma00]
    [puma10]
    [puma20]
    [cities_2020]

The @insert_switch parameter acts as a switch where a value of 1 inserts data
to the [inputs].[mgra] table and a value of 0 returns the tabular result set
without the shape attribute. This is used to validate data in Python without
needing to handle the shape attribute.
*/
SET NOCOUNT ON;
DECLARE @insert_switch BIT = :insert_switch;
DECLARE @run_id INTEGER = :run_id;
DECLARE @mgra_version NVARCHAR(10) = :mgra_version;


-- Get MGRA data from [GeoAnalyst] and INSERT to temporary table
DROP TABLE IF EXISTS [#inputs_mgra];
WITH [mgra] AS (
    SELECT
        [zone].[zone] AS [mgra],
        [zone].[shape]
    FROM [GeoAnalyst].[geography].[zone]
    INNER JOIN [GeoAnalyst].[geography].[geography]
        ON [zone].[geography_id] = [geography].[geography_id]
    WHERE [geography].[alias] = @mgra_version
),
[xref_2010_census_blockgroup] AS (
    SELECT
        [from_zone] AS [mgra],
        [to_zone] AS [2010_census_blockgroup]
    FROM [GeoAnalyst].[geography].[fn_xref_zones](
        CASE WHEN @mgra_version = 'mgra15' THEN 87 ELSE NULL END
    )
),
[xref_2020_census_blockgroup] AS (
    SELECT
        [from_zone] AS [mgra],
        [to_zone] AS [2020_census_blockgroup]
    FROM [GeoAnalyst].[geography].[fn_xref_zones](
        CASE WHEN @mgra_version = 'mgra15' THEN 90 ELSE NULL END
    )
),
[xref_2010_census_tract] AS (
    SELECT
        [from_zone] AS [mgra],
        [to_zone] AS [2010_census_tract]
    FROM [GeoAnalyst].[geography].[fn_xref_zones](
        CASE WHEN @mgra_version = 'mgra15' THEN 25 ELSE NULL END
    )
),
[xref_2020_census_tract] AS (
    SELECT
        [from_zone] AS [mgra],
        [to_zone] AS [2020_census_tract]
    FROM [GeoAnalyst].[geography].[fn_xref_zones](
        CASE WHEN @mgra_version = 'mgra15' THEN 16 ELSE NULL END
    )
),
[xref_puma00] AS (
    SELECT
        [from_zone] AS [mgra],
        [to_zone] AS [puma00]
    FROM [GeoAnalyst].[geography].[fn_xref_zones](
        CASE WHEN @mgra_version = 'mgra15' THEN 43 ELSE NULL END
    )
),
[xref_puma10] AS (
    SELECT
        [from_zone] AS [mgra],
        [to_zone] AS [puma10]
    FROM [GeoAnalyst].[geography].[fn_xref_zones](
        CASE WHEN @mgra_version = 'mgra15' THEN 42 ELSE NULL END
    )
),
[xref_puma20] AS (
    SELECT
        [from_zone] AS [mgra],
        [to_zone] AS [puma20]
    FROM [GeoAnalyst].[geography].[fn_xref_zones](
        CASE WHEN @mgra_version = 'mgra15' THEN 41 ELSE NULL END
    )
),
[xref_cities_2020] AS (
    SELECT
        [from_zone] AS [mgra],
        [to_name] AS [cities_2020]
    FROM [GeoAnalyst].[geography].[fn_xref_zones](
        CASE WHEN @mgra_version = 'mgra15' THEN 74 ELSE NULL END
    )
)
SELECT
    @run_id AS [run_id],
    CONVERT(int, [mgra].[mgra]) AS [mgra],
    [2010_census_blockgroup],
    [2020_census_blockgroup],
    [2010_census_tract],
    [2020_census_tract],
    [puma00],
    [puma10],
    [puma20],
    [cities_2020],
    [mgra].[shape]
INTO [#inputs_mgra]
FROM [mgra]
INNER JOIN [xref_2010_census_blockgroup]
    ON [mgra].[mgra] = [xref_2010_census_blockgroup].[mgra]
INNER JOIN [xref_2020_census_blockgroup]
    ON [mgra].[mgra] = [xref_2020_census_blockgroup].[mgra]
INNER JOIN [xref_2010_census_tract]
    ON [mgra].[mgra] = [xref_2010_census_tract].[mgra]
INNER JOIN [xref_2020_census_tract]
    ON [mgra].[mgra] = [xref_2020_census_tract].[mgra]
INNER JOIN [xref_puma00]
    ON [mgra].[mgra] = [xref_puma00].[mgra]
INNER JOIN [xref_puma10]
    ON [mgra].[mgra] = [xref_puma10].[mgra]
INNER JOIN [xref_puma20]
    ON [mgra].[mgra] = [xref_puma20].[mgra]
INNER JOIN [xref_cities_2020]
    ON [mgra].[mgra] = [xref_cities_2020].[mgra]


-- INSERT data into [inputs].[mgra] if @insert switch is set
-- Otherwise return the tabular data only without the shape attribute
IF @insert_switch = 1
BEGIN
    INSERT INTO [inputs].[mgra] (
        [run_id],
        [mgra],
        [2010_census_blockgroup],
        [2020_census_blockgroup],
        [2010_census_tract],
        [2020_census_tract],
        [puma00],
        [puma10],
        [puma20],
        [cities_2020],
        [shape]
    )
    SELECT
        [run_id],
        [mgra],
        [2010_census_blockgroup],
        [2020_census_blockgroup],
        [2010_census_tract],
        [2020_census_tract],
        [puma00],
        [puma10],
        [puma20],
        [cities_2020],
        [shape]
    FROM [#inputs_mgra]
    ORDER BY [mgra]
END
ELSE IF @insert_switch = 0
BEGIN
    SELECT
        [run_id],
        [mgra],
        [2010_census_blockgroup],
        [2020_census_blockgroup],
        [2010_census_tract],
        [2020_census_tract],
        [puma00],
        [puma10],
        [puma20],
        [cities_2020]
    FROM [#inputs_mgra]
    ORDER BY [mgra]
END