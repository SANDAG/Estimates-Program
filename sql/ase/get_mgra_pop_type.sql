-- Initialize parameters -----------------------------------------------------
DECLARE @run_id integer = :run_id;
DECLARE @year integer = :year;


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
INNER JOIN [inputs].[mgra]
    ON [mgra].[run_id] = @run_id
    AND [population].[mgra] = [mgra].[mgra]
INNER JOIN [demographic_warehouse].[dim].[mgra] AS [dw_mgra]
    ON [mgra].[mgra] = [dw_mgra].[mgra]
    AND [dw_mgra].[series] = (SELECT [series] FROM [metadata].[run] WHERE [run_id] = @run_id)
INNER JOIN [demographic_warehouse].[dim].[mgra_xref]
    ON [dw_mgra].[mgra_id] = [mgra_xref].[mgra_id]
    AND [mgra_xref].[xref_year] = @year