-- Initialize parameters -----------------------------------------------------
DECLARE @run_id integer = :run_id;
DECLARE @year integer = :year;
DECLARE @series INTEGER = (SELECT [series] FROM [metadata].[run] WHERE [run_id] = @run_id);


-- Get population by type ----------------------------------------------------
WITH [population] AS (
    SELECT
        [mgra],
        [gq_type] AS [pop_type],
        [value]
    FROM [outputs].[gq]
    WHERE
        [run_id] = @run_id
        AND [year] = @year

    UNION ALL

    SELECT
        [mgra],
        'Household Population' AS [pop_type],
        [value]
    FROM [outputs].[hhp]
    WHERE
        [run_id] = @run_id
        AND [year] = @year
)
SELECT
    [population].[mgra],
    [tract],
    [pop_type],
    [value]
FROM [population]
INNER JOIN [demographic_warehouse].[dim].[mgra]
    ON [population].[mgra] = [mgra].[mgra]
    AND [mgra].[series] = @series
INNER JOIN [demographic_warehouse].[dim].[mgra_xref]
    ON [mgra].[mgra_id] = [mgra_xref].[mgra_id]
    AND [mgra_xref].[xref_year] = @year
ORDER BY
    [population].[mgra],
    [pop_type];