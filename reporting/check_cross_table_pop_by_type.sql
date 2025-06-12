-- SQL script to check that all population by type data in a given [run_id] are
-- consistent between tables. Basically, check that the total population of each type
-- at the MGRA level match between totals in [outputs].[hhp]/[outputs].[gq] and ASE
-- in [outputs].[ase]
SET NOCOUNT ON;
DECLARE @run_id INTEGER = :run_id;

-- Get MGRA level controls ------------------------------------------------------------
DROP TABLE IF EXISTS [#mgra_controls]
SELECT 
    [hhp].[year],
    [hhp].[mgra],
    [hhp].[value] AS [hhp],
    [gq_college],
    [gq_miltary],
    [gq_prison],
    [gq_other]
INTO [#mgra_controls]
FROM [outputs].[hhp]
LEFT JOIN (
        SELECT 
            [run_id],
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
    ) AS [gq]
    ON [hhp].[run_id] = [gq].[run_id]
    AND [hhp].[year] = [gq].[year]
    AND [hhp].[mgra] = [gq].[mgra]
WHERE [hhp].[run_id] = @run_id

-- Aggregate population and housing characteristics to the MGRA level -----------------
DROP TABLE IF EXISTS [#aggregated_data];
SELECT
    [year],
    [mgra],
    SUM([Household Population]) AS [hhp],
    SUM([Group Quarters - College]) AS [gq_college],
    SUM([Group Quarters - Military]) AS [gq_miltary],
    SUM([Group Quarters - Institutional Correctional Facilities]) AS [gq_prison],
    SUM([Group Quarters - Other]) AS [gq_other]
INTO [#aggregated_data]
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

-- Compare controls and aggregated data -----------------------------------------------
SELECT 
    [#mgra_controls].[year],
    [#mgra_controls].[mgra],
    [#mgra_controls].[hhp] AS [control_hhp],
    [#aggregated_data].[hhp] AS [aggregated_hhp],
    [#mgra_controls].[gq_college] AS [control_gq_college],
    [#aggregated_data].[gq_college] AS [aggregated_gq_college],
    [#mgra_controls].[gq_miltary] AS [control_gq_miltary],
    [#aggregated_data].[gq_miltary] AS [aggregated_gq_miltary],
    [#mgra_controls].[gq_prison] AS [control_gq_prison],
    [#aggregated_data].[gq_prison] AS [aggregated_gq_prison],
    [#mgra_controls].[gq_other] AS [control_gq_other],
    [#aggregated_data].[gq_other] AS [aggregated_gq_other]
FROM [#mgra_controls]
LEFT JOIN [#aggregated_data]
    ON [#mgra_controls].[year] = [#aggregated_data].[year]
    AND [#mgra_controls].[mgra] = [#aggregated_data].[mgra]
WHERE [#mgra_controls].[hhp] != [#aggregated_data].[hhp]
    OR [#mgra_controls].[gq_college] != [#aggregated_data].[gq_college]
    OR [#mgra_controls].[gq_miltary] != [#aggregated_data].[gq_miltary]
    OR [#mgra_controls].[gq_prison] != [#aggregated_data].[gq_prison]
    OR [#mgra_controls].[gq_other] != [#aggregated_data].[gq_other]
ORDER BY [#mgra_controls].[mgra], [#mgra_controls].[year]