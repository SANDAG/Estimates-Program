-- SQL Script which can pull ASE population from the ACS based on some generic 
-- geography. The way this works is by searching in [dim].[mgra_denormalize] for the
-- requested geography, finding the MGRAs in the geography, then finding the tracts in
-- the geography. Then, ACS data corresponding to those tracts is pulled and aggregated
--DECLARE @geotype NVARCHAR(32) = :geotype;
--DECLARE @geozone NVARCHAR(32) = :geozone;
DECLARE @series NVARCHAR(4) = '15';
DECLARE @geotype NVARCHAR(32) = 'jurisdiction';
DECLARE @geozone NVARCHAR(128) = 'Solana Beach';
DECLARE @query NVARCHAR(MAX);

-- Find the tracts which correspond to the geotype/geozone ----------------------------
SET @query = '
    DROP TABLE IF EXISTS [##tracts]
    SELECT DISTINCT CONCAT(''06073'', RIGHT(REPLICATE(''0'', 6) + LEFT([tract], 6), 6)) AS [tract]
    INTO [##tracts]
    FROM [demographic_warehouse].[dim].[mgra_denormalize]
    WHERE [series] = ' + @series + '
        AND ' + @geotype + ' = ''' + @geozone + '''';
EXEC sp_executesql @query;

-- Get the ACS data for these tracts --------------------------------------------------
-- Ethnicity
SELECT
    [year],
    [ethnicity],
    SUM([value]) AS [population]
FROM (
    SELECT
        [tables].[year],
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
        AND [tract] IN (SELECT [tract] FROM [##tracts])
) AS [tbl]
WHERE [ethnicity] IS NOT NULL
GROUP BY [year], [ethnicity]
ORDER BY [ethnicity], [year]

-- Age Group
SELECT
    [year],
    [age_group],
    SUM([value]) AS [value]
FROM (
    SELECT
        [tables].[year],
        [tract],
        CASE
            WHEN [variables].[label] LIKE 'Estimate%Under 5%' THEN 'Under 5'
            WHEN [variables].[label] LIKE 'Estimate%5 to 9%' THEN '5 to 9'
            WHEN [variables].[label] LIKE 'Estimate%10 to 14%' THEN '10 to 14'
            WHEN [variables].[label] LIKE 'Estimate%15 to 17%' THEN '15 to 17'
            WHEN [variables].[label] LIKE 'Estimate%18 and 19%' THEN '18 and 19'
            WHEN [variables].[label] LIKE 'Estimate%20 years%'
                OR [variables].[label] LIKE 'Estimate%21 years%'
                OR [variables].[label] LIKE 'Estimate%22 to 24 years%'
            THEN '20 to 24'
            WHEN [variables].[label] LIKE 'Estimate%25 to 29%' THEN '25 to 29'
            WHEN [variables].[label] LIKE 'Estimate%30 to 34%' THEN '30 to 34'
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
        AND [tract] IN (SELECT [tract] FROM [##tracts])
) AS [tbl]
WHERE [age_group] IS NOT NULL
GROUP BY [year], [age_group]
ORDER BY [age_group], [year]

-- Sex
SELECT
    [year],
    [sex],
    SUM([value]) AS [value]
FROM (
    SELECT
        [tables].[year],
        [tract],
        CASE
            WHEN [variables].[label] LIKE 'Estimate%Female%' THEN 'Female'
            WHEN [variables].[label] LIKE 'Estimate%Male%' THEN 'Male'
            ELSE NULL
        END AS [sex],
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
        AND [tract] IN (SELECT [tract] FROM [##tracts])
) AS [tbl]
WHERE [sex] IS NOT NULL
GROUP BY [year], [sex]
ORDER BY [sex], [year]
