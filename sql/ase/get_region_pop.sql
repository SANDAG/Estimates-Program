-- Initialize parameters -----------------------------------------------------
DECLARE @run_id integer = :run_id;
DECLARE @year integer = :year;


-- Get total population by type ----------------------------------------------
SELECT 
    [gq_type] AS [pop_type],
    SUM([value]) AS [value]
FROM [outputs].[gq]
WHERE
    [run_id] = @run_id
    AND [year] = @year
GROUP BY [gq_type]
    UNION ALL
SELECT
    'Household Population' AS [pop_type],
    SUM([value]) AS [value]
FROM [outputs].[hhp]
WHERE
    [run_id] = @run_id
    AND [year] = @year