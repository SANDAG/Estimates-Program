-- Initialize parameters -----------------------------------------------------
DECLARE @run_id integer = :run_id;
DECLARE @year integer = :year;


-- Get households by MGRA ----------------------------------------------------
SELECT
    [mgra],
    SUM([value]) AS [value]
FROM [outputs].[hh]
WHERE
    [run_id] = @run_id
    AND [year] = @year
GROUP BY [mgra]