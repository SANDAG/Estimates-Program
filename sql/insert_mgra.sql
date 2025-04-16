/*
For an input MGRA alias from the [GeoAnalyst].[geography].[geography] table,
return the MGRA zones, their shapes, and the one-to-many cross references to
the following geographies and insert these records into [inputs].[mgra]:
	[2010_census_tract]
	[2020_census_tract]
	[cities_2020]
*/

DECLARE @run_id integer = :run_id;
DECLARE @mgra nvarchar(10) = :mgra;

with [mgra] AS (
	SELECT
		[zone].[zone] AS [mgra],
		[zone].[shape]
	FROM [GeoAnalyst].[geography].[zone]
	INNER JOIN [GeoAnalyst].[geography].[geography]
		ON [zone].[geography_id] = [geography].[geography_id]
	WHERE [geography].[alias] = @mgra
),
[xref_2010_census_tract] AS (
	SELECT
		[from_zone].[zone] AS [mgra],
		[to_zone].[zone] AS [2010_census_tract]
	FROM [GeoAnalyst].[geography].[xref_zone]
	INNER JOIN [GeoAnalyst].[geography].[xref]
		ON [xref_zone].[xref_id] = [xref].[xref_id]
	INNER JOIN [GeoAnalyst].[geography].[geography] AS [from_geo]
		ON [xref].[from_geography_id] = [from_geo].[geography_id]
	INNER JOIN [GeoAnalyst].[geography].[geography] AS [to_geo]
		ON [xref].[to_geography_id] = [to_geo].[geography_id]
	INNER JOIN [GeoAnalyst].[geography].[zone] AS [from_zone]
		ON [xref_zone].[from_zone_id] = [from_zone].[zone_id]
	INNER JOIN [GeoAnalyst].[geography].[zone] AS [to_zone]
		ON [xref_zone].[to_zone_id] = [to_zone].[zone_id]
	WHERE
		[from_geo].[alias] = @mgra
		AND [to_geo].[alias] = '2010_census_tract'
		AND CASE WHEN @mgra = 'mgra15' THEN 25  -- One to one xref between Series 15 MGRA and 2010 census tract
		    ELSE NULL END = [xref].[xref_id]
),
[xref_2020_census_tract] AS (
	SELECT
		[from_zone].[zone] AS [mgra],
		[to_zone].[zone] AS [2020_census_tract]
	FROM [GeoAnalyst].[geography].[xref_zone]
	INNER JOIN [GeoAnalyst].[geography].[xref]
		ON [xref_zone].[xref_id] = [xref].[xref_id]
	INNER JOIN [GeoAnalyst].[geography].[geography] AS [from_geo]
		ON [xref].[from_geography_id] = [from_geo].[geography_id]
	INNER JOIN [GeoAnalyst].[geography].[geography] AS [to_geo]
		ON [xref].[to_geography_id] = [to_geo].[geography_id]
	INNER JOIN [GeoAnalyst].[geography].[zone] AS [from_zone]
		ON [xref_zone].[from_zone_id] = [from_zone].[zone_id]
	INNER JOIN [GeoAnalyst].[geography].[zone] AS [to_zone]
		ON [xref_zone].[to_zone_id] = [to_zone].[zone_id]
	WHERE
		[from_geo].[alias] = @mgra
		AND [to_geo].[alias] = '2020_census_tract'
),
[xref_cities_2020] AS (
	SELECT
		[from_zone].[zone] AS [mgra],
		[to_zone].[name] AS [cities_2020]
	FROM [GeoAnalyst].[geography].[xref_zone]
	INNER JOIN [GeoAnalyst].[geography].[xref]
		ON [xref_zone].[xref_id] = [xref].[xref_id]
	INNER JOIN [GeoAnalyst].[geography].[geography] AS [from_geo]
		ON [xref].[from_geography_id] = [from_geo].[geography_id]
	INNER JOIN [GeoAnalyst].[geography].[geography] AS [to_geo]
		ON [xref].[to_geography_id] = [to_geo].[geography_id]
	INNER JOIN [GeoAnalyst].[geography].[zone] AS [from_zone]
		ON [xref_zone].[from_zone_id] = [from_zone].[zone_id]
	INNER JOIN [GeoAnalyst].[geography].[zone] AS [to_zone]
		ON [xref_zone].[to_zone_id] = [to_zone].[zone_id]
	WHERE
		[from_geo].[alias] = @mgra
		AND [to_geo].[alias] = 'cities_2020'
)
INSERT INTO [inputs].[mgra] (
	[run_id],
	[mgra],
	[2010_census_tract],
	[2020_census_tract],
	[cities_2020],
	[shape]
)
SELECT
	@run_id AS [run_id],
	CONVERT(int, [mgra].[mgra]) AS [mgra],
	[2010_census_tract],
	[2020_census_tract],
	[cities_2020],
	[mgra].[shape]
FROM [mgra]
INNER JOIN [xref_2010_census_tract]
	ON [mgra].[mgra] = [xref_2010_census_tract].[mgra]
INNER JOIN [xref_2020_census_tract]
	ON [mgra].[mgra] = [xref_2020_census_tract].[mgra]
INNER JOIN [xref_cities_2020]
	ON [mgra].[mgra] = [xref_cities_2020].[mgra]