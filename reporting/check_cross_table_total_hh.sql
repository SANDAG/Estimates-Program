-- SQL script to check that all total households data in a given [run_id] are
-- consistent between tables
SET NOCOUNT ON;
DECLARE @run_id INTEGER = :run_id;

-- Get MGRA level controls ------------------------------------------------------------
DROP TABLE IF EXISTS [#mgra_hh];
SELECT
    [year],
    [mgra],
    SUM([value]) AS [hh]
INTO [#mgra_hh]
FROM [outputs].[hh]
WHERE [run_id] = @run_id
GROUP BY [year], [mgra]

-- Aggregate populuation and housing characteristics to the MGRA level ----------------
DROP TABLE IF EXISTS [#aggregated_data];
SELECT
    [hh_income].[year],
    [hh_income].[mgra],
    [hh_income].[hh] AS [hh_income],
    [hh_size].[hh] AS [hh_size]
INTO [#aggregated_data]
FROM (
        SELECT
            [year],
            [mgra],
            SUM([value]) AS [hh]
        FROM [outputs].[hh_characteristics]
        WHERE [run_id] = @run_id
            AND [metric] LIKE 'Income Category%'
        GROUP BY [year], [mgra]
    ) AS [hh_income]
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
    ON [hh_income].[year] = [hh_size].[year]
    AND [hh_income].[mgra] = [hh_size].[mgra]

-- Compare controls and aggregated data -----------------------------------------------
SELECT
    [#mgra_hh].[year],
    [#mgra_hh].[mgra],
    [#mgra_hh].[hh] AS [control_hh],
    [#aggregated_data].[hh_income] AS [aggregated_hh_income],
    [#aggregated_data].[hh_size] AS [aggregated_hh_size]
FROM [#mgra_hh]
LEFT JOIN [#aggregated_data]
    ON [#mgra_hh].[year] = [#aggregated_data].[year]
    AND [#mgra_hh].[mgra] = [#aggregated_data].[mgra]
WHERE [#mgra_hh].[hh] != [#aggregated_data].[hh_income]
    OR [#mgra_hh].[hh] != [#aggregated_data].[hh_size]
ORDER BY [#mgra_hh].[mgra], [#mgra_hh].[year]