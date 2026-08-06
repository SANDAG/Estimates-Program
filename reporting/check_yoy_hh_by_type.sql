-- SQL script to get households aggregated to some geography
DECLARE @run_id NVARCHAR(MAX) = :run_id;
DECLARE @series NVARCHAR(MAX) = :series;
DECLARE @geography NVARCHAR(MAX) = :geography;

DECLARE @query NVARCHAR(MAX) = '
    SELECT
        [year],
        [' + @geography + '],
        ''Households - '' + [structure_type] AS [metric],
        SUM([value]) AS [value]
    FROM [outputs].[hh]
    INNER JOIN [demographic_warehouse].[dim].[vi_mgra_denormalize]
        ON [hh].[year] = [vi_mgra_denormalize].[xref_year]
        AND [hh].[mgra] = [vi_mgra_denormalize].[mgra]
        AND [vi_mgra_denormalize].[series] = ' + @series + '
    WHERE [hh].[run_id] = ' + @run_id + '
    GROUP BY [year], [' + @geography + '], [structure_type]
    ORDER BY [year], [' + @geography + '], [metric]'
EXEC sp_executesql @query;
