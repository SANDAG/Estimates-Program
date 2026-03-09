/*
This query provides a many-to-many cross reference mapping 2020 Census Blocks to Series 15 MGRAs
There are two cross references for separate use cases
  1) Cross reference based on EDD point-level jobs data
  2) Cross reference based on simple land area intersection

Notes: 
    1) The land area intersection cross reference is used as a default cross
    reference as there may be instances where the EDD point layer indicates no
    MGRAs to allocate data to but the Census LEHD LODES contains jobs that
    need to be allocated to MGRAs.
    2) Data prior to year 2017 is not present in the EDD view and must be
    queried directly from the source database table.
    3) This must be run on the GIS server
*/

SET NOCOUNT ON;
-- Initialize parameters and return table ------------------------------------
DECLARE @year INTEGER = :year;
DECLARE @mgra_version NVARCHAR(10) = :mgra_version;
DECLARE @msg nvarchar(45) = 'EDD point-level data does not exist';


-- Check for MGRA version and stop execution if not Series 15
IF @mgra_version != 'mgra15' 
BEGIN
    RAISERROR('EDD xref only valid for Series 15 MGRAs',16,1)
    RETURN
END

-- Create temporary table for EDD data to support spatial index
DROP TABLE IF EXISTS [#edd];
CREATE TABLE [#edd] (
    [id] INTEGER IDENTITY(1,1) NOT NULL,
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
        1.0 * [emp_total]/[emp_valid] AS [jobs],
        [SHAPE]
    FROM (
        SELECT
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
        FROM [ca_edd].[vi_ca_edd_employment]
        WHERE [year] = @year
    ) AS [tt]
    WHERE
        [emp_valid] > 0
        AND [emp_total] > 0
END
ELSE IF @year = 2016 OR @year BETWEEN 2010 AND 2014
BEGIN
    INSERT INTO [#edd]
        SELECT 
            [employment] * ISNULL([headquarters].[share], 1) AS [jobs],
            ISNULL([headquarters].[shape], [businesses].[shape]) AS [SHAPE]
        FROM [ca_edd].[businesses]
        LEFT JOIN [ca_edd].[headquarters]
            ON [businesses].[year] = [headquarters].[year]
            AND [businesses].[emp_id] = [headquarters].[emp_id]
        INNER JOIN (
            SELECT [year], [emp_id], [employment]
            FROM [ca_edd].[employment]
            WHERE 
                [month_id] = 14  -- adjusted employment
                AND [employment] > 0
                AND [year] = @year
        ) AS [employment]
            ON [businesses].[year] = [employment].[year]
            AND [businesses].[emp_id] = [employment].[emp_id]
END
ELSE IF @year = 2015
BEGIN
    INSERT INTO [#edd]
        SELECT 
            [employment] * ISNULL([headquarters].[share], 1) AS [jobs],
            ISNULL([headquarters].[shape], [businesses].[shape]) AS [SHAPE]
        FROM [ca_edd].[businesses]
        LEFT JOIN [ca_edd].[headquarters]
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
	        FROM [ca_edd].[employment]
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
    SELECT TOP (1) *
	FROM [#edd]
)
SELECT @msg AS [msg]
ELSE
-- Build cross reference of Census 2020 Blocks to MGRAs ----------------------
BEGIN
    -- Calculate sum of jobs in Census 2020 Blocks by MGRAs using EDD points
    -- Used later to calculate % allocation of Census 2020 Block jobs to MGRAs
    WITH [xref_edd] AS (
        SELECT
            [CENSUSBLOCKS].[GEOID20] AS [block],
            [MGRA15].[MGRA] AS [mgra],
	        SUM([jobs]) AS [mgra_jobs],
	        SUM(SUM([jobs])) OVER (PARTITION BY [CENSUSBLOCKS].[GEOID20]) 
            AS [block_jobs]
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
			[CENSUSBLOCKS].[GEOID20] AS [block],
			[MGRA15].[MGRA] AS [mgra],
			([CENSUSBLOCKS].[Shape].STIntersection([MGRA15].[Shape]).STArea() 
                / [CENSUSBLOCKS].[Shape].STArea()) 
            AS [pct_area]
		FROM [GeoDepot].[sde].[CENSUSBLOCKS]
		LEFT JOIN [GeoDepot].[sde].[MGRA15] 
			ON [CENSUSBLOCKS].[Shape].STIntersects([MGRA15].[Shape]) = 1
		WHERE ([CENSUSBLOCKS].[Shape].STIntersection([MGRA15].[Shape]).STArea() 
            / [CENSUSBLOCKS].[Shape].STArea()) > 0.01
    ),
    -- Combine results and calculate % allocations of Census 2020 blocks to MGRAs
    [results] AS (
	    SELECT
		    ISNULL([xref_edd].[block], [xref_area].[block]) AS [block],
		    ISNULL([xref_edd].[mgra], [xref_area].[mgra]) AS [mgra],
		    SUM(CASE WHEN ISNULL([xref_edd].[block_jobs], 0) = 0 THEN 0
				    ELSE 1.0 * ISNULL([xref_edd].[mgra_jobs], 0) 
                        / ISNULL([xref_edd].[block_jobs], 0)
				    END) AS [pct_edd],
			SUM(ISNULL([xref_area].[pct_area], 0)) AS [pct_area]
	    FROM [xref_edd]
	    FULL JOIN [xref_area]
		    ON [xref_edd].[block] = [xref_area].[block]
            AND [xref_edd].[mgra] = [xref_area].[mgra]
	    GROUP BY 
	        ISNULL([xref_edd].[block], [xref_area].[block]),
	        ISNULL([xref_edd].[mgra], [xref_area].[mgra])
    )
    -- Return results ensuring % allocations add to 1 within each Census 2020 Block
    SELECT
	    [block],
	    [mgra],
	    CASE WHEN SUM([pct_edd]) OVER (PARTITION BY [block]) > 0
	         THEN [pct_edd] * 1/SUM([pct_edd]) OVER (PARTITION BY [block])
		     ELSE 0 END AS [pct_edd],
	    [pct_area] * 1/SUM([pct_area]) OVER (PARTITION BY [block]) AS [pct_area],
        CASE WHEN SUM([pct_edd]) OVER (PARTITION BY [block])> 0 
            THEN 1 
            ELSE 0 END AS edd_flag
    FROM
	    [results]
    WHERE
	    [mgra] IS NOT NULL
    ORDER BY
        [block],
        [mgra]
END

--Drop Temp table
DROP TABLE IF EXISTS [#edd];