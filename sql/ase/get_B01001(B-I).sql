/*
Get population by age/sex/ethnicity using B01001(B-I) tables and B01001 table for a given ACS 5-Year survey.
The B01001(B-I) tables aggregate age categories are naively split using the B01001 table allocations at the region level.

The following aggregate age categories are split:
    35 to 44 - Split into 35 to 39, 40 to 44
    45 to 54 - Split into 45 to 49, 50 to 54
    55 to 64 - Split into 55 to 59, 60 and 61, 62 to 64
    65 to 74 - Split into 65 to 69, 70 to 74
    75 to 84 - Split into 75 to 79, 80 to 84 

Note that only Hispanic and White Alone are split by Hispanic/Non-Hispanic in
the B01001(B-I) tables although the race categories are encoded as if they are.

This data is used as seed data for the IPF process that generates age/sex/ethnicity seed data.
*/

SET NOCOUNT ON;
-- Initialize parameters -----------------------------------------------------
DECLARE @year integer = :year;


-- Send message if not all tables exist --------------------------------------
DECLARE @rows integer = (
    SELECT COUNT([table_id]) AS [rows]
    FROM [acs].[detailed].[tables]
    WHERE 
        [name] IN ('B01001', 'B01001B', 'B01001C', 'B01001D', 'B01001E', 'B01001G', 'B01001H', 'B01001I')
	    AND [year] = @year
	    AND [product] = '5Y'
);

IF @rows = 0
    SELECT 'ACS 5-Year Table does not exist' AS [msg]
ELSE IF @rows != 8
    SELECT 'Incorrect number of ACS 5-Year Tables exist' AS [msg]
