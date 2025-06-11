-- Generic SQL script which can be used to check ASE distributions at any generic 
-- geography. Just fill in the values at the top and you will get three tables, one for 
-- each of age, sex, and ethnicity. The geography value must exactly match a column of
-- the table [demographic_warehouse].[dim].[mgra_denormalize]
DECLARE @run_id NVARCHAR(4) = :run_id;
DECLARE @geography NVARCHAR(32) = :geography;
DECLARE @pop_type NVARCHAR(32) = :pop_type;
DECLARE @years NVARCHAR(64) = :years;
DECLARE @series NVARCHAR(4) = '15';
DECLARE @query NVARCHAR(MAX);

-- Since 'Total' is not technically a [pop_type] in [outputs].[ase], we need to do it 
-- separately
IF @pop_type = 'Total'
BEGIN
    SET @query = '
        SELECT *
        FROM (
            SELECT 
                [' + @geography + '],
                ''Age Group - '' + [age_group] AS [metric],
                ' + @years + '
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
                    WHERE [run_id] = ' + @run_id + '
                    GROUP BY [year], [' + @geography + '], [age_group]
                ) AS [grouped]
            PIVOT(
                    SUM([value])
                    FOR [year] IN (' + @years + ')
                ) AS [pivot]
        
            UNION ALL
        
            SELECT 
                [' + @geography + '],
                ''Sex - '' + [sex] AS [metric],
                ' + @years + '
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
                    WHERE [run_id] = ' + @run_id + '
                    GROUP BY [year], [' + @geography + '], [sex]
                ) AS [grouped]
            PIVOT(
                    SUM([value])
                    FOR [year] IN (' + @years + ')
                ) AS [pivot]

            UNION ALL

            SELECT 
                [' + @geography + '],
                ''Ethnicity - '' + [ethnicity] AS [metric],
                ' + @years + '
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
                    WHERE [run_id] = ' + @run_id + '
                    GROUP BY [year], [' + @geography + '], [ethnicity]
                ) AS [grouped]
            PIVOT(
                    SUM([value])
                    FOR [year] IN (' + @years + ')
                ) AS [pivot]
        ) AS [table]
        ORDER BY [' + @geography + '], [metric]';
    EXEC sp_executesql @query;
END

-- All other [pop_type]s can be done together with a simple filter
ELSE
BEGIN
    SET @query = '
        SELECT *
        FROM (
            SELECT 
                [' + @geography + '],
                ''Age Group - '' + [age_group] AS [metric],
                ' + @years + '
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
                    WHERE [run_id] = ' + @run_id + '
                        AND [pop_type] = ''' + @pop_type + '''
                    GROUP BY [year], [' + @geography + '], [age_group]
                ) AS [grouped]
            PIVOT(
                    SUM([value])
                    FOR [year] IN (' + @years + ')
                ) AS [pivot]
        
            UNION ALL

            SELECT 
                [' + @geography + '],
                ''Sex - '' + [sex] AS [metric],
                ' + @years + '
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
                    WHERE [run_id] = ' + @run_id + '
                        AND [pop_type] = ''' + @pop_type + '''
                    GROUP BY [year], [' + @geography + '], [sex]
                ) AS [grouped]
            PIVOT(
                    SUM([value])
                    FOR [year] IN (' + @years + ')
                ) AS [pivot]

            UNION ALL

            SELECT 
                [' + @geography + '],
                ''Ethnicity - '' + [ethnicity] AS [metric],
                ' + @years + '
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
                    WHERE [run_id] = ' + @run_id + '
                        AND [pop_type] = ''' + @pop_type + '''
                    GROUP BY [year], [' + @geography + '], [ethnicity]
                ) AS [grouped]
            PIVOT(
                    SUM([value])
                    FOR [year] IN (' + @years + ')
                ) AS [pivot]
        ) AS [table]
        ORDER BY [' + @geography + '], [metric]';
    EXEC sp_executesql @query;
END