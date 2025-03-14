/*
This query takes SANDAGs GIS team Group Quarters (GQ) point layer and
aggregates to the MGRA level by type. Results are returned as a SELECT
statement for use in a Python utility that generates final results.

Note that the [inputs].[special_mgras] table is used to segment
"Other Group Quarters" into "Non-Disabled Institutional Group Quarters"
and "Disabled Institutional Group Quarters".
*/


SET NOCOUNT ON;
-- Initialize parameters and return table ------------------------------------
DECLARE @run_id integer = :run_id;
DECLARE @year integer = :year;
DECLARE @mgra_version nvarchar(10) = :mgra_version;
DECLARE @gis_server nvarchar(20) = :gis_server;

-- Build the expected return table MGRA x GQ Type
SELECT 
	[mgra],
	CASE WHEN @mgra_version = 'mgra15' THEN [cities_2020] ELSE NULL END AS [city],
	[gq_type]
INTO [#tt_shell]
FROM [inputs].[mgra]
CROSS JOIN (
	SELECT [gq_type] FROM (
		VALUES
			('Group Quarters - College'),
			('Group Quarters - Military'),
			('Group Quarters - Non-Disabled Institutional'),
			('Group Quarters - Disabled Institutional')
	) AS [tt] ([gq_type])
) AS [gq_type]
WHERE [run_id] = @run_id


-- Get SANDAG GIS team GQ dataset --------------------------------------------
-- Build the OPENQUERY to the GIS server to get the GQ point data of interest
-- Note the statement stores results in a temporary table for later use
CREATE TABLE [#gq] (
	[id] INT IDENTITY(1,1) NOT NULL,
	[gqMil] INT NOT NULL,
	[gqCivCol] INT NOT NULL,
	[gqOther] INT NOT NULL,
	[Shape] geometry NOT NULL,
	CONSTRAINT [pk_tt_gq] PRIMARY KEY ([id])
)

DECLARE @qry nvarchar(max) = '
	INSERT INTO [#gq]
	SELECT * FROM OPENQUERY([' + @gis_server + '],
	''SELECT [gqMil], [gqCivCol], [gqOther], [Shape] FROM [SPACECORE].[gis].[GROUPQUARTERS] WHERE [effectYear] = ' + CONVERT(nvarchar, @year) + ''')
'
EXEC sp_executesql @qry;


-- Aggregate GQ points to MGRAs by type -------------------------------------
SELECT
	@run_id AS [run_id],
	@year AS [year],
	[#tt_shell].[mgra],
	[#tt_shell].[city],
	[#tt_shell].[gq_type],
	ISNULL([value], 0) AS [value]
FROM [#tt_shell]
LEFT OUTER JOIN (
	SELECT
		[mgra], 
		SUM([gqCivCol]) AS [Group Quarters - College],
		SUM([gqMil]) AS [Group Quarters - Military],
		SUM(
			CASE WHEN [special_mgras].[facility_type] = 'Non-Disabled Institutional Group Quarters'
				 THEN [gqOther]
				 ELSE 0 END
		) AS [Group Quarters - Non-Disabled Institutional],
		SUM(
			CASE WHEN [special_mgras].[facility_type] != 'Non-Disabled Institutional Group Quarters'
					OR [special_mgras].[facility_type] IS NULL
				 THEN [gqOther]
				 ELSE 0 END
		) AS [Group Quarters - Disabled Institutional]
	FROM [inputs].[mgra]
	LEFT OUTER JOIN [inputs].[special_mgras]
		ON [mgra].[mgra] = CASE WHEN @mgra_version = 'mgra15' THEN [special_mgras].[mgra15] END
	INNER JOIN [#gq]
		ON [mgra].[Shape].STIntersects([#gq].[Shape]) = 1
	WHERE [run_id] = @run_id
	GROUP BY [mgra]
) AS [pivot]
UNPIVOT (
	[value] FOR [gq_type] IN (
		[Group Quarters - College],
		[Group Quarters - Military],
		[Group Quarters - Non-Disabled Institutional],
		[Group Quarters - Disabled Institutional]
	)
) AS [unpivot]
	ON [#tt_shell].[mgra] = [unpivot].[mgra]
	AND [#tt_shell].[gq_type] = [unpivot].[gq_type]


-- Clean up ------------------------------------------------------------------
-- Drop the temporary tables
DROP TABLE [#tt_shell]
DROP TABLE [#gq]