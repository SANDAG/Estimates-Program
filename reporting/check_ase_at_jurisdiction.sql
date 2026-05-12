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
            [jurisdiction],
            'Age Group - ' + [age_group] AS [metric],
            SUM([value]) AS [value]
        FROM [outputs].[ase]
        LEFT JOIN [inputs].[mgra]
            ON [ase].[mgra] = [mgra].[mgra]
            AND [ase].[run_id] = [mgra].[run_id]
        LEFT JOIN [demographic_warehouse].[dim].[mgra] AS [dw_mgra]
            ON [mgra].[mgra] = [dw_mgra].[mgra]
            AND [dw_mgra].[series] = (SELECT [series] FROM [metadata].[run] WHERE [run_id] = @run_id)
        LEFT JOIN [demographic_warehouse].[dim].[mgra_xref]
            ON [dw_mgra].[mgra_id] = [mgra_xref].[mgra_id]
            AND [mgra_xref].[xref_year] = [ase].[year]
        WHERE [ase].[run_id] = @run_id
        GROUP BY [year], [jurisdiction], [age_group]
        
        UNION ALL
        
        SELECT 
            [year],
            [jurisdiction],
            'Sex - ' + [sex] AS [metric],
            SUM([value]) AS [value]
        FROM [outputs].[ase]
        LEFT JOIN [inputs].[mgra]
            ON [ase].[mgra] = [mgra].[mgra]
            AND [ase].[run_id] = [mgra].[run_id]
        LEFT JOIN [demographic_warehouse].[dim].[mgra] AS [dw_mgra]
            ON [mgra].[mgra] = [dw_mgra].[mgra]
            AND [dw_mgra].[series] = (SELECT [series] FROM [metadata].[run] WHERE [run_id] = @run_id)
        LEFT JOIN [demographic_warehouse].[dim].[mgra_xref]
            ON [dw_mgra].[mgra_id] = [mgra_xref].[mgra_id]
            AND [mgra_xref].[xref_year] = [ase].[year]
        WHERE [ase].[run_id] = @run_id
        GROUP BY [year], [jurisdiction], [sex]

        UNION ALL
        
        SELECT 
            [year],
            [jurisdiction],
            'Ethnicity - ' + [ethnicity] AS [metric],
            SUM([value]) AS [value]
        FROM [outputs].[ase]
        LEFT JOIN [inputs].[mgra]
            ON [ase].[mgra] = [mgra].[mgra]
            AND [ase].[run_id] = [mgra].[run_id]
        LEFT JOIN [demographic_warehouse].[dim].[mgra] AS [dw_mgra]
            ON [mgra].[mgra] = [dw_mgra].[mgra]
            AND [dw_mgra].[series] = (SELECT [series] FROM [metadata].[run] WHERE [run_id] = @run_id)
        LEFT JOIN [demographic_warehouse].[dim].[mgra_xref]
            ON [dw_mgra].[mgra_id] = [mgra_xref].[mgra_id]
            AND [mgra_xref].[xref_year] = [ase].[year]
        WHERE [ase].[run_id] = @run_id
        GROUP BY [year], [jurisdiction], [ethnicity]
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
            [jurisdiction],
            'Age Group - ' + [age_group] AS [metric],
            SUM([value]) AS [value]
        FROM [outputs].[ase]
        LEFT JOIN [inputs].[mgra]
            ON [ase].[mgra] = [mgra].[mgra]
            AND [ase].[run_id] = [mgra].[run_id]
        LEFT JOIN [demographic_warehouse].[dim].[mgra] AS [dw_mgra]
            ON [mgra].[mgra] = [dw_mgra].[mgra]
            AND [dw_mgra].[series] = (SELECT [series] FROM [metadata].[run] WHERE [run_id] = @run_id)
        LEFT JOIN [demographic_warehouse].[dim].[mgra_xref]
            ON [dw_mgra].[mgra_id] = [mgra_xref].[mgra_id]
            AND [mgra_xref].[xref_year] = [ase].[year]
        WHERE
            [ase].[run_id] = @run_id
            AND [pop_type] = @pop_type
        GROUP BY [year], [jurisdiction], [age_group]
        
        UNION ALL
        
        SELECT 
            [year],
            [jurisdiction],
            'Sex - ' + [sex] AS [metric],
            SUM([value]) AS [value]
        FROM [outputs].[ase]
        LEFT JOIN [inputs].[mgra]
            ON [ase].[mgra] = [mgra].[mgra]
            AND [ase].[run_id] = [mgra].[run_id]
        LEFT JOIN [demographic_warehouse].[dim].[mgra] AS [dw_mgra]
            ON [mgra].[mgra] = [dw_mgra].[mgra]
            AND [dw_mgra].[series] = (SELECT [series] FROM [metadata].[run] WHERE [run_id] = @run_id)
        LEFT JOIN [demographic_warehouse].[dim].[mgra_xref]
            ON [dw_mgra].[mgra_id] = [mgra_xref].[mgra_id]
            AND [mgra_xref].[xref_year] = [ase].[year]
        WHERE
            [ase].[run_id] = @run_id
            AND [pop_type] = @pop_type
        GROUP BY [year], [jurisdiction], [sex]

        UNION ALL
        
        SELECT 
            [year],
            [jurisdiction],
            'Ethnicity - ' + [ethnicity] AS [metric],
            SUM([value]) AS [value]
        FROM [outputs].[ase]
        LEFT JOIN [inputs].[mgra]
            ON [ase].[mgra] = [mgra].[mgra]
            AND [ase].[run_id] = [mgra].[run_id]
        LEFT JOIN [demographic_warehouse].[dim].[mgra] AS [dw_mgra]
            ON [mgra].[mgra] = [dw_mgra].[mgra]
            AND [dw_mgra].[series] = (SELECT [series] FROM [metadata].[run] WHERE [run_id] = @run_id)
        LEFT JOIN [demographic_warehouse].[dim].[mgra_xref]
            ON [dw_mgra].[mgra_id] = [mgra_xref].[mgra_id]
            AND [mgra_xref].[xref_year] = [ase].[year]
        WHERE
            [ase].[run_id] = @run_id
            AND [pop_type] = @pop_type
        GROUP BY [year], [jurisdiction], [ethnicity]
    ) AS [table]
    ORDER BY [jurisdiction], [metric]
END