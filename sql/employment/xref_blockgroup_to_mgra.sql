/* 
This query creates a cross reference from blockgroup to SANDAG MGRA using the
following methodology.

    1). The percentage of 18-64 year olds across MGRAs within each blockgroup
        after removing 'Group Quarters - Institutional Correctional Facilities'
        and 'Group Quarters - Military' persons.
    2). The percentage of all persons across MGRAs within each blockgroup
    3). An equal split across MGRAs within each blockgroup
*/

-- Initialize parameters -----------------------------------------------------
DECLARE @run_id INTEGER = :run_id;
DECLARE @year INTEGER = :year;
DECLARE @msg nvarchar(25) = 'ACS 5-Year Table does not exist';

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

    -- Get blockgroup to MGRA cross reference ------------------------------------
    -- Population aged 18-64 excluding Military and Prisons
    WITH [18_64] AS (
        SELECT
            [mgra],
            SUM([value]) AS [value]
        FROM [outputs].[ase]
        WHERE
            [run_id] = @run_id
            AND [year] = @year
            AND [value] > 0
            AND [pop_type] NOT IN (
                'Group Quarters - Military',
                'Group Quarters - Institutional Correctional Facilities'
            )
            AND [age_group] IN (
                '18 and 19',
                '20 to 24',
                '25 to 29',
                '30 to 34',
                '35 to 39',
                '40 to 44',
                '45 to 49',
                '50 to 54',
                '55 to 59',
                '60 and 61',
                '62 to 64'
            )
        GROUP BY [mgra]
    ),
    -- Total population without exclusions
    [pop] AS (
        SELECT
            [mgra],
            SUM([value]) AS [value]
        FROM [outputs].[ase]
        WHERE
            [run_id] = @run_id
            AND [year] = @year
            AND [value] > 0
        GROUP BY [mgra]
    ),
    -- Exxhaustive list of MGRAs and Blockgroups
    [mgras] AS (
        SELECT
            [mgra],
            CASE
                WHEN @year BETWEEN 2010 AND 2019 THEN [2010_census_blockgroup]
                WHEN @year BETWEEN 2020 AND 2029 THEN [2020_census_blockgroup]
            END AS [blockgroup]
        FROM [inputs].[mgra]
        WHERE [run_id] = @run_id
    )
    -- Return cross reference with flag field indicating which to use
    SELECT
        [blockgroup],
        [mgras].[mgra],
        COALESCE(
            1.0 * [18_64].[value] 
            / SUM([18_64].[value]) OVER (PARTITION BY [blockgroup])
            , 0) 
        AS [pct_18_64],
        COALESCE(
            1.0 * [pop].[value] 
            / SUM([pop].[value]) OVER (PARTITION BY [blockgroup])
            , 0) 
        AS [pct_pop],
        1.0 / COUNT([blockgroup]) OVER (PARTITION BY [blockgroup]) AS [pct_split],
        CASE
            WHEN SUM([18_64].[value]) OVER (PARTITION BY [blockgroup]) > 0 
                THEN 'pct_18_64'
            WHEN SUM([pop].[value]) OVER (PARTITION BY [blockgroup]) > 0 
                THEN 'pct_pop'
            ELSE 'pct_split'
        END AS [flag]
    FROM [mgras]
    LEFT OUTER JOIN [18_64]
        ON [mgras].[mgra] = [18_64].[mgra]
    LEFT OUTER JOIN [pop]
        ON [mgras].[mgra] = [pop].[mgra]
    ORDER BY
        [blockgroup],
        [mgras].[mgra]
END