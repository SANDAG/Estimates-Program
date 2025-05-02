/*
Get population by Age/Sex using the B01001 table for a given ACS 5-Year survey.
This data provides granular age groups for use in age/sex/ethnicity seed generation.
*/

-- Initialize parameters -----------------------------------------------------
DECLARE @year integer = :year;


-- Get ACS 5-Year B01001 -----------------------------------------------------
SELECT
    [tract],
    [sex],
    [age_group],
    SUM([value]) AS [value]
FROM (
    SELECT
        [tract],
        CASE
            WHEN [variables].[label] LIKE 'Estimate%Female%' THEN 'Female'
            WHEN [variables].[label] LIKE 'Estimate%Male%' THEN 'Male'
            ELSE NULL
        END AS [sex],
        CASE
            WHEN [variables].[label] LIKE 'Estimate%Under 5%' THEN 'Under 5'
            WHEN [variables].[label] LIKE 'Estimate%5 to 9%' THEN '5 to 9'
            WHEN [variables].[label] LIKE 'Estimate%10 to 14%' THEN '10 to 14'
            WHEN [variables].[label] LIKE 'Estimate%15 to 17%' THEN '15 to 17'
            WHEN [variables].[label] LIKE 'Estimate%18 and 19%' THEN '18 and 19'
            WHEN [variables].[label] LIKE 'Estimate%20 years%' OR [variables].[label] LIKE 'Estimate%21 years%' OR [variables].[label] LIKE 'Estimate%22 to 24 years%' THEN '20 to 24'
            WHEN [variables].[label] LIKE 'Estimate%25 to 29%' THEN '25 to 29'
            WHEN [variables].[label] LIKE 'Estimate%30 to 34%' THEN '30 to 34'
            WHEN [variables].[label] LIKE 'Estimate%35 to 39%' THEN '35 to 39'
            WHEN [variables].[label] LIKE 'Estimate%40 to 44%' THEN '40 to 44'
            WHEN [variables].[label] LIKE 'Estimate%45 to 49%' THEN '45 to 49'
            WHEN [variables].[label] LIKE 'Estimate%50 to 54%' THEN '50 to 54'
            WHEN [variables].[label] LIKE 'Estimate%55 to 59%' THEN '55 to 59'
            WHEN [variables].[label] LIKE 'Estimate%60 and 61%' THEN '60 and 61'
            WHEN [variables].[label] LIKE 'Estimate%62 to 64%' THEN '62 to 64'
            WHEN [variables].[label] LIKE 'Estimate%65 and 66%' OR [variables].[label] LIKE 'Estimate%67 to 69%' THEN '65 to 69'
            WHEN [variables].[label] LIKE 'Estimate%70 to 74%' THEN '70 to 74'
            WHEN [variables].[label] LIKE 'Estimate%75 to 79%' THEN '75 to 79'
            WHEN [variables].[label] LIKE 'Estimate%80 to 84%' THEN '80 to 84'
            WHEN [variables].[label] LIKE 'Estimate%85 years and over%' THEN '85 and Older'
            ELSE NULL
        END AS [age_group],
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
        [tables].[name] = 'B01001'
        AND [tables].[product] = '5Y'
        AND [tables].[year] = @year
) AS [tbl]
WHERE
    [sex] IS NOT NULL 
    AND [age_group] IS NOT NULL
GROUP BY
    [tract],
    [sex],
    [age_group]