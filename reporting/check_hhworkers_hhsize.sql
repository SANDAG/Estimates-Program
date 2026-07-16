-- SQL script to check that households by workers do not exceed households by size
DECLARE @run_id INTEGER = :run_id;


-- Check hard constraint of household size is not violated
WITH [Household Size] AS (
	SELECT
		[year],
		[mgra],
		SUM(CASE WHEN [metric] != 'Household Size - 1' THEN [value] ELSE 0 END) AS [2+ size],  -- 2+ household size
		SUM(CASE WHEN [metric] NOT IN ('Household Size - 1','Household Size - 2') THEN [value] ELSE 0 END) AS [3+ size]  -- 3+ household size
	FROM [outputs].[hh_characteristics]
	WHERE [run_id] = @run_id AND [metric] LIKE 'Household Size%'
	GROUP BY [year], [mgra]
),
[Household Workers] AS (
	SELECT
		[year],
		[mgra],
		SUM(CASE WHEN [metric] = 'Household Workers - 2' THEN [value] ELSE 0 END) AS [2 workers],
		SUM(CASE WHEN [metric] = 'Household Workers - 3+' THEN [value] ELSE 0 END) AS [3+ workers]
	FROM [outputs].[hh_characteristics]
	WHERE [run_id] = @run_id AND [metric] LIKE 'Household Workers%'
	GROUP BY [year], [mgra]
)
SELECT
	[Household Size].[year],
	[Household Size].[mgra],
	[Household Size].[2+ size],
	[Household Size].[3+ size],
	[Household Workers].[2 workers],
	[Household Workers].[3+ workers]
FROM [Household Size]
INNER JOIN [Household Workers]
	ON [Household Size].[year] = [Household Workers].[year]
	AND [Household Size].[mgra] = [Household Workers].[mgra]
WHERE
	[Household Size].[2+ size] < [Household Workers].[2 workers]
	OR [Household Size].[3+ size] < [Household Workers].[3+ workers]