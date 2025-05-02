/*
Pull population by ethnicity using the B03002 table for a given ACS 5-Year survey.
This data provides Hispanic/Non-Hispanic ethnicity groups for use in age/sex/ethnicity seed generation.
*/

-- Initialize parameters -----------------------------------------------------
DECLARE @year integer = :year;


-- Get ACS 5-Year B03002 -----------------------------------------------------
SELECT
    [tract],
    [ethnicity],
    SUM([value]) AS [value]
FROM (
    SELECT
        [tract],
        CASE    
            WHEN REPLACE([variables].[label], ':', '') = 'Estimate!!Total!!Hispanic or Latino' THEN 'Hispanic'
            WHEN REPLACE([variables].[label], ':', '') = 'Estimate!!Total!!Not Hispanic or Latino!!White alone' THEN 'Non-Hispanic, White'
            WHEN REPLACE([variables].[label], ':', '') = 'Estimate!!Total!!Not Hispanic or Latino!!Black or African American alone' THEN 'Non-Hispanic, Black'
            WHEN REPLACE([variables].[label], ':', '') = 'Estimate!!Total!!Not Hispanic or Latino!!American Indian and Alaska Native alone' THEN 'Non-Hispanic, American Indian or Alaska Native'
            WHEN REPLACE([variables].[label], ':', '') = 'Estimate!!Total!!Not Hispanic or Latino!!Asian alone' THEN 'Non-Hispanic, Asian'
            WHEN REPLACE([variables].[label], ':', '') = 'Estimate!!Total!!Not Hispanic or Latino!!Native Hawaiian and Other Pacific Islander alone' THEN 'Non-Hispanic, Hawaiian or Pacific Islander'
            WHEN REPLACE([variables].[label], ':', '') = 'Estimate!!Total!!Not Hispanic or Latino!!Two or more races' THEN 'Non-Hispanic, Two or More Races'
            ELSE NULL
        END AS [ethnicity],
        [value]
    FROM [acs].[detailed].[values]
    LEFT JOIN [acs].[detailed].[tables]
        ON [values].[table_id] = [tables].[table_id]
    LEFT JOIN [acs].[detailed].[variables]
        ON [values].[variable] = [variables].[variable]
        AND [values].[table_id] = [variables].[table_id]
    LEFT JOIN [acs].[detailed].[geography]
        ON [values].[geography_id] = [geography].[geography_id]
    WHERE
        [tables].[name] = 'B03002'
        AND [tables].[product] = '5Y'
        AND [tables].[year] = @year
) AS [tbl]
WHERE
    [ethnicity] IS NOT NULL
    AND [tract] != '06073990100'  -- Exclude shoreline/water tract 
GROUP BY
    [tract],
    [ethnicity]