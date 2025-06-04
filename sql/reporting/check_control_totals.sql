-- SQL script to check that all data in a given [run_id] matches control totals
DECLARE @run_id INTEGER = 189;

-- The threshold variable determines how far away the aggregated occupancy rate must be
-- from the control occupancy rate to raise an error
DECLARE @threshold FLOAT = .01;

-- Get non-ASE city level controls from the DOF ---------------------------------------
DROP TABLE IF EXISTS [#dof_controls];
SELECT *
INTO [#dof_controls]
FROM (
	-- E-8 Estimates - 2010-2019
	SELECT
		[year],
		CASE 
            WHEN [area_name] = 'Balance of County' THEN 'Unincorporated'
			ELSE [area_name]  
        END AS [city],
        [household_population],
        [group_quarters],
        1 - [vacancy_rate] AS [occupancy_rate]
	FROM [socioec_data].[ca_dof].[estimates_e8]
	WHERE
		[estimates_id] = 24  -- E-8: January 2025
		AND [fips] = '06073'  -- San Diego County
		AND [year] != 2020  -- Use the E-5 Estimates for 2020+
		AND [area_name] NOT IN ('Total Incorporated' , 'Incorporated', 'County Total')

	UNION ALL

	-- E-5 Estimates - 2020+
	SELECT
		[year],
		CASE
            WHEN [area_name] = 'Balance of County' THEN 'Unincorporated'
            WHEN [area_name] = 'National City' THEN 'National City'
			ELSE REPLACE([area_name], ' City', '')
        END AS [city],
        [household_population],
        [group_quarters],
        1 - [vacancy_rate] AS [occupancy_rate]
	FROM [socioec_data].[ca_dof].[estimates_e5]
	WHERE
		[estimates_id] = 25  -- E-5: Vintage 2025 (2025.5.1)
		AND [fips] = '06073'  -- San Diego County
		AND [area_name] NOT IN ('Total Incorporated' , 'Incorporated', 'County Total')
) AS [dof];

-- Get all data for the city level controls aggregated to the city level --------------
DROP TABLE IF EXISTS [#aggregated_data];
WITH [mgra_hhp] AS (
        SELECT 
            [year],
            [mgra],
            SUM([value]) AS [household_population]
        FROM [outputs].[hhp]
        WHERE [run_id] = @run_id
        GROUP BY [year], [mgra]
    ),
    [mgra_gq] AS (
        SELECT 
            [year],
            [mgra],
            SUM([value]) AS [group_quarters]
        FROM [outputs].[gq]
        WHERE [run_id] = @run_id
        GROUP BY [year], [mgra]
    ),
    [mgra_hs] AS (
        SELECT 
            [year],
            [mgra],
            SUM([value]) AS [housing_stock]
        FROM [outputs].[hs]
        WHERE [run_id] = @run_id
        GROUP BY [year], [mgra]
    ),
    [mgra_hh] AS (
        SELECT 
            [year],
            [mgra],
            SUM([value]) AS [households]
        FROM [outputs].[hh]
        WHERE [run_id] = @run_id
        GROUP BY [year], [mgra]
    )
SELECT 
    [mgra_hhp].[year],
    [cities_2020] AS [city],
    SUM([household_population]) AS [household_population],
    SUM([group_quarters]) AS [group_quarters],
    1.0 * SUM([households]) / SUM([housing_stock]) AS [occupancy_rate]
INTO [#aggregated_data]
FROM [mgra_hhp]
LEFT JOIN [mgra_gq]
    ON [mgra_hhp].[year] = [mgra_gq].[year]
    AND [mgra_hhp].[mgra] = [mgra_gq].[mgra]
LEFT JOIN [mgra_hs]
    ON [mgra_hhp].[year] = [mgra_hs].[year]
    AND [mgra_hhp].[mgra] = [mgra_hs].[mgra]
LEFT JOIN [mgra_hh]
    ON [mgra_hhp].[year] = [mgra_hh].[year]
    AND [mgra_hhp].[mgra] = [mgra_hh].[mgra]
LEFT JOIN [inputs].[mgra]
    ON [mgra_hhp].[mgra] = [mgra].[mgra]
    AND [mgra].[run_id] = @run_id
GROUP BY [mgra_hhp].[year], [cities_2020]

-- Compare controls and aggregated data -----------------------------------------------
SELECT 
    [#aggregated_data].[year],
    [#aggregated_data].[city],
    [#aggregated_data].[household_population] AS [aggregated_hhp],
    [#dof_controls].[household_population] AS [control_hhp],
    [#dof_controls].[group_quarters] AS [control_gq],
    [#aggregated_data].[group_quarters] AS [aggregated_gq],
    [#aggregated_data].[occupancy_rate] AS [aggregated_occ_rate],
    [#dof_controls].[occupancy_rate] AS [control_occ_rate]
FROM [#aggregated_data]
LEFT JOIN [#dof_controls]
    ON [#aggregated_data].[year] = [#dof_controls].[year]
    AND [#aggregated_data].[city] = [#dof_controls].[city]
WHERE [#aggregated_data].[household_population] != [#dof_controls].[household_population]
    OR [#aggregated_data].[group_quarters] != [#dof_controls].[group_quarters]
    OR ABS([#aggregated_data].[occupancy_rate] - [#dof_controls].[occupancy_rate]) > @threshold