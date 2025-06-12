-- SQL script to check consistency between householders and adult household population
DECLARE @run_id INTEGER = :run_id;

SELECT
    [adults].[year],
    [adults].[mgra],
    [adult_hhp],
    [hh_size_1]
FROM (
        SELECT
            [year],
            [mgra],
            SUM([value]) AS [adult_hhp]
        FROM [outputs].[ase]
        WHERE [run_id] = @run_id
            AND [pop_type] = 'Household Population'
            AND [age_group] NOT IN ('Under 5', '5 to 9', '10 to 14')
        GROUP BY [year], [mgra]
    ) AS [adults]
LEFT JOIN (
        SELECT
            [year],
            [mgra],
            [value] AS [hh_size_1]
        FROM [outputs].[hh_characteristics]
        WHERE [run_id] = @run_id
            AND [metric] = 'Household Size - 1'
    ) AS [hhs1]
    ON [adults].[year] = [hhs1].[year]
    AND [adults].[mgra] = [hhs1].[mgra]
WHERE [adult_hhp] < [hh_size_1]
