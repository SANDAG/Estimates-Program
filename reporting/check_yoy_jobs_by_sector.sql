-- SQL script to get jobs aggregated to some geography
DECLARE @run_id NVARCHAR(MAX) = :run_id;
DECLARE @series NVARCHAR(MAX) = :series;
DECLARE @geography NVARCHAR(MAX) = :geography;

DECLARE @query NVARCHAR(MAX) = '
    SELECT
        [year],
        [' + @geography + '],
        [ownership_title] + ''/'' + [industry_code] AS [metric],
        SUM([value]) AS [value]
    FROM [outputs].[jobs]
    INNER JOIN [demographic_warehouse].[dim].[vi_mgra_denormalize]
        ON [jobs].[year] = [vi_mgra_denormalize].[xref_year]
        AND [jobs].[mgra] = [vi_mgra_denormalize].[mgra]
        AND [vi_mgra_denormalize].[series] = ' + @series + '
    WHERE [jobs].[run_id] = ' + @run_id + '
    GROUP BY [year], [' + @geography + '], [ownership_title] + ''/'' + [industry_code]
    ORDER BY [year], [' + @geography + '], [metric]'
EXEC sp_executesql @query;
