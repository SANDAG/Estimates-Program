/*
This query provides a many-to-many cross reference mapping 2020 Census Blocks to Series 15 MGRAs
There are two cross references for separate use cases
  1) Cross reference based on EDD point-level jobs data within industry codes
  2) Cross reference based on EDD point-level jobs data without considering industry codes
  3) Cross reference based on simple land area intersection

Notes: 
    1) The land area intersection cross reference is used as a default cross
    reference as there may be instances where the EDD point layer indicates no
    MGRAs to allocate data to but the Census LEHD LODES contains jobs that
    need to be allocated to MGRAs.
    2) Data prior to year 2017 is not present in the EDD view and must be
    queried directly from the source database table. Note there is no 2016
    data available.
    3) This must be run on the GIS server.
*/

SET NOCOUNT ON;
-- Initialize parameters and return table ------------------------------------
DECLARE @year INTEGER = :year;
DECLARE @series INTEGER = :series;
DECLARE @msg nvarchar(45) = 'EDD point-level data does not exist';


-- Check for MGRA series and stop execution if not Series 15
IF @series != 15
BEGIN
    THROW 50000, 'EDD xref only valid for Series 15 MGRAs',1;
END

-- Create shell table of 2020 Census Block x Industry Code
DROP TABLE IF EXISTS [#tt_block_industry];
SELECT [GEOID20] AS [block], [industry_code]
INTO [#tt_block_industry]
FROM [GeoDepot].[sde].[CENSUSBLOCKS]
CROSS JOIN (
    SELECT DISTINCT
        CASE
            WHEN LEFT([naics_code], 2) IN ('31','32','33') THEN '31-33'
            WHEN LEFT([naics_code], 2) IN ('44','45') THEN '44-45'
            WHEN LEFT([naics_code], 2) IN ('48','49') THEN '48-49'
            -- there are records in 2011-2012 tagged as "Self Employed" with [naics_code] = '72'
            -- there are records in all years with [naics_code] = '999999' as a NULL placeholder
            WHEN [naics_code] = '72' OR LEFT([naics_code], 2) = '99' THEN NULL
            WHEN LEFT([naics_code], 2) = '72' THEN LEFT([naics_code], 3)
            -- NULL records are mapped to NULL despite falling into this ELSE condition
            ELSE LEFT([naics_code], 2)
        END AS [industry_code]
    FROM [EMPCORE].[ca_edd].[vi_ca_edd_employment]
) AS [industry_code]
WHERE [industry_code] IS NOT NULL;

-- Create temporary table for EDD data to support spatial index
DROP TABLE IF EXISTS [#edd];
CREATE TABLE [#edd] (
    [id] INTEGER IDENTITY(1,1) NOT NULL,
    [industry_code] NVARCHAR(5) NULL,
    [jobs] FLOAT NOT NULL,
    [Shape] GEOMETRY NOT NULL,
    CONSTRAINT [pk_tt_edd] PRIMARY KEY ([id])
)

-- Create spatial index for later spatial join
-- Bounding box coordinates from SANDAG GIS team
-- Identical to spatial index on LUDU point layers in GIS database
CREATE SPATIAL INDEX [sidx_tt_edd] ON [#edd]
([Shape]) USING GEOMETRY_AUTO_GRID 
WITH (BOUNDING_BOX = (
    6151635.98006938, 
    1775442.36347014, 
    6613401.66775663, 
    2129306.52024172), 
    CELLS_PER_OBJECT = 8
)


-- Get SANDAG GIS team EDD dataset -------------------------------------------
IF @year >= 2017
BEGIN
    INSERT INTO [#edd]
    SELECT
        [industry_code],
        1.0 * [emp_total]/[emp_valid] AS [jobs],
        [SHAPE]
    FROM (
        SELECT
            CASE
                WHEN LEFT([naics_code], 2) IN ('31','32','33') THEN '31-33'
                WHEN LEFT([naics_code], 2) IN ('44','45') THEN '44-45'
                WHEN LEFT([naics_code], 2) IN ('48','49') THEN '48-49'
                -- there are records in 2011-2012 tagged as "Self Employed" with [naics_code] = '72'
                -- there are records in all years with [naics_code] = '999999' as a NULL placeholder
                WHEN [naics_code] = '72' OR LEFT([naics_code], 2) = '99' THEN NULL
                WHEN LEFT([naics_code], 2) = '72' THEN LEFT([naics_code], 3)
                -- NULL records are mapped to NULL despite falling into this ELSE condition
                -- Keep these records for total EDD jobs xref even if industry code is NULL
                ELSE LEFT([naics_code], 2)
            END AS [industry_code],
            CASE WHEN [emp_m1] IS NOT NULL THEN 1 ELSE 0 END 
                + CASE WHEN [emp_m2] IS NOT NULL THEN 1 ELSE 0 END 
                + CASE WHEN [emp_m3] IS NOT NULL THEN 1 ELSE 0 END 
                + CASE WHEN [emp_m4] IS NOT NULL THEN 1 ELSE 0 END 
                + CASE WHEN [emp_m5] IS NOT NULL THEN 1 ELSE 0 END 
                + CASE WHEN [emp_m6] IS NOT NULL THEN 1 ELSE 0 END 
                + CASE WHEN [emp_m7] IS NOT NULL THEN 1 ELSE 0 END 
                + CASE WHEN [emp_m8] IS NOT NULL THEN 1 ELSE 0 END 
                + CASE WHEN [emp_m9] IS NOT NULL THEN 1 ELSE 0 END 
                + CASE WHEN [emp_m10] IS NOT NULL THEN 1 ELSE 0 END 
                + CASE WHEN [emp_m11] IS NOT NULL THEN 1 ELSE 0 END 
                + CASE WHEN [emp_m12] IS NOT NULL THEN 1 ELSE 0 END 
            AS [emp_valid],
            ISNULL([emp_m1], 0) 
                + ISNULL([emp_m2], 0) 
                + ISNULL([emp_m3], 0) 
                + ISNULL([emp_m4], 0) 
                + ISNULL([emp_m5], 0) 
                + ISNULL([emp_m6], 0) 
                + ISNULL([emp_m7], 0) 
                + ISNULL([emp_m8], 0) 
                + ISNULL([emp_m9], 0) 
                + ISNULL([emp_m10], 0) 
                + ISNULL([emp_m11], 0) 
                + ISNULL([emp_m12], 0)
            AS [emp_total],
            [SHAPE]
        FROM [EMPCORE].[ca_edd].[vi_ca_edd_employment]
        WHERE [year] = @year
    ) AS [tt]
    WHERE
        [emp_valid] > 0
        AND [emp_total] > 0
END
ELSE IF @year BETWEEN 2010 AND 2013
BEGIN
    INSERT INTO [#edd]
    SELECT
        CASE
            WHEN LEFT([code], 2) IN ('31','32','33') THEN '31-33'
            WHEN LEFT([code], 2) IN ('44','45') THEN '44-45'
            WHEN LEFT([code], 2) IN ('48','49') THEN '48-49'
            -- there are records in 2011-2012 tagged as "Self Employed" with [code] = '72'
            -- there are records in all years with [code] = '999999' as a NULL placeholder
            WHEN [code] = '72' OR LEFT([code], 2) = '99' THEN NULL
            WHEN LEFT([code], 2) = '72' THEN LEFT([code], 3)
            -- NULL records are mapped to NULL despite falling into this ELSE condition
            -- Keep these records for total EDD jobs xref even if industry code is NULL
            ELSE LEFT([code], 2)
        END AS [industry_code],
        [employment] * ISNULL([headquarters].[share], 1) AS [jobs],
        ISNULL([headquarters].[shape], [businesses].[shape]) AS [SHAPE]
    FROM [EMPCORE].[ca_edd].[businesses]
    LEFT OUTER JOIN [EMPCORE].[ca_edd].[naics]
        ON [businesses].[naics_id] = [naics].[naics_id]
    LEFT JOIN [EMPCORE].[ca_edd].[headquarters]
        ON [businesses].[year] = [headquarters].[year]
        AND [businesses].[emp_id] = [headquarters].[emp_id]
    INNER JOIN (
        SELECT [year], [emp_id], [employment]
        FROM [EMPCORE].[ca_edd].[employment]
        WHERE 
            [month_id] = 14  -- adjusted employment
            AND [employment] > 0
            AND [year] = @year
    ) AS [employment]
        ON [businesses].[year] = [employment].[year]
        AND [businesses].[emp_id] = [employment].[emp_id]
END
ELSE IF @year BETWEEN 2014 AND 2016
BEGIN
    INSERT INTO [#edd]
    SELECT
        CASE
            WHEN LEFT([code], 2) IN ('31','32','33') THEN '31-33'
            WHEN LEFT([code], 2) IN ('44','45') THEN '44-45'
            WHEN LEFT([code], 2) IN ('48','49') THEN '48-49'
            -- there are records in 2011-2012 tagged as "Self Employed" with [code] = '72'
            -- there are records in all years with [code] = '999999' as a NULL placeholder
            WHEN [code] = '72' OR LEFT([code], 2) = '99' THEN NULL
            WHEN LEFT([code], 2) = '72' THEN LEFT([code], 3)
            -- NULL records are mapped to NULL despite falling into this ELSE condition
            -- Keep these records for total EDD jobs xref even if industry code is NULL
            ELSE LEFT([code], 2)
        END AS [industry_code],
        [employment] * ISNULL([headquarters].[share], 1) AS [jobs],
        ISNULL([headquarters].[shape], [businesses].[shape]) AS [SHAPE]
    FROM [EMPCORE].[ca_edd].[businesses]
    LEFT OUTER JOIN [EMPCORE].[ca_edd].[naics]
        ON [businesses].[naics_id] = [naics].[naics_id]
    LEFT JOIN [EMPCORE].[ca_edd].[headquarters]
        ON [businesses].[year] = [headquarters].[year]
        AND [businesses].[emp_id] = [headquarters].[emp_id]
    INNER JOIN (
        SELECT
            [year],
            [emp_id],
            -- 15, 16, 17 are mpnths from [employment] table where data was 
            -- stored in [emp1], [emp2], [emp3] but actual month unknown
            -- check [EMPCORE].[ca_edd].[month] for more detail
            1.0 * ((ISNULL([15], 0) + ISNULL([16], 0) + ISNULL([17], 0)) 
                /
                (CASE WHEN [15] IS NOT NULL THEN 1 ELSE 0 END 
                    + CASE WHEN [16] IS NOT NULL THEN 1 ELSE 0 END 
                    + CASE WHEN [17] IS NOT NULL THEN 1 ELSE 0 END
                ))
            AS [employment]
        FROM [EMPCORE].[ca_edd].[employment]
        PIVOT(SUM([employment]) FOR [month_id] IN ([15], [16], [17])) AS [pivot]
        WHERE
            [year] = @year AND
            ([15] IS NOT NULL OR [16] IS NOT NULL OR [17] IS NOT NULL)
    ) AS [employment]
        ON [businesses].[year] = [employment].[year]
        AND [businesses].[emp_id] = [employment].[emp_id]
END


-- Send error message if no data exists --------------------------------------
IF NOT EXISTS (
    SELECT TOP (1) * FROM [#edd]
)
SELECT @msg AS [msg]
ELSE
-- Build cross reference of Census 2020 Blocks to MGRAs ----------------------
BEGIN
    -- Calculate % allocation of Census 2020 Block jobs to MGRAs within Industry Code
    WITH [xref_industry] AS (
        SELECT
            [CENSUSBLOCKS].[GEOID20] AS [block],
            [industry_code],
            [MGRA15].[MGRA] AS [mgra],
            SUM([jobs]) 
                / SUM(SUM([jobs])) OVER (PARTITION BY [CENSUSBLOCKS].[GEOID20], [industry_code])
            AS [pct_industry]
        FROM [#edd]
        INNER JOIN [GeoDepot].[sde].[CENSUSBLOCKS]
            ON [#edd].[Shape].STIntersects([CENSUSBLOCKS].[Shape]) = 1
        INNER JOIN [GeoDepot].[sde].[MGRA15]
            ON [#edd].[Shape].STIntersects([MGRA15].[Shape]) = 1
        GROUP BY 
            [CENSUSBLOCKS].[GEOID20], [industry_code], [MGRA15].[MGRA]
    ),
    -- Calculate % allocation of Census 2020 Block jobs to MGRAs
    [xref_edd] AS (
        SELECT
            [CENSUSBLOCKS].[GEOID20] AS [block],
            [MGRA15].[MGRA] AS [mgra],
            SUM(SUM([jobs])) OVER (PARTITION BY [CENSUSBLOCKS].[GEOID20], [MGRA15].[MGRA]) 
                / SUM(SUM([jobs])) OVER (PARTITION BY [CENSUSBLOCKS].[GEOID20])
            AS [pct_edd]
        FROM [#edd]
        INNER JOIN [GeoDepot].[sde].[CENSUSBLOCKS]
            ON [#edd].[Shape].STIntersects([CENSUSBLOCKS].[Shape]) = 1
        INNER JOIN [GeoDepot].[sde].[MGRA15]
            ON [#edd].[Shape].STIntersects([MGRA15].[Shape]) = 1
        GROUP BY 
            [CENSUSBLOCKS].[GEOID20], [MGRA15].[MGRA]
    ),
    -- Get % area overlap of Census 2020 Block area and MGRAs
    [xref_area] AS (
        SELECT
            [block],
            [mgra],
            -- Ensure the % adds up to one due to exclusion of records <= 0.01
            [pct_area] * 1/SUM([pct_area]) OVER (PARTITION BY [block]) AS [pct_area]
        FROM (
            SELECT
                [CENSUSBLOCKS].[GEOID20] AS [block],
                [MGRA15].[MGRA] AS [mgra],
                ([CENSUSBLOCKS].[Shape].STIntersection([MGRA15].[Shape]).STArea() 
                    / [CENSUSBLOCKS].[Shape].STArea())
                AS [pct_area]
            FROM [GeoDepot].[sde].[CENSUSBLOCKS]
            LEFT OUTER JOIN [GeoDepot].[sde].[MGRA15] 
                ON [CENSUSBLOCKS].[Shape].STIntersects([MGRA15].[Shape]) = 1
            WHERE ([CENSUSBLOCKS].[Shape].STIntersection([MGRA15].[Shape]).STArea() 
                / [CENSUSBLOCKS].[Shape].STArea()) > 0.01
        ) AS [raw_xref_area]
    )
    -- Combine results and set flag indicating which xref to use within Block x Industry Code
    SELECT
        [#tt_block_industry].[block],
        [xref_area].[mgra],
        [#tt_block_industry].[industry_code],
        [pct_industry],
        [pct_edd],
        [pct_area],
        CASE
            WHEN COUNT([pct_industry]) OVER (PARTITION BY [#tt_block_industry].[block], [#tt_block_industry].[industry_code]) > 0 THEN 'pct_industry'
            WHEN COUNT([pct_edd]) OVER (PARTITION BY [#tt_block_industry].[block], [#tt_block_industry].[industry_code]) > 0 THEN 'pct_edd'
            ELSE 'pct_area'
        END AS [flag]
    FROM [#tt_block_industry]
    LEFT OUTER JOIN [xref_area]
        ON [#tt_block_industry].[block] = [xref_area].[block]
    LEFT OUTER JOIN [xref_edd]
        ON [#tt_block_industry].[block] = [xref_edd].[block]
        AND [xref_area].[mgra] = [xref_edd].[mgra]
    LEFT OUTER JOIN [xref_industry]
        ON [#tt_block_industry].[block] = [xref_industry].[block]
        AND [#tt_block_industry].[industry_code] = [xref_industry].[industry_code]
        AND [xref_area].[mgra] = [xref_industry].[mgra]
    ORDER BY
        [#tt_block_industry].[block],
        [xref_area].[mgra],
        [#tt_block_industry].[industry_code]
END

DROP TABLE IF EXISTS [#edd];