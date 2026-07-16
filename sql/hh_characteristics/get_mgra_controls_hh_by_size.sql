/*
Get MGRA controls for household population used in households by household size.
This data is pulled from previously run modules.

Two input parameters are used
    run_id - the run identifier for this run
    year - the year parameter grabs the year of data to use
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