-- SQL script to check the MGRA restrictions present in [inputs].[special_mgras]
DECLARE @run_id INTEGER = :run_id;

SELECT *
FROM (
    -- Check sex restrictions ---------------------------------------------------------
    SELECT 
        [mgra_sex].[year],
        [special_mgras].[mgra15] AS [mgra],
        [special_mgras].[pop_type],
        'Allowed Sex - ' + [special_mgras].[sex] AS [metric],
        [mgra_sex].[pop] AS [invalid_pop]
    FROM [inputs].[special_mgras]
    LEFT JOIN (
            SELECT 
                [year],
                [mgra],
                [sex],
                [pop_type],
                SUM([value]) AS [pop]
            FROM [outputs].[ase]
            WHERE [run_id] = @run_id
            GROUP BY [year], [mgra], [sex], [pop_type]
        ) AS [mgra_sex]
        ON [special_mgras].[mgra15] = [mgra_sex].[mgra]
        AND [special_mgras].[sex] != [mgra_sex].[sex]
        AND [special_mgras].[pop_type] = [mgra_sex].[pop_type]
    WHERE [special_mgras].[sex] IS NOT NULL
        AND [mgra_sex].[pop] > 0

    UNION ALL 

    -- Check minimum age restrictions -------------------------------------------------
    SELECT 
        [ase].[year],
        [ase].[mgra],
        [ase].[pop_type],
        'Minimum Age - ' + CAST([min_age] AS NVARCHAR) AS [metric],
        SUM([value]) AS [invalid_pop]
    FROM [outputs].[ase]
    LEFT JOIN [demographic_warehouse].[dim].[age_group]
        ON [ase].[age_group] = [age_group].[name]
    LEFT JOIN [inputs].[special_mgras]
        ON [ase].[mgra] = [special_mgras].[mgra15]
        AND [ase].[pop_type] = [special_mgras].[pop_type]
    WHERE [run_id] = @run_id
        AND [special_mgras].[min_age] IS NOT NULL
        AND [upper_bound] < [min_age]
        AND [value] > 0
    GROUP BY [ase].[year], [ase].[mgra], [ase].[pop_type], [min_age]

    UNION ALL 

    -- Check maximum age restrictions -------------------------------------------------
    SELECT 
        [ase].[year],
        [ase].[mgra],
        [ase].[pop_type],
        'Maximum Age - ' + CAST([max_age] AS NVARCHAR) AS [metric],
        SUM([value]) AS [invalid_pop]
    FROM [outputs].[ase]
    LEFT JOIN [demographic_warehouse].[dim].[age_group]
        ON [ase].[age_group] = [age_group].[name]
    LEFT JOIN [inputs].[special_mgras]
        ON [ase].[mgra] = [special_mgras].[mgra15]
        AND [ase].[pop_type] = [special_mgras].[pop_type]
    WHERE [run_id] = @run_id
        AND [special_mgras].[max_age] IS NOT NULL
        AND [lower_bound] > [max_age]
        AND [value] > 0
    GROUP BY [ase].[year], [ase].[mgra], [ase].[pop_type], [max_age]
) AS [error_rows]
ORDER BY [mgra], [metric], [pop_type], [year]