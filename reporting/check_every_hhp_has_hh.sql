-- SQL script to check that all household population has a household
DECLARE @run_id INTEGER = :run_id;

SELECT
    [hh].[year],
    [hh].[mgra]
    [hh],
    [hhp]
FROM (
        SELECT
            [year],
            [mgra],
            SUM([value]) AS [hh]
        FROM [outputs].[hh]
        WHERE [run_id] = @run_id
        GROUP BY [year], [mgra]
    ) AS [hh]
LEFT JOIN (
        SELECT
            [year],
            [mgra],
            [value] AS [hhp]
        FROM [outputs].[hhp]
        WHERE [run_id] = @run_id
    ) AS [hhp]
    ON [hh].[year] = [hhp].[year]
    AND [hh].[mgra] = [hhp].[mgra]
WHERE [hh] > [hhp]
ORDER BY [hh].[year], [hh].[mgra]
