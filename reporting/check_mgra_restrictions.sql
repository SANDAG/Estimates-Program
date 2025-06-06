-- SQL script to check the MGRA restrictions present in [inputs].[special_mgras]
DECLARE @run_id INTEGER = 189;

-- Check sex restrictions -------------------------------------------------------------
SELECT 
    [mgra_sex].[year],
    [special_mgras].[mgra15] AS [mgra],
    [special_mgras].[pop_type],
    [special_mgras].[sex] AS [allowed_sex],
    [mgra_sex].[pop] AS [non_allowed_sex_pop]
FROM [inputs].[special_mgras]
LEFT JOIN (
        SELECT 
            [year],
            [mgra],
            [sex],
            SUM([value]) AS [pop]
        FROM [outputs].[ase]
        WHERE [run_id] = @run_id
        GROUP BY [year], [mgra], [sex]
    ) AS [mgra_sex]
    ON [special_mgras].[mgra15] = [mgra_sex].[mgra]
    AND [special_mgras].[sex] != [mgra_sex].[sex]
WHERE [special_mgras].[sex] IS NOT NULL
    AND [mgra_sex].[pop] > 0
ORDER BY [mgra], [year]

-- Check minimum age restrictions -----------------------------------------------------
SELECT 
    [ase].[year],
    [ase].[mgra],
    [min_age],
    SUM([value]) AS [pop_under_min_age]
FROM [outputs].[ase]
LEFT JOIN [demographic_warehouse].[dim].[age_group]
    ON [ase].[age_group] = [age_group].[name]
LEFT JOIN [inputs].[special_mgras]
    ON [ase].[mgra] = [special_mgras].[mgra15]
WHERE [run_id] = @run_id
    AND [special_mgras].[min_age] IS NOT NULL
    AND [upper_bound] < [min_age]
    AND [value] > 0
GROUP BY [ase].[year], [ase].[mgra], [min_age]
ORDER BY [ase].[mgra], [ase].[year]

-- Check maximum age restrictions -----------------------------------------------------
SELECT 
    [ase].[year],
    [ase].[mgra],
    [max_age],
    SUM([value]) AS [pop_over_max_age]
FROM [outputs].[ase]
LEFT JOIN [demographic_warehouse].[dim].[age_group]
    ON [ase].[age_group] = [age_group].[name]
LEFT JOIN [inputs].[special_mgras]
    ON [ase].[mgra] = [special_mgras].[mgra15]
WHERE [run_id] = @run_id
    AND [special_mgras].[max_age] IS NOT NULL
    AND [lower_bound] > [max_age]
    AND [value] > 0
GROUP BY [ase].[year], [ase].[mgra], [max_age]
ORDER BY [ase].[mgra], [ase].[year]