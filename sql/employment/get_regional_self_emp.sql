-- Get the ACS 1-year self-employed total for San Diego County

-- Initialize parameters -----------------------------------------------------
DECLARE @year INTEGER = :year;
DECLARE @msg nvarchar(25) = 'ACS 1-Year Table does not exist';

-- Send error message if no data exists --------------------------------------
IF NOT EXISTS (
    SELECT TOP (1) *
    FROM [acs].[detailed].[tables]
    WHERE 
        [name] = 'B24080'
        AND [year] = @year
        AND 
            (
            [tables].[product] = '1y' 
            OR ([tables].[year] = 2020 AND [tables].[product] = '5y')
            )
)
SELECT @msg AS [msg]
ELSE
BEGIN

    -- Get the ACS data --------------------------------------------------------
    SELECT
        @year AS [year],
        'SE' AS [naics_code], -- assign to 'SE' (Self Employed) NAICS category
        'jobs' AS [metric],
        SUM([value]) AS [value]
    FROM [acs].[detailed].[values]
    INNER JOIN [acs].[detailed].[variables]
        ON [values].[table_id] = [variables].[table_id]
        AND [variables].[variable] = [values].[variable]
    INNER JOIN [acs].[detailed].[tables]
        ON [values].[table_id] = [tables].[table_id]
    WHERE
        [tables].[name] = 'B24080'
        -- there is no 1-year data release for 2020
        AND 
            (
            [tables].[product] = '1y' 
            OR ([tables].[year] = 2020 AND [tables].[product] = '5y')
            )
        -- TODO: currently excluding "self-employed in own incorporated business workers", is this correct?
        AND REPLACE([variables].[label], ':', '') IN (
            'Estimate!!Total!!Male!!Self-employed in own not incorporated business workers',
            'Estimate!!Total!!Female!!Self-employed in own not incorporated business workers'
        )
        AND [year] = @year
END