-- SQL script to check that implied workers do not exceed persons aged 18+
DECLARE @run_id INTEGER = :run_id;


-- Check soft constraint of persons aged 18+
WITH [Household Size] AS (
	SELECT
		[year],
		[mgra],
		SUM(
			CASE
				WHEN [metric] = 'Household Workers - 1' THEN [value]
				WHEN [metric] = 'Household Workers - 2' THEN [value]*2
				WHEN [metric] = 'Household Workers - 3+' THEN [value]*3
				ELSE 0
			END
		) AS [min_workers]
	FROM [outputs].[hh_characteristics]
	WHERE [run_id] = @run_id AND [metric] LIKE 'Household Workers%'
	GROUP BY [year], [mgra]
),
[Population Aged 18+] AS (
    SELECT
        [year],
        [mgra],
        SUM([value]) AS [persons_18plus]
    FROM [outputs].[ase]
    WHERE
        [run_id] = @run_id
        AND [age_group] NOT IN (
            'Under 5',
            '5 to 9',
            '10 to 14',
            '15 to 17'
        )
    GROUP BY [year], [mgra]
)
SELECT
	[Household Size].[year],
	[Household Size].[mgra],
	[Household Size].[min_workers],
	ISNULL([Population Aged 18+].[persons_18plus], 0) AS [persons_18plus]
FROM [Household Size]
LEFT OUTER JOIN [Population Aged 18+]
	ON [Household Size].[year] = [Population Aged 18+].[year]
	AND [Household Size].[mgra] = [Population Aged 18+].[mgra]
WHERE [min_workers] > ISNULL([Population Aged 18+].[persons_18plus], 0);