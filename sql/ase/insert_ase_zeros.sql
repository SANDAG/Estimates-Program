DECLARE @run_id INTEGER = :run_id;
DECLARE @year INTEGER = :year;
DECLARE @series INTEGER = :series;

DROP TABLE IF EXISTS [#shell];
SELECT *, 0 AS [value]
INTO [#shell]
FROM (VALUES(@run_id)) AS [run_id]([run_id])
CROSS JOIN (VALUES(@year)) AS [year]([year])
CROSS JOIN (
        SELECT DISTINCT [mgra]
        FROM [demographic_warehouse].[dim].[mgra]
        WHERE [series] = @series
) AS [mgra]
CROSS JOIN (
        SELECT DISTINCT [long_name] AS [pop_type]
        FROM [demographic_warehouse].[dim].[housing_type]
        WHERE [housing_type_id] IN (1, 2, 3, 4, 6) -- Skip 'Group Quarters - Civilian'
) AS [pop_type]
CROSS JOIN (
        SELECT DISTINCT [name] AS [age_group]
        FROM [demographic_warehouse].[dim].[age_group]
        WHERE [age_group_id] BETWEEN 1 AND 20
    ) AS [age_group]
CROSS JOIN (
        SELECT DISTINCT [sex]
        FROM [demographic_warehouse].[dim].[sex]
        WHERE [sex_id] IN (1, 2)
    ) AS [sex]
CROSS JOIN (
        SELECT DISTINCT [long_name] AS [ethnicity]
        FROM [demographic_warehouse].[dim].[ethnicity]
        WHERE [ethnicity_id] IN (1, 2, 3, 4, 5, 6, 8) -- Skip 'Non-Hispanic, Other'
    ) AS [ethnicity]

INSERT INTO [EstimatesProgram].[outputs].[ase]
SELECT
    [#shell].[run_id],
    [#shell].[year],
    [#shell].[mgra],
    [#shell].[pop_type],
    [#shell].[age_group],
    [#shell].[sex],
    [#shell].[ethnicity],
    [#shell].[value]
FROM [#shell]
LEFT JOIN [EstimatesProgram].[outputs].[ase]
    ON [#shell].[run_id] = [ase].[run_id]
    AND [#shell].[year] = [ase].[year]
    AND [#shell].[mgra] = [ase].[mgra]
    AND [#shell].[pop_type] = [ase].[pop_type]
    AND [#shell].[age_group] = [ase].[age_group]
    AND [#shell].[sex] = [ase].[sex]
    AND [#shell].[ethnicity] = [ase].[ethnicity]
WHERE [ase].[value] IS NULL
