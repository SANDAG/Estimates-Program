/*
This query provides a split of 2-digit NAICS 72 into 3-digit NAICS codes.
Point-level data is gotten from the confidential EDD dataset, assigned to
2020 Census Blocks and the percentage split of 2-digit NAICS 72 into the
3-digit NAICS codes of 721 and 722 is calculated within each block.

Notes: 
    1) This query assumes the connection is to the GIS server.
    2) Data prior to year 2017 is not present in the EDD view and must be
    queried directly from the source database table.
    3) If no split is present for a block, the regional percentage split is
    substituted. All 2020 Census blocks are represented.
*/

SET NOCOUNT ON;
-- Initialize parameters and return table ------------------------------------
DECLARE @year INTEGER = :year;
DECLARE @msg nvarchar(45) = 'EDD point-level data does not exist';


--Drop temp table if exist and then create temp table 
DROP TABLE IF EXISTS [#edd];
CREATE TABLE [#edd] (
    [id] INTEGER IDENTITY(1,1) NOT NULL,
    [industry_code] NVARCHAR(3) NOT NULL,
    [average_monthly_jobs] FLOAT NOT NULL,
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
        1.0 * [emp_total]/[emp_valid] AS [average_monthly_jobs],
        [SHAPE]
    FROM (
        SELECT
            CASE 
                WHEN LEFT([code], 3) = '721' THEN '721'
                WHEN LEFT([code], 3) = '722' THEN '722'
                ELSE NULL 
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
                + CASE WHEN [emp_m12] IS NOT NULL THEN 1 ELSE 0 
            END AS [emp_valid],
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
        INNER JOIN [EMPCORE].[ca_edd].[naics]
            ON [vi_ca_edd_employment].[naics_id] = [naics].[naics_id]
        WHERE 
            [year] = @year
            AND LEFT([code], 3) IN ('721','722')
    ) AS [tt]
    WHERE
        [emp_valid] > 0
        AND [emp_total] > 0
END
ELSE IF @year = 2016 OR @year BETWEEN 2010 AND 2014
BEGIN
    INSERT INTO [#edd]
    SELECT
        CASE 
            WHEN LEFT([code], 3) = '721' THEN '721'
            WHEN LEFT([code], 3) = '722' THEN '722'
            ELSE NULL 
        END AS [industry_code],
        [employment] * ISNULL([headquarters].[share], 1) AS [average_monthly_jobs],
        ISNULL([headquarters].[shape], [businesses].[shape]) AS [SHAPE]
    FROM [EMPCORE].[ca_edd].[businesses]
    INNER JOIN [EMPCORE].[ca_edd].[naics]
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
    WHERE LEFT([code], 3) IN ('721','722')
END
ELSE IF @year = 2015
BEGIN
    INSERT INTO [#edd]
    SELECT
        CASE 
            WHEN LEFT([code], 3) = '721' THEN '721'
            WHEN LEFT([code], 3) = '722' THEN '722'
            ELSE NULL 
        END AS [industry_code],
        [employment] * ISNULL([headquarters].[share], 1) AS [average_monthly_jobs],
        ISNULL([headquarters].[shape], [businesses].[shape]) AS [SHAPE]
    FROM [EMPCORE].[ca_edd].[businesses]
    INNER JOIN [EMPCORE].[ca_edd].[naics]
        ON [businesses].[naics_id] = [naics].[naics_id]
    LEFT JOIN [EMPCORE].[ca_edd].[headquarters]
        ON [businesses].[year] = [headquarters].[year]
        AND [businesses].[emp_id] = [headquarters].[emp_id]
    INNER JOIN (
        SELECT
            [year],
            [emp_id],
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
            [year] = @year
            AND ([15] IS NOT NULL OR [16] IS NOT NULL OR [17] IS NOT NULL)
    ) AS [employment]
        ON [businesses].[year] = [employment].[year]
        AND [businesses].[emp_id] = [employment].[emp_id]
    WHERE LEFT([code], 3) IN ('721','722')
END


-- Send error message if no data exists --------------------------------------
IF NOT EXISTS (
    SELECT TOP (1) *
    FROM [#edd]
)
BEGIN
    SELECT @msg AS [msg]
END
ELSE
BEGIN
    -- Calculate % split of NAICS 72 into 721 and 722 for 2020 Census Blocks -
    SELECT
        [GEOID20] AS [block],
        CASE 
            WHEN [72] = 0 THEN SUM([721]) OVER() / SUM([72]) OVER()
            ELSE [721] / [72] 
        END AS [pct_721],
        CASE 
            WHEN [72] = 0 THEN SUM([722]) OVER() / SUM([72]) OVER()
            ELSE [722] / [72] 
        END AS [pct_722]
    FROM (
        SELECT
            [GEOID20],
            SUM(CASE WHEN [industry_code] = '721' THEN [average_monthly_jobs] ELSE 0 END) AS [721],
            SUM(CASE WHEN [industry_code] = '722' THEN [average_monthly_jobs] ELSE 0 END) AS [722],
            ISNULL(SUM([average_monthly_jobs]), 0) AS [72]
        FROM [#edd]
        RIGHT OUTER JOIN [GeoDepot].[sde].[CENSUSBLOCKS]
            ON [#edd].[Shape].STIntersects([CENSUSBLOCKS].[Shape]) = 1
        GROUP BY [GEOID20]
    ) [tt]
    ORDER BY [GEOID20]
END

--Drop Temp table
DROP TABLE IF EXISTS [#edd];