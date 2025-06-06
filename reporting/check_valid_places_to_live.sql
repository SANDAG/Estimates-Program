-- SQL script to check that there are valid places to live in each MGRA. Basically 
-- meaning there is housing stock for each household, and there are households for 
-- every household population
DECLARE @run_id INTEGER = 189;

-- Check housing stock and households -------------------------------------------------
SELECT 
    [hs].[year],
    [hs].[mgra],
    [hs].[structure_type],
    [hs].[value] AS [hs],
    [hh].[value] AS [hh]
FROM [outputs].[hs]
LEFT JOIN [outputs].[hh]
    ON [hs].[run_id] = [hh].[run_id]
    AND [hs].[year] = [hh].[year]
    AND [hs].[mgra] = [hh].[mgra]
    AND [hs].[structure_type] = [hh].[structure_type]
WHERE [hs].[run_id] = @run_id
    AND [hs].[value] < [hh].[value]

-- Check households and household population ------------------------------------------
SELECT 
    [hh].[year],
    [hh].[mgra],
    [hh].[hh],
    [hhp].[value] AS [hhp]
FROM (
        SELECT 
            [year],
            [mgra],
            SUM([value]) AS [hh]
        FROM [outputs].[hh]
        WHERE [run_id] = @run_id
        GROUP BY [year], [mgra]
    ) AS [hh]
LEFT JOIN [outputs].[hhp]
    ON [hh].[year] = [hhp].[year]
    AND [hh].[mgra] = [hhp].[mgra]
WHERE [hhp].[run_id] = @run_id
    AND [hh] > [hhp].[value]