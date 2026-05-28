/* 
This query grabs the Military Active Duty (Job) Data and assigns counts to MGRA15.
This will assign 0 to MGRAs where there is no Military Jobs

Notes:
    1) This is assuming a connection to the GIS server
    2) currently only works using MGRA15 
*/

-- Initialize parameters -----------------------------------------------------
DECLARE @run_id INTEGER = :run_id;
DECLARE @year INTEGER = :year;
DECLARE @series INTEGER = :series;

-- Check for MGRA series and stop execution if not Series 15
IF @series != 15
BEGIN
    RAISERROR('EDD xref only valid for Series 15 MGRAs',16,1)
    RETURN
END

-- Send error message if no data exists --------------------------------------
IF NOT EXISTS (
    SELECT TOP (1) *
    FROM [EMPCORE].[dbo].[mil_active_duty]
    WHERE [yr] = @year
)
BEGIN
    THROW 50000, 'Military Active duty data does not exist.', 1;
END
ELSE
BEGIN

-- Get MGRA Military Active Duty Counts ------------------------------------- 
    SELECT
        @run_id AS [run_id],
        @year AS [year],
        [mgra],
        'MIL' AS [industry_code],
        'jobs' AS [metric],
        COALESCE(SUM([site_active_duty]), 0) AS [value]
    FROM [GeoDepot].[sde].[MGRA15]
    LEFT OUTER JOIN (
        SELECT [site_active_duty], [shape] 
        FROM [EMPCORE].[dbo].[mil_active_duty]
        WHERE [yr] = @year
        ) AS [mil_active_duty]
        ON [mil_active_duty].[shape].STWithin([MGRA15].[shape]) = 1
    GROUP BY [mgra]
    ORDER BY [mgra]
END