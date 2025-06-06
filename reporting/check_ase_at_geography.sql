-- Generic SQL script which can be used to check ASE distributions at any generic 
-- geography. Just fill in the values at the top and you will get three tables, one for 
-- each of age, sex, and ethnicity. The geography value must exactly match a column of
-- the table [demographic_warehouse].[dim].[mgra_denormalize]
DECLARE @run_id INTEGER = 189;
DECLARE @geography NVARCHAR(32) = 'cpa';
DECLARE @pop_type NVARCHAR(32) = 'Total';
DECLARE @series NVARCHAR(4) = '15';
DECLARE @query NVARCHAR(MAX);

-- Since 'Total' is not technically a [pop_type] in [outputs].[ase], we need to do it 
-- separately
IF @pop_type = 'Total'
BEGIN
    SET @query = '
        SELECT 
            [' + @geography + '],
            [age_group],
            [2020],
            [2021]
        FROM (
                SELECT 
                    [year],
                    [' + @geography + '],
                    [age_group],
                    SUM([value]) AS [value]
                FROM [outputs].[ase]
                LEFT JOIN [demographic_warehouse].[dim].[mgra_denormalize]
                    ON [ase].[mgra] = [mgra_denormalize].[mgra]
                    AND [mgra_denormalize].[series] = ' + @series + '
                WHERE [run_id] = 189
                GROUP BY [year], [' + @geography + '], [age_group]
            ) AS [grouped]
        PIVOT(
                SUM([value])
                FOR [year] IN ([2020], [2021])
            ) AS [pivot]
        ORDER BY [' + @geography + '], [age_group]';
    EXEC sp_executesql @query;

    SET @query = '
        SELECT 
            [' + @geography + '],
            [sex],
            [2020],
            [2021]
        FROM (
                SELECT 
                    [year],
                    [' + @geography + '],
                    [sex],
                    SUM([value]) AS [value]
                FROM [outputs].[ase]
                LEFT JOIN [demographic_warehouse].[dim].[mgra_denormalize]
                    ON [ase].[mgra] = [mgra_denormalize].[mgra]
                    AND [mgra_denormalize].[series] = ' + @series + '
                WHERE [run_id] = 189
                GROUP BY [year], [' + @geography + '], [sex]
            ) AS [grouped]
        PIVOT(
                SUM([value])
                FOR [year] IN ([2020], [2021])
            ) AS [pivot]
        ORDER BY [' + @geography + '], [sex]';
    EXEC sp_executesql @query;

    SET @query = '
        SELECT 
            [' + @geography + '],
            [ethnicity],
            [2020],
            [2021]
        FROM (
                SELECT 
                    [year],
                    [' + @geography + '],
                    [ethnicity],
                    SUM([value]) AS [value]
                FROM [outputs].[ase]
                LEFT JOIN [demographic_warehouse].[dim].[mgra_denormalize]
                    ON [ase].[mgra] = [mgra_denormalize].[mgra]
                    AND [mgra_denormalize].[series] = ' + @series + '
                WHERE [run_id] = 189
                GROUP BY [year], [' + @geography + '], [ethnicity]
            ) AS [grouped]
        PIVOT(
                SUM([value])
                FOR [year] IN ([2020], [2021])
            ) AS [pivot]
        ORDER BY [' + @geography + '], [ethnicity]';
    EXEC sp_executesql @query;
END

-- All other [pop_type]s can be done together with a simple filter
ELSE
BEGIN
    SET @query = '
        SELECT 
            [' + @geography + '],
            [age_group],
            [2020],
            [2021]
        FROM (
                SELECT 
                    [year],
                    [' + @geography + '],
                    [age_group],
                    SUM([value]) AS [value]
                FROM [outputs].[ase]
                LEFT JOIN [demographic_warehouse].[dim].[mgra_denormalize]
                    ON [ase].[mgra] = [mgra_denormalize].[mgra]
                    AND [mgra_denormalize].[series] = ' + @series + '
                WHERE [run_id] = 189
                    AND [pop_type] = ''' + @pop_type + '''
                GROUP BY [year], [' + @geography + '], [age_group]
            ) AS [grouped]
        PIVOT(
                SUM([value])
                FOR [year] IN ([2020], [2021])
            ) AS [pivot]
        ORDER BY [' + @geography + '], [age_group]';
    EXEC sp_executesql @query;

    SET @query = '
        SELECT 
            [' + @geography + '],
            [sex],
            [2020],
            [2021]
        FROM (
                SELECT 
                    [year],
                    [' + @geography + '],
                    [sex],
                    SUM([value]) AS [value]
                FROM [outputs].[ase]
                LEFT JOIN [demographic_warehouse].[dim].[mgra_denormalize]
                    ON [ase].[mgra] = [mgra_denormalize].[mgra]
                    AND [mgra_denormalize].[series] = ' + @series + '
                WHERE [run_id] = 189
                    AND [pop_type] = ''' + @pop_type + '''
                GROUP BY [year], [' + @geography + '], [sex]
            ) AS [grouped]
        PIVOT(
                SUM([value])
                FOR [year] IN ([2020], [2021])
            ) AS [pivot]
        ORDER BY [' + @geography + '], [sex]';
    EXEC sp_executesql @query;

    SET @query = '
        SELECT 
            [' + @geography + '],
            [ethnicity],
            [2020],
            [2021]
        FROM (
                SELECT 
                    [year],
                    [' + @geography + '],
                    [ethnicity],
                    SUM([value]) AS [value]
                FROM [outputs].[ase]
                LEFT JOIN [demographic_warehouse].[dim].[mgra_denormalize]
                    ON [ase].[mgra] = [mgra_denormalize].[mgra]
                    AND [mgra_denormalize].[series] = ' + @series + '
                WHERE [run_id] = 189
                    AND [pop_type] = ''' + @pop_type + '''
                GROUP BY [year], [' + @geography + '], [ethnicity]
            ) AS [grouped]
        PIVOT(
                SUM([value])
                FOR [year] IN ([2020], [2021])
            ) AS [pivot]
        ORDER BY [' + @geography + '], [ethnicity]';
    EXEC sp_executesql @query;
END