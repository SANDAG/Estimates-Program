-- SQL script to get population aggregated to some geography
DECLARE @run_id NVARCHAR(MAX) = :run_id;
DECLARE @series NVARCHAR(MAX) = :series;
DECLARE @geography NVARCHAR(MAX) = :geography;

DECLARE @query NVARCHAR(MAX) = '
    SELECT *
    FROM (
        SELECT
            [year],
            [' + @geography + '],
            ''Household Population'' AS [metric],
            SUM([value]) AS [value]
        FROM [outputs].[hhp]
        INNER JOIN [demographic_warehouse].[dim].[vi_mgra_denormalize]
            ON [hhp].[year] = [vi_mgra_denormalize].[xref_year]
            AND [hhp].[mgra] = [vi_mgra_denormalize].[mgra]
            AND [vi_mgra_denormalize].[series] = ' + @series + '
        WHERE [hhp].[run_id] = ' + @run_id + '
        GROUP BY [year], [' + @geography + ']

        UNION ALL
        
        SELECT
            [year],
            [' + @geography + '],
            [gq_type] AS [metric],
            SUM([value]) AS [value]
        FROM [outputs].[gq]
        INNER JOIN [demographic_warehouse].[dim].[vi_mgra_denormalize]
            ON [gq].[year] = [vi_mgra_denormalize].[xref_year]
            AND [gq].[mgra] = [vi_mgra_denormalize].[mgra]
            AND [vi_mgra_denormalize].[series] = ' + @series + '
        WHERE [gq].[run_id] = ' + @run_id + '
        GROUP BY [year], [' + @geography + '], [gq_type]
    ) AS [table]
    ORDER BY [year], [' + @geography + '], [metric]'
EXEC sp_executesql @query;
