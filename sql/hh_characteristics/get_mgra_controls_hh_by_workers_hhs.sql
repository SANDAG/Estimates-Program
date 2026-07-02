/*
Get MGRA controls for households by size used in households by number of workers.
This data is pulled from previously run portions of this module.

Since households by workers only contains (0,1,2,3+) categories, the household
size categories are collapsed to (1,2,3+) to match the households by workers
categories.

Two input parameters are used
    run_id - the run identifier for this run
    year - the year parameter grabs the year of data to use
*/

-- Initialize parameters
DECLARE @run_id integer = :run_id;
DECLARE @year integer = :year;

-- Get households by size
SELECT
    @run_id AS [run_id],
    @year AS [year],
    [mgra],
    CASE
        WHEN [metric] IN ('Household Size - 1', 'Household Size - 2') THEN [metric]
        ELSE 'Household Size - 3+'
    END AS [household_size_3plus],
    SUM([value]) AS [hh]
FROM [outputs].[hh_characteristics]
WHERE
    [run_id] = @run_id
    AND [year] = @year
    AND [metric] LIKE 'Household Size%'
GROUP BY
    [mgra],
    CASE
        WHEN [metric] IN ('Household Size - 1', 'Household Size - 2') THEN [metric]
        ELSE 'Household Size - 3+'
    END
ORDER BY
    [mgra],
    [household_size_3plus]