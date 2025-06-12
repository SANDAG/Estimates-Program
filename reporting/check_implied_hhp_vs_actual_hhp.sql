-- SQL script to check consistency between implied household population, derived from
-- the households by household size, and actual household population
DECLARE @run_id INTEGER = :run_id;
DECLARE @7_plus_max_size INTEGER = 11;

SELECT
    [hhp].[year],
    [hhp].[mgra],
    [value] AS [hhp],
    [implied_min_hhp],
    [implied_max_hhp]
FROM [outputs].[hhp]
LEFT JOIN (
        SELECT 
            [run_id],
            [year],
            [mgra],
            [Household Size - 1] 
                + 2 * [Household Size - 2]
                + 3 * [Household Size - 3]
                + 4 * [Household Size - 4]
                + 5 * [Household Size - 5]
                + 6 * [Household Size - 6]
                + 7 * [Household Size - 7+] AS [implied_min_hhp]
        FROM [outputs].[hh_characteristics]
        PIVOT(
            SUM([value])
            FOR [metric] IN (
                [Household Size - 1],
                [Household Size - 2],
                [Household Size - 3],
                [Household Size - 4],
                [Household Size - 5],
                [Household Size - 6],
                [Household Size - 7+])
            ) AS [pivot]
        WHERE [run_id] = @run_id
    ) AS [implied_min_hhp]
    ON  [hhp].[year] = [implied_min_hhp].[year]
    AND [hhp].[mgra] = [implied_min_hhp].[mgra]
LEFT JOIN (
        SELECT 
            [run_id],
            [year],
            [mgra],
            [Household Size - 1] 
                + 2 * [Household Size - 2]
                + 3 * [Household Size - 3]
                + 4 * [Household Size - 4]
                + 5 * [Household Size - 5]
                + 6 * [Household Size - 6]
                + @7_plus_max_size * [Household Size - 7+] AS [implied_max_hhp]
        FROM [outputs].[hh_characteristics]
        PIVOT(
            SUM([value])
            FOR [metric] IN (
                [Household Size - 1],
                [Household Size - 2],
                [Household Size - 3],
                [Household Size - 4],
                [Household Size - 5],
                [Household Size - 6],
                [Household Size - 7+])
            ) AS [pivot]
        WHERE [run_id] = @run_id
    ) AS [implied_max_hhp]
    ON  [hhp].[year] = [implied_max_hhp].[year]
    AND [hhp].[mgra] = [implied_max_hhp].[mgra]
WHERE [hhp].[run_id] = @run_id
    AND (
        [value] < [implied_min_hhp]
        OR [value] > [implied_max_hhp]
    )
