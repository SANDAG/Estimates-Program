-- Initialize parameters -----------------------------------------------------
DECLARE @run_id integer = :run_id;
DECLARE @year integer = :year;


-- Get household population controls from California DOF Estimates -----------------
with [dof] AS (
    -- E-8 Estimates - 2010-2019
    SELECT
        [year],
        CASE
            WHEN [area_name] = 'Balance of County' THEN 'Unincorporated'
            ELSE [area_name]
        END AS [city],
        [household_population]
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
        [household_population]
    FROM [socioec_data].[ca_dof].[estimates_e5]
    WHERE
        [estimates_id] = 25  -- E-5: Vintage 2025 (2025.5.1)
        AND [fips] = '06073'  -- San Diego County
        AND [area_name] NOT IN ('Total Incorporated' , 'Incorporated', 'County Total')
)
SELECT
    @run_id AS [run_id],
    @year AS [year],
    [city],
    'Household Population' AS [metric],
    [household_population] AS [value]
FROM [dof]
WHERE [year] = @year