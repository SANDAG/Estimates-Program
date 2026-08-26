/* 
This query grabs the Military Active Duty (Job) Data and assigns counts to MGRAs.
This will assign 0s to MGRAs where there are no military jobs.

Note: This is assuming a connection to the GIS server
*/

SET NOCOUNT ON;
-- Initialize parameters -----------------------------------------------------
DECLARE @run_id INTEGER = :run_id;
DECLARE @year INTEGER = :year;
DECLARE @estimates_server nvarchar(20) = :estimates_server;
DECLARE @estimates_database nvarchar(20) = :estimates_database;


-- Get MGRA geography and insert to temporary table
-- Build the OPENQUERY to the Estimates database to get the MGRA geography
-- Note the statement stores results in a temporary table for later use
DROP TABLE IF EXISTS [#mgra];
CREATE TABLE [#mgra] (
    [mgra] INTEGER NOT NULL,
    [shape] GEOMETRY NOT NULL,
    CONSTRAINT [pk_tt_mgra] PRIMARY KEY ([mgra])
);

DECLARE @qry NVARCHAR(max) = '
    INSERT INTO [#mgra]
    SELECT [mgra], [shape]
    FROM OPENQUERY([' + @estimates_server + '], ''
        SELECT [mgra], [shape]
        FROM ' + @estimates_database + '.[inputs].[mgra]
        WHERE [run_id] = ' + CONVERT(NVARCHAR, @run_id) + '
    '')
'
EXEC sp_executesql @qry;


-- Send error message if no data exists --------------------------------------
IF NOT EXISTS (
    SELECT TOP (1) *
    FROM [EMPCORE].[dbo].[mil_active_duty]
    WHERE [yr] = @year
)
BEGIN
    THROW 50000, 'Military active duty data does not exist.', 1;
END
ELSE
BEGIN

-- Get MGRA Military Active Duty Counts ------------------------------------- 
    SELECT
        @run_id AS [run_id],
        @year AS [year],
        [mgra],
        'Federal Government' AS [ownership_title],
        'MIL' AS [industry_code],
        COALESCE(SUM([site_active_duty]), 0) AS [value]
    FROM [#mgra]
    LEFT OUTER JOIN (
        SELECT [site_active_duty], [shape] 
        FROM [EMPCORE].[dbo].[mil_active_duty]
        WHERE [yr] = @year
        ) AS [mil_active_duty]
        ON [mil_active_duty].[shape].STWithin([#mgra].[shape]) = 1
    GROUP BY [mgra]
    ORDER BY [mgra];

    DROP TABLE IF EXISTS [#mgra];
END