/*
This query takes SANDAGs GIS team Land Use and Dwelling Unit (LUDU) point layer
and aggregates dwelling units to the MGRA level by structure type. Results are
inserted into a table. Note that the choice of LUDU layer is determined by the
input @year parameter.
*/


-- Initialize parameters and return table ------------------------------------
DECLARE @run_id integer = :run_id;
DECLARE @year integer = :year;
DECLARE @gis_server nvarchar(20) = :gis_server;

-- Build the expected return table MGRA x Structure Type
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
WITH (BOUNDING_BOX =(6151635.98006938, 1775442.36347014, 6613401.66775663, 2129306.52024172), CELLS_PER_OBJECT = 8)

DECLARE @qry nvarchar(max) = '
	INSERT INTO [#ludu]
	SELECT * FROM OPENQUERY([' + @gis_server + '],
	''SELECT[lu], [du], [Shape] FROM [GeoDepot].[sde].[' + @tbl +'] WHERE [du] > 0'')
'
EXEC sp_executesql @qry;


-- Aggregate LUDU dwelling units to MGRAs by structure type ------------------
with [hs] AS (
	SELECT
		[mgra],
		CASE WHEN [lu] BETWEEN 1000 AND 1119 THEN 'Single Family - Detached'
			 WHEN [lu] BETWEEN 1120 AND 1199 THEN 'Single Family - Multiple Unit'
			 WHEN [lu] BETWEEN 1200 AND 1299 OR [lu] > 1300 THEN 'Multifamily'
			 WHEN [lu] = 1300 THEN 'Mobile Home'
		END AS [structure_type],
		[du]
	FROM [inputs].[mgra]
	INNER JOIN [#ludu]
		ON [mgra].[Shape].STIntersects([#ludu].[Shape]) = 1
	WHERE [run_id] = @run_id
)
INSERT INTO [outputs].[hs]  -- Insert results into [outputs].[hs] table
SELECT
	@run_id AS [run_id],
	@year AS [year],
	[#tt_shell].[mgra],
	[#tt_shell].[structure_type],
	ISNULL(SUM([du]), 0) AS [value]
FROM [#tt_shell]
LEFT OUTER JOIN [hs]
	ON [#tt_shell].[mgra] = [hs].[mgra]
	AND [#tt_shell].[structure_type] = [hs].[structure_type]
GROUP BY
	[#tt_shell].[mgra],
	[#tt_shell].[structure_type]


-- Clean up ------------------------------------------------------------------
-- Drop the temporary tables
DROP TABLE [#tt_shell]
DROP TABLE [#ludu]