ELSE
BEGIN
    -- Create aggregate age category allocation table ------------------------
    -- Use B01001 to determine a naive split of aggregate age categories in the B01001(B-I) tables
    DROP TABLE IF EXISTS [#allocation_tbl];
    WITH [b01001] AS (
        SELECT
            [sex],
            [age_group],
            [split_age_group],
            SUM([value]) AS [value]
        FROM (
            SELECT
                CASE
                    WHEN [variables].[label] LIKE 'Estimate%Female%' THEN 'Female'
                    WHEN [variables].[label] LIKE 'Estimate%Male%' THEN 'Male'
                    ELSE NULL
                END AS [sex],
                CASE
                    WHEN [variables].[label] LIKE 'Estimate%35 to 39%' THEN '35 to 39'
                    WHEN [variables].[label] LIKE 'Estimate%40 to 44%' THEN '40 to 44'
                    WHEN [variables].[label] LIKE 'Estimate%45 to 49%' THEN '45 to 49'
                    WHEN [variables].[label] LIKE 'Estimate%50 to 54%' THEN '50 to 54'
                    WHEN [variables].[label] LIKE 'Estimate%55 to 59%' THEN '55 to 59'
                    WHEN [variables].[label] LIKE 'Estimate%60 and 61%' THEN '60 and 61'
                    WHEN [variables].[label] LIKE 'Estimate%62 to 64%' THEN '62 to 64'
                    WHEN [variables].[label] LIKE 'Estimate%65 and 66%'
                        OR [variables].[label] LIKE 'Estimate%67 to 69%'
                    THEN '65 to 69'
                    WHEN [variables].[label] LIKE 'Estimate%70 to 74%' THEN '70 to 74'
                    WHEN [variables].[label] LIKE 'Estimate%75 to 79%' THEN '75 to 79'
                    WHEN [variables].[label] LIKE 'Estimate%80 to 84%' THEN '80 to 84'
                    ELSE NULL
                END AS [age_group],
                CASE
                    WHEN [variables].[label] LIKE 'Estimate%35 to 39%' THEN '35 to 44'
                    WHEN [variables].[label] LIKE 'Estimate%40 to 44%' THEN '35 to 44'
                    WHEN [variables].[label] LIKE 'Estimate%45 to 49%' THEN '45 to 54'
                    WHEN [variables].[label] LIKE 'Estimate%50 to 54%' THEN '45 to 54'
                    WHEN [variables].[label] LIKE 'Estimate%55 to 59%' THEN '55 to 64'
                    WHEN [variables].[label] LIKE 'Estimate%60 and 61%' THEN '55 to 64'
                    WHEN [variables].[label] LIKE 'Estimate%62 to 64%' THEN '55 to 64'
                    WHEN [variables].[label] LIKE 'Estimate%65 and 66%'
                        OR [variables].[label] LIKE 'Estimate%67 to 69%'
                    THEN '65 to 74'
                    WHEN [variables].[label] LIKE 'Estimate%70 to 74%' THEN '65 to 74'
                    WHEN [variables].[label] LIKE 'Estimate%75 to 79%' THEN '75 to 84'
                    WHEN [variables].[label] LIKE 'Estimate%80 to 84%' THEN '75 to 84'
                    ELSE NULL
                END AS [split_age_group],
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
            [sex],
            [age_group],
            [split_age_group]
    )
    -- Calculate naive split %s of aggregate age categories from B01001 used in the B01001(B-I) tables
    SELECT
        [sex],
        [age_group],
        [split_age_group],
        CASE
            WHEN SUM([value]) OVER (PARTITION BY [sex], [split_age_group]) = 0 THEN 0
            ELSE [value] / SUM([value]) OVER (PARTITION BY [sex], [split_age_group])
        END AS [pct]
    INTO [#allocation_tbl]
    FROM [b01001];


    -- Get B01001(B-I) table data and apply aggregate age category splits ----
    WITH [b01001b-i] AS (
        SELECT
            [tract],
            [sex],
            [ethnicity],
            [age_group],
            [split_age_group],
            SUM([value]) AS [value]
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
                    WHEN [variables].[label] LIKE 'Estimate%85 years and over%' THEN '85 and Older'
                    ELSE NULL
                END AS [age_group],
                CASE
                    WHEN [variables].[label] LIKE 'Estimate%35 to 44%' THEN '35 to 44'
                    WHEN [variables].[label] LIKE 'Estimate%45 to 54%' THEN '45 to 54'
                    WHEN [variables].[label] LIKE 'Estimate%55 to 64%' THEN '55 to 64'
                    WHEN [variables].[label] LIKE 'Estimate%65 to 74%' THEN '65 to 74'
                    WHEN [variables].[label] LIKE 'Estimate%75 to 84%' THEN '75 to 84'
                    ELSE NULL
                END AS [split_age_group],
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
        WHERE
            [sex] IS NOT NULL
            AND [ethnicity] IS NOT NULL
            AND ([age_group] IS NOT NULL OR [split_age_group] IS NOT NULL)
        GROUP BY
            [tract],
            [sex],
            [ethnicity],
            [age_group],
            [split_age_group]
    )
    -- Take the B01001(B-I) data and split aggregate age groups using naive %s from B01001
    SELECT
        [tract],
        [b01001b-i].[sex],
        [b01001b-i].[ethnicity],
        CASE
            WHEN [b01001b-i].[age_group] IS NULL THEN [#allocation_tbl].[age_group]
            ELSE [b01001b-i].[age_group]
        END AS [age_group],
        CASE
            WHEN [#allocation_tbl].[pct] IS NULL THEN [b01001b-i].[value]
            ELSE [#allocation_tbl].[pct] * [b01001b-i].[value]
        END AS [value]
    FROM [b01001b-i]
    LEFT OUTER JOIN [#allocation_tbl]
        ON [b01001b-i].[sex] = [#allocation_tbl].[sex]
        AND [b01001b-i].[split_age_group] = [#allocation_tbl].[split_age_group]
    WHERE [tract] != '06073990100'  -- Exclude shoreline/water tract
END