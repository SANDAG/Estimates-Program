/* 
This query grabs the Military Active Duty (Job) Data and assigns counts to MGRA15.
This will assign 0 to MGRAs where there is no Military Jobs
*/

-- Initialize parameters -----------------------------------------------------
DECLARE @run_id INTEGER = :run_id;
DECLARE @year INTEGER = :year;


-- Send error message if no data exists --------------------------------------
IF NOT EXISTS (
    SELECT TOP (1) *
    FROM [ws].[fact].[MILILTARY_EMPLOYMENT]
    WHERE [year] = @year
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
    FROM [inputs].[mgra]
    LEFT OUTER JOIN [ws].[fact].[MILILTARY_EMPLOYMENT]
        ON [MILILTARY_EMPLOYMENT].[shape].STWithin([mgra].[shape]) = 1
        AND [run_id] = @run_id AND [year] = @year
    WHERE [run_id] = @run_id 
    GROUP BY [run_id], [year], [mgra]
    ORDER BY [year], [mgra]
END