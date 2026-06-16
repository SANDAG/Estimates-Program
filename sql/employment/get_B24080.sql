-- Get ACS 5-year self-employment counts by census blockgroup (2013+) or tract (2010-2012)

-- Initialize parameters -----------------------------------------------------
DECLARE @year INTEGER = :year;
DECLARE @msg nvarchar(31) = 'ACS 5-Year Table does not exist';

-- Send error message if no data exists --------------------------------------
IF NOT EXISTS (
    SELECT TOP (1) *
    FROM [acs].[detailed].[tables]
    WHERE 
        [name] = 'B24080'
        AND [year] = @year
        AND [product] = '5Y'
)
SELECT @msg AS [msg]
ELSE
BEGIN

    -- Get the ACS data ----------------------------------------------------------
    SELECT
        @year AS [year],
        CASE
            WHEN @year BETWEEN 2010 AND 2012 THEN [tract]
            ELSE [blockgroup]
        END AS [geography],
        'SE' AS [industry_code],
        SUM([value]) AS [value]
    FROM [acs].[detailed].[values]
    INNER JOIN [acs].[detailed].[geography]
        ON [values].[geography_id] = [geography].[geography_id]
    INNER JOIN [acs].[detailed].[variables]
        ON [values].[table_id] = [variables].[table_id]
        AND [variables].[variable] = [values].[variable]
    INNER JOIN [acs].[detailed].[tables]
        ON [values].[table_id] = [tables].[table_id]
    WHERE
        [tables].[name] = 'B24080'
        AND [tables].[product] = '5Y'
        AND REPLACE([variables].[label], ':', '') IN (
            'Estimate!!Total!!Male!!Self-employed in own not incorporated business workers',
            'Estimate!!Total!!Female!!Self-employed in own not incorporated business workers'
        )
        AND [tables].[year] = @year
    GROUP BY
        CASE
            WHEN @year BETWEEN 2010 AND 2012 THEN [tract]
            ELSE [blockgroup]
        END
    ORDER BY [geography]
END