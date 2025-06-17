-- SQL scrip to get ASE population aggregated at the city level, based on the input
-- population type
DECLARE @run_id INTEGER = :run_id;
DECLARE @pop_type NVARCHAR(32) = :pop_type;

-- Since 'Total' is not technically a [pop_type] in [outputs].[ase], we need to do it 
-- separately
IF @pop_type = 'Total'
BEGIN
    SELECT *
    FROM (
        SELECT 
            [year],
            [cities_2020] AS [jurisdiction],
            'Age Group - ' + [age_group] AS [metric],
            SUM([value]) AS [value]
        FROM [outputs].[ase]
        LEFT JOIN [inputs].[mgra]
            ON [ase].[mgra] = [mgra].[mgra]
            AND [ase].[run_id] = [mgra].[run_id]
        WHERE [ase].[run_id] = @run_id
        GROUP BY [year], [cities_2020], [age_group]
        
        UNION ALL
        
        SELECT 
            [year],
            [cities_2020] AS [jurisdiction],
            'Sex - ' + [sex] AS [metric],
            SUM([value]) AS [value]
        FROM [outputs].[ase]
        LEFT JOIN [inputs].[mgra]
            ON [ase].[mgra] = [mgra].[mgra]
            AND [ase].[run_id] = [mgra].[run_id]
        WHERE [ase].[run_id] = @run_id
        GROUP BY [year], [cities_2020], [sex]

        UNION ALL
        
        SELECT 
            [year],
            [cities_2020] AS [jurisdiction],
            'Ethnicity - ' + [ethnicity] AS [metric],
            SUM([value]) AS [value]
        FROM [outputs].[ase]
        LEFT JOIN [inputs].[mgra]
            ON [ase].[mgra] = [mgra].[mgra]
            AND [ase].[run_id] = [mgra].[run_id]
        WHERE [ase].[run_id] = @run_id
        GROUP BY [year], [cities_2020], [ethnicity]
    ) AS [table]
    ORDER BY [jurisdiction], [metric]
END

-- All other [pop_type]s can be done together with a simple filter
ELSE
BEGIN
    SELECT *
    FROM (
        SELECT 
            [year],
            [cities_2020] AS [jurisdiction],
            'Age Group - ' + [age_group] AS [metric],
            SUM([value]) AS [value]
        FROM [outputs].[ase]
        LEFT JOIN [inputs].[mgra]
            ON [ase].[mgra] = [mgra].[mgra]
            AND [ase].[run_id] = [mgra].[run_id]
        WHERE [ase].[run_id] = @run_id
            AND [pop_type] = @pop_type
        GROUP BY [year], [cities_2020], [age_group]
        
        UNION ALL
        
        SELECT 
            [year],
            [cities_2020] AS [jurisdiction],
            'Sex - ' + [sex] AS [metric],
            SUM([value]) AS [value]
        FROM [outputs].[ase]
        LEFT JOIN [inputs].[mgra]
            ON [ase].[mgra] = [mgra].[mgra]
            AND [ase].[run_id] = [mgra].[run_id]
        WHERE [ase].[run_id] = @run_id
            AND [pop_type] = @pop_type
        GROUP BY [year], [cities_2020], [sex]

        UNION ALL
        
        SELECT 
            [year],
            [cities_2020] AS [jurisdiction],
            'Ethnicity - ' + [ethnicity] AS [metric],
            SUM([value]) AS [value]
        FROM [outputs].[ase]
        LEFT JOIN [inputs].[mgra]
            ON [ase].[mgra] = [mgra].[mgra]
            AND [ase].[run_id] = [mgra].[run_id]
        WHERE [ase].[run_id] = @run_id
            AND [pop_type] = @pop_type
        GROUP BY [year], [cities_2020], [ethnicity]
    ) AS [table]
    ORDER BY [jurisdiction], [metric]
END