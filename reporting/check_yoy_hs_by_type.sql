-- SQL script to get housing units aggregated to some geography
DECLARE @run_id NVARCHAR(MAX) = :run_id;
DECLARE @series NVARCHAR(MAX) = :series;
DECLARE @geography NVARCHAR(MAX) = :geography;

DECLARE @query NVARCHAR(MAX) = '
    SELECT
        [year],
        [' + @geography + '],
        ''Housing Units - '' + [structure_type] AS [metric],
        SUM([value]) AS [value]
    FROM [outputs].[hs]
    INNER JOIN [demographic_warehouse].[dim].[vi_mgra_denormalize]
        ON [hs].[year] = [vi_mgra_denormalize].[xref_year]
        AND [hs].[mgra] = [vi_mgra_denormalize].[mgra]
        AND [vi_mgra_denormalize].[series] = ' + @series + '
    WHERE [hs].[run_id] = ' + @run_id + '
    GROUP BY [year], [' + @geography + '], [structure_type]
    ORDER BY [year], [' + @geography + '], [metric]'
EXEC sp_executesql @query;
