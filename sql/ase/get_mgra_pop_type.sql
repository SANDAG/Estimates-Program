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
    CASE
        WHEN @year BETWEEN 2010 AND 2019 THEN [2010_census_tract]
        WHEN @year BETWEEN 2020 AND 2029 THEN [2020_census_tract]
        ELSE NULL
    END AS [tract],
    [pop_type],
    [value]
FROM [population]
INNER JOIN [inputs].[mgra]
    ON [mgra].[run_id] = @run_id
    AND [population].[mgra] = [mgra].[mgra]