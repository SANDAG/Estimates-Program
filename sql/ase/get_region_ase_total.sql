-- Initialize parameters -----------------------------------------------------
DECLARE @run_id integer = :run_id;
DECLARE @year integer = :year;


-- Get age/sex/ethnicity controls from California DOF Projections ------------
-- TODO: Implement pre-2020 see https://github.com/SANDAG/CA-DOF/issues/39
with [p3] AS (
    SELECT
        [year],
        CASE 
            WHEN [age] BETWEEN 0 AND 4 THEN 'Under 5'
            WHEN [age] BETWEEN 5 AND 9 THEN '5 to 9'
            WHEN [age] BETWEEN 10 AND 14 THEN '10 to 14'
            WHEN [age] BETWEEN 15 AND 17 THEN '15 to 17'
            WHEN [age] BETWEEN 18 AND 19 THEN '18 and 19'
            WHEN [age] BETWEEN 20 AND 24 THEN '20 to 24'
            WHEN [age] BETWEEN 25 AND 29 THEN '25 to 29'
            WHEN [age] BETWEEN 30 AND 34 THEN '30 to 34'
            WHEN [age] BETWEEN 35 AND 39 THEN '35 to 39'
            WHEN [age] BETWEEN 40 AND 44 THEN '40 to 44'
            WHEN [age] BETWEEN 45 AND 49 THEN '45 to 49'
            WHEN [age] BETWEEN 50 AND 54 THEN '50 to 54'
            WHEN [age] BETWEEN 55 AND 59 THEN '55 to 59'
            WHEN [age] BETWEEN 60 AND 61 THEN '60 and 61'
            WHEN [age] BETWEEN 62 AND 64 THEN '62 to 64'
            WHEN [age] BETWEEN 65 AND 69 THEN '65 to 69'
            WHEN [age] BETWEEN 70 AND 74 THEN '70 to 74'
            WHEN [age] BETWEEN 75 AND 79 THEN '75 to 79'
            WHEN [age] BETWEEN 80 AND 84 THEN '80 to 84'
            WHEN [age] >= 85 THEN '85 and Older'
            ELSE NULL
        END AS [age_group],
        [sex],
        CASE
            WHEN [race/ethnicity] = 'Hispanic (any race)' THEN 'Hispanic'
            WHEN [race/ethnicity] = 'White, Non-Hispanic' THEN 'Non-Hispanic, White'
            WHEN [race/ethnicity] = 'Black, Non-Hispanic' THEN 'Non-Hispanic, Black'
            WHEN [race/ethnicity] = 'American Indian or Alaska Native, Non-Hispanic' THEN 'Non-Hispanic, American Indian or Alaska Native'
            WHEN [race/ethnicity] = 'Asian, Non-Hispanic' THEN 'Non-Hispanic, Asian'
            WHEN [race/ethnicity] = 'Native Hawaiian or Pacific Islander, Non-Hispanic' THEN 'Non-Hispanic, Hawaiian or Pacific Islander'
            WHEN [race/ethnicity] = 'Multiracial (two or more of above races), Non-Hispanic' THEN 'Non-Hispanic, Two or More Races'
            ELSE NULL
        END AS [ethnicity],
        [population]
    FROM [socioec_data].[ca_dof].[projections_p3]
    WHERE 
        [projections_id] = 11  -- Vintage 2025 (2025.4.25)
        AND [fips] = '06073'
        AND [year] = @year
)
SELECT
    @run_id AS [run_id],
    [year],
    [age_group],
    [sex],
    [ethnicity],
    SUM([population]) AS [population]
FROM [p3]
GROUP BY
    [year],
    [age_group],
    [sex],
    [ethnicity]