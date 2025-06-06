-- SQL script to check that all data in a given [run_id] are consistent between tables.
-- For example, the total household poulation in each MGRA should match between the 
-- tables [outputs].[hhp] and [outputs].[ase]. The specific variables compared are
-- population by type and total households
DECLARE @run_id INTEGER = :run_id;

-- Get MGRA level controls ------------------------------------------------------------
WITH [mgra_controls] AS (
        SELECT 
            [hhp].[year],
            [hhp].[mgra],
            [hhp].[value] AS [hhp],
            [gq_college],
            [gq_miltary],
            [gq_prison],
            [gq_other],
            [hh]
        FROM [outputs].[hhp]
        LEFT JOIN (
                SELECT 
                    [year],
                    [mgra],
                    [Group Quarters - College] AS [gq_college], 
                    [Group Quarters - Military] AS [gq_miltary],
                    [Group Quarters - Institutional Correctional Facilities] AS [gq_prison],
                    [Group Quarters - Other] AS [gq_other]
                FROM [outputs].[gq]
                PIVOT (
                    SUM([value]) 
                    FOR [gq_type] IN (
                        [Group Quarters - College], 
                        [Group Quarters - Military],
                        [Group Quarters - Institutional Correctional Facilities],
                        [Group Quarters - Other])
                    ) AS [pivot]
                WHERE [run_id] = @run_id
            ) AS [gq]
            ON [hhp].[year] = [gq].[year]
            AND [hhp].[mgra] = [gq].[mgra]
        LEFT JOIN (
                SELECT 
                    [year],
                    [mgra],
                    SUM([value]) AS [hh]
                FROM [outputs].[hh]
                WHERE [run_id] = @run_id
                GROUP BY [year], [mgra]
            ) AS [hh]
            ON [hhp].[year] = [hh].[year]
            AND [hhp].[mgra] = [hh].[mgra]
        WHERE [run_id] = @run_id
    ),

    -- Aggregate populuation and housing characteristics to the MGRA level ------------
    [aggregated_data] AS (
        SELECT 
            [pop].[year],
            [pop].[mgra],
            [pop].[hhp],
            [pop].[gq_college],
            [pop].[gq_miltary],
            [pop].[gq_prison],
            [pop].[gq_other],
            [hh_income].[hh] AS [hh_income],
            [hh_size].[hh] AS [hh_size]
        FROM (
                SELECT 
                    [year],
                    [mgra],
                    SUM([Household Population]) AS [hhp], 
                    SUM([Group Quarters - College]) AS [gq_college], 
                    SUM([Group Quarters - Military]) AS [gq_miltary],
                    SUM([Group Quarters - Institutional Correctional Facilities]) AS [gq_prison],
                    SUM([Group Quarters - Other]) AS [gq_other]
                FROM [outputs].[ase]
                PIVOT (
                    SUM([value]) 
                    FOR [pop_type] IN (
                        [Household Population],
                        [Group Quarters - College], 
                        [Group Quarters - Military],
                        [Group Quarters - Institutional Correctional Facilities],
                        [Group Quarters - Other])
                    ) AS [pivot]
                WHERE [run_id] = @run_id
                GROUP BY [year], [mgra]
            ) AS [pop]
        LEFT JOIN (
                SELECT 
                    [year],
                    [mgra],
                    SUM([value]) AS [hh]
                FROM [outputs].[hh_characteristics]
                WHERE [run_id] = @run_id
                    AND [metric] LIKE 'Income Category%'
                GROUP BY [year], [mgra]
            ) AS [hh_income]
            ON [pop].[year] = [hh_income].[year]
            AND [pop].[mgra] = [hh_income].[mgra]
        LEFT JOIN (
                SELECT 
                    [year],
                    [mgra],
                    SUM([value]) AS [hh]
                FROM [outputs].[hh_characteristics]
                WHERE [run_id] = @run_id
                    AND [metric] LIKE 'Household Size%'
                GROUP BY [year], [mgra]
            ) AS [hh_size]
            ON [pop].[year] = [hh_size].[year]
            AND [pop].[mgra] = [hh_size].[mgra]
    )

-- Compare controls and aggregated data -----------------------------------------------
SELECT 
    [mgra_controls].[year],
    [mgra_controls].[mgra],
    [mgra_controls].[hhp] AS [control_hhp],
    [aggregated_data].[hhp] AS [aggregated_hhp],
    [mgra_controls].[gq_college] AS [control_gq_college],
    [aggregated_data].[gq_college] AS [aggregated_gq_college],
    [mgra_controls].[gq_miltary] AS [control_gq_miltary],
    [aggregated_data].[gq_miltary] AS [aggregated_gq_miltary],
    [mgra_controls].[gq_prison] AS [control_gq_prison],
    [aggregated_data].[gq_prison] AS [aggregated_gq_prison],
    [mgra_controls].[gq_other] AS [control_gq_other],
    [aggregated_data].[gq_other] AS [aggregated_gq_other],
    [mgra_controls].[hh] AS [control_hh],
    [aggregated_data].[hh_income] AS [aggregated_hh_income],
    [aggregated_data].[hh_size] AS [aggregated_hh_size]
FROM [mgra_controls]
LEFT JOIN [aggregated_data]
    ON [mgra_controls].[year] = [aggregated_data].[year]
    AND [mgra_controls].[mgra] = [aggregated_data].[mgra]
WHERE [mgra_controls].[hhp] != [aggregated_data].[hhp]
    OR [mgra_controls].[gq_college] != [aggregated_data].[gq_college]
    OR [mgra_controls].[gq_miltary] != [aggregated_data].[gq_miltary]
    OR [mgra_controls].[gq_prison] != [aggregated_data].[gq_prison]
    OR [mgra_controls].[gq_other] != [aggregated_data].[gq_other]
    OR [mgra_controls].[hh] != [aggregated_data].[hh_income]
    OR [mgra_controls].[hh] != [aggregated_data].[hh_size]
ORDER BY [mgra_controls].[mgra], [mgra_controls].[year]