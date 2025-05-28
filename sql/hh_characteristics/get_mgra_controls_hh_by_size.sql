/*
Get MGRA controls for households by household size, which are total household population
and household population over the age of 18. All this data is pulled from previously
run modules

Two input parameters are used
    run_id - the run identifier is used to get the list of census tracts in tandem with
        the year parameter that determines their vintage
    year - the year parameter is used to identify the 5-year ACS Detailed Tables release
        to use (ex. 2023 maps to 2019-2023) and the census tract geography vintage
        (2010-2019 uses 2010, 2020-2029 uses 2020)
*/

SET NOCOUNT ON;

-- Initialize parameters and return table
DECLARE @run_id integer = :run_id;
DECLARE @year integer = :year;

-- Get household population and household population over the age of 18
WITH [hhp_total] AS (
        SELECT
            [mgra],
            [value] AS [hhp_total]
        FROM [outputs].[hhp]
        WHERE [run_id] = @run_id
            AND [year] = @year
    ),
    [hhp_over_18] AS (
        SELECT
            [mgra],
            SUM([value]) AS [hhp_over_18]
        FROM [outputs].[ase]
        WHERE [run_id] = @run_id
            AND [year] = @year
            AND [age_group] NOT IN ('Under 5', '5 to 9', '10 to 14', '15 to 17')
        GROUP BY [mgra]
    )

-- Combine the two variables with a tract xref for easy joining later on in Python
SELECT
    @run_id AS [run_id],
    @year AS [year],
    [hhp_total].[mgra],
    [tract],
    [hhp_total],
    [hhp_over_18]
FROM [hhp_total]
LEFT JOIN [hhp_over_18]
    ON [hhp_total].[mgra] = [hhp_over_18].[mgra]
LEFT JOIN (
        SELECT
            [mgra],
            CASE
                WHEN @year BETWEEN 2010 AND 2019 THEN [2010_census_tract]
                WHEN @year BETWEEN 2020 AND 2029 THEN [2020_census_tract]
                ELSE NULL
            END AS [tract]
        FROM [inputs].[mgra]
        WHERE [run_id] = @run_id
    ) AS [tracts]
        ON [hhp_total].[mgra] = [tracts].[mgra]
