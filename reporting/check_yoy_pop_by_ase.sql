-- SQL script to get population by age/sex/ethnicity aggregated to some geography
DECLARE @run_id NVARCHAR(MAX) = :run_id;
DECLARE @series NVARCHAR(MAX) = :series;
DECLARE @geography NVARCHAR(MAX) = :geography;

DECLARE @query NVARCHAR(MAX) = '
    SELECT *
    FROM (
        SELECT
            [year],
            [' + @geography + '],
            ''Age Group - '' + [age_group] AS [metric],
            SUM([value]) AS [value]
        FROM [outputs].[ase]
        INNER JOIN [demographic_warehouse].[dim].[vi_mgra_denormalize]
            ON [ase].[year] = [vi_mgra_denormalize].[xref_year]
            AND [ase].[mgra] = [vi_mgra_denormalize].[mgra]
            AND [vi_mgra_denormalize].[series] = ' + @series + '
        WHERE [ase].[run_id] = ' + @run_id + '
        GROUP BY [year], [' + @geography + '], [age_group]

        UNION ALL

        SELECT
            [year],
            [' + @geography + '],
            ''Sex - '' + [sex] AS [metric],
            SUM([value]) AS [value]
        FROM [outputs].[ase]
        INNER JOIN [demographic_warehouse].[dim].[vi_mgra_denormalize]
            ON [ase].[year] = [vi_mgra_denormalize].[xref_year]
            AND [ase].[mgra] = [vi_mgra_denormalize].[mgra]
            AND [vi_mgra_denormalize].[series] = ' + @series + '
        WHERE [ase].[run_id] = ' + @run_id + '
        GROUP BY [year], [' + @geography + '], [sex]

        UNION ALL

        SELECT
            [year],
            [' + @geography + '],
            ''Ethnicity - '' + [ethnicity] AS [metric],
            SUM([value]) AS [value]
        FROM [outputs].[ase]
        INNER JOIN [demographic_warehouse].[dim].[vi_mgra_denormalize]
            ON [ase].[year] = [vi_mgra_denormalize].[xref_year]
            AND [ase].[mgra] = [vi_mgra_denormalize].[mgra]
            AND [vi_mgra_denormalize].[series] = ' + @series + '
        WHERE [ase].[run_id] = ' + @run_id + '
        GROUP BY [year], [' + @geography + '], [ethnicity]
    ) AS [table]
    ORDER BY [year], [' + @geography + '], [metric]'
EXEC sp_executesql @query;
