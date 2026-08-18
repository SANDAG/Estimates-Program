-- SQL Script to check that MGRA level jobs exactly matches regional jobs controls
DECLARE @run_id INTEGER = :run_id;

SELECT 
    [controls_jobs].[year],
    [controls_jobs].[ownership_title],
    [controls_jobs].[industry_code],
    [controls_jobs].[value] AS [control],
    [aggregated_data].[value] AS [actual]
FROM [inputs].[controls_jobs]
LEFT OUTER JOIN (
    SELECT 
        [year],
        [ownership_title],
        [industry_code],
        SUM([value]) AS [value]
    FROM [outputs].[jobs]
    WHERE [run_id] = @run_id
    GROUP BY
        [year],
        [ownership_title],
        [industry_code]
) AS [aggregated_data]
    ON [controls_jobs].[year] = [aggregated_data].[year]
    AND [controls_jobs].[ownership_title] = [aggregated_data].[ownership_title]
    AND [controls_jobs].[industry_code] = [aggregated_data].[industry_code]
WHERE
    [run_id] = @run_id
    AND [controls_jobs].[value] != [aggregated_data].[value]