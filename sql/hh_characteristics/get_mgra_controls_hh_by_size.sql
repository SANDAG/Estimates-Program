/*
Get MGRA controls for household population used in households by household size.
This data is pulled from previously run modules.

Two input parameters are used
    run_id - the run identifier is used to get the list of census tracts in tandem with
        the year parameter that determines their vintage
    year - the year parameter is used to identify the 5-year ACS Detailed Tables release
        to use (ex. 2023 maps to 2019-2023) and the census tract geography vintage
        (2010-2019 uses 2010, 2020-2029 uses 2020)
*/

-- Initialize parameters
DECLARE @run_id integer = :run_id;
DECLARE @year integer = :year;

-- Get household population
SELECT
    @run_id AS [run_id],
    @year AS [year],
    [mgra],
    [value] AS [hhp_total]
FROM [outputs].[hhp]
WHERE
    [run_id] = @run_id
    AND [year] = @year