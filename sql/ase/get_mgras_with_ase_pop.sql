/*
Find Census Tracts which have population matching the input year and age/sex/ethnicity
category.
*/

-- Initialize parameters --------------------------------------------------------------
DECLARE @age_group NVARCHAR(MAX) = :age_group;
DECLARE @sex NVARCHAR(MAX) = :sex;
DECLARE @ethnicity NVARCHAR(MAX) = :ethnicity;
DECLARE @year INTEGER = :year;
DECLARE @series INTEGER = :series;

-- Send error message if no data exists -----------------------------------------------
IF @year > 2011
BEGIN
SELECT 'ACS 5-Year Data does not exist' AS [msg]
END

-- Find tracts in the given year/ASE with population ----------------------------------
ELSE
BEGIN
SELECT DISTINCT [mgra]
FROM [demographic_warehouse].[dim].[mgra_xref]
INNER JOIN [demographic_warehouse].[dim].[mgra]
    ON [mgra_xref].[mgra_id] = [mgra].[mgra_id]
WHERE [series] = @series
    AND [xref_year] = @year
    AND [tract] IN (
        SELECT DISTINCT [tract]
        FROM (
            SELECT
                [tract],
                CASE
                    WHEN [variables].[label] LIKE 'Estimate%Female%' THEN 'Female'
                    WHEN [variables].[label] LIKE 'Estimate%Male%' THEN 'Male'
                    ELSE NULL
                END AS [sex],
                -- Note: race categories are consistent with Estimates program and will be generated in IPF process
                CASE
                    WHEN [tables].[description] = 'SEX BY AGE (HISPANIC OR LATINO)' THEN 'Hispanic'
                    WHEN [tables].[description] = 'SEX BY AGE (WHITE ALONE, NOT HISPANIC OR LATINO)' THEN 'Non-Hispanic, White'
                    WHEN [tables].[description] = 'SEX BY AGE (BLACK OR AFRICAN AMERICAN ALONE)' THEN 'Non-Hispanic, Black'
                    WHEN [tables].[description] = 'SEX BY AGE (AMERICAN INDIAN AND ALASKA NATIVE ALONE)' THEN 'Non-Hispanic, American Indian or Alaska Native'
                    WHEN [tables].[description] = 'SEX BY AGE (ASIAN ALONE)' THEN 'Non-Hispanic, Asian'
                    WHEN [tables].[description] = 'SEX BY AGE (NATIVE HAWAIIAN AND OTHER PACIFIC ISLANDER ALONE)' THEN 'Non-Hispanic, Hawaiian or Pacific Islander'
                    WHEN [tables].[description] = 'SEX BY AGE (TWO OR MORE RACES)' THEN 'Non-Hispanic, Two or More Races'
                ELSE NULL
                END AS [ethnicity],
                CASE
                    WHEN [variables].[label] LIKE 'Estimate%Under 5%' THEN 'Under 5'
                    WHEN [variables].[label] LIKE 'Estimate%5 to 9%' THEN '5 to 9'
                    WHEN [variables].[label] LIKE 'Estimate%10 to 14%' THEN '10 to 14'
                    WHEN [variables].[label] LIKE 'Estimate%15 to 17%' THEN '15 to 17'
                    WHEN [variables].[label] LIKE 'Estimate%18 and 19%' THEN '18 and 19'
                    WHEN [variables].[label] LIKE 'Estimate%20 to 24 years%' THEN '20 to 24'
                    WHEN [variables].[label] LIKE 'Estimate%25 to 29%' THEN '25 to 29'
                    WHEN [variables].[label] LIKE 'Estimate%30 to 34%' THEN '30 to 34'
                    WHEN [variables].[label] LIKE 'Estimate%35 to 44%' THEN '35 to 44'
                    WHEN [variables].[label] LIKE 'Estimate%45 to 54%' THEN '45 to 54'
                    WHEN [variables].[label] LIKE 'Estimate%55 to 64%' THEN '55 to 64'
                    WHEN [variables].[label] LIKE 'Estimate%65 to 74%' THEN '65 to 74'
                    WHEN [variables].[label] LIKE 'Estimate%75 to 84%' THEN '75 to 84'
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
                [tables].[name] IN ('B01001B', 'B01001C', 'B01001D', 'B01001E', 'B01001G', 'B01001H', 'B01001I')
                AND [tables].[product] = '5Y'
                AND [tables].[year] = @year
        ) AS [tbl]
        WHERE [age_group] = @age_group
            AND [sex] = @sex
            AND [ethnicity] = @ethnicity
            AND [value] > 0
    )
END
