-- SQL script to check consistency between households and population variables. This 
-- includes but is not limited to checking things like making sure there are enough
-- adults (age >= 15 by Census definition) for all households of size 1
DECLARE @run_id INTEGER = 189;

-- Check adults vs households of size one ---------------------------------------------
SELECT 
    [adults].[year],
    [adults].[mgra],
    [adult_hhp],
    [value] AS [hhs1]
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
LEFT JOIN [outputs].[hh_characteristics]
    ON [adults].[year] = [hh_characteristics].[year]
    AND [adults].[mgra] = [hh_characteristics].[mgra]
WHERE [hh_characteristics].[metric] = 'Household Size - 1'
    AND [hh_characteristics].[run_id] = @run_id
    AND [adult_hhp] < [value]

-- Check implied minimum household size from hhs distribution -------------------------
SELECT 
    [hhp].[year],
    [hhp].[mgra],
    [hhp].[value] AS [actual_hhp],
    [implied_min_hhp]
FROM [outputs].[hhp]
LEFT JOIN (
        SELECT 
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
WHERE [run_id] = @run_id
    AND [hhp].[value] < [implied_min_hhp]

-- Check implied maximum household size from hhs distribution -------------------------
SELECT 
    [hhp].[year],
    [hhp].[mgra],
    [hhp].[value] AS [actual_hhp],
    [implied_max_hhp]
FROM [outputs].[hhp]
LEFT JOIN (
        SELECT 
            [year],
            [mgra],
            [Household Size - 1] 
                + 2 * [Household Size - 2]
                + 3 * [Household Size - 3]
                + 4 * [Household Size - 4]
                + 5 * [Household Size - 5]
                + 6 * [Household Size - 6]
                + 11 * [Household Size - 7+] AS [implied_max_hhp]
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
WHERE [run_id] = @run_id
    AND [hhp].[value] > [implied_max_hhp]
