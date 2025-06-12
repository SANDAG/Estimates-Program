-- SQL Script to check that MGRA level ASE data exactly matches regional ASE controls
DECLARE @run_id INTEGER = 239;

SELECT 
    [controls_ase].[year],
    [controls_ase].[pop_type],
    [controls_ase].[age_group],
    [controls_ase].[sex],
    [controls_ase].[ethnicity],
    [controls_ase].[value] AS [control],
    [aggregated_data].[value] AS [actual]
FROM [inputs].[controls_ase]
LEFT JOIN (
        SELECT 
            [year],
            [pop_type],
            [age_group],
            [sex],
            [ethnicity],
            SUM([value]) AS [value]
        FROM [outputs].[ase]
        WHERE [run_id] = @run_id
        GROUP BY [year], [pop_type], [age_group], [sex], [ethnicity]
    ) AS [aggregated_data]
    ON [aggregated_data].[year] = [controls_ase].[year]
    AND [aggregated_data].[pop_type] = [controls_ase].[pop_type]
    AND [aggregated_data].[age_group] = [controls_ase].[age_group]
    AND [aggregated_data].[sex] = [controls_ase].[sex]
    AND [aggregated_data].[ethnicity] = [controls_ase].[ethnicity]
WHERE [run_id] = @run_id
    AND [controls_ase].[value] != [aggregated_data].[value]