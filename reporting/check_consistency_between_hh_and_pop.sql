-- SQL script to check consistency between households and population variables. This 
-- includes but is not limited to checking things like making sure there are enough
-- adults (age >= 15 by Census definition) for all households of size 1
DECLARE @run_id INTEGER = :run_id;
DECLARE @7_plus_max_size INTEGER = 11;

-- Check adults vs households of size one ---------------------------------------------
SELECT 
    [adults].[year],
    [adults].[mgra],
    [adult_hhp],
    [hh_size_1],
    [hhp],
    [implied_min_hhp],
    [implied_max_hhp]
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
LEFT JOIN (
        SELECT 
            [year],
            [mgra],
            [value] AS [hhp]
        FROM [outputs].[hhp]
        WHERE [run_id] = @run_id
    ) AS [hhp]
    ON [adults].[year] = [hhp].[year]
    AND [adults].[mgra] = [hhp].[mgra]
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
    ON  [adults].[year] = [implied_min_hhp].[year]
    AND [adults].[mgra] = [implied_min_hhp].[mgra]
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
    ON  [adults].[year] = [implied_max_hhp].[year]
    AND [adults].[mgra] = [implied_max_hhp].[mgra]
WHERE [adult_hhp] < [hh_size_1]
    OR [hhp] < [implied_min_hhp]
    OR [hhp] > [implied_max_hhp]
