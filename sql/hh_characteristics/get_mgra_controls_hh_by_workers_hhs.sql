/*
Get MGRA controls for households by size used in households by number of workers.
This data is pulled from previously run portions of this module.

Since households by workers only contains (0,1,2,3+) categories, the household
size categories are collapsed to (2+,3+) to match the minimum implied household
sizes from the households by workers categories (e.g. 0 and 1 worker households
can be any size 1+, a 2 worker household must be at least size 2, and a three
worker household must be at least size 3).

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
    SUM(
        CASE 
            WHEN [metric] != 'Household Size - 1' THEN [value] 
            ELSE 0
        END
    ) AS [2],  -- 2+ household size
    SUM(
        CASE 
            WHEN [metric] NOT IN (
                'Household Size - 1',
                'Household Size - 2'
            ) THEN [value] 
            ELSE 0
        END
    ) AS [3]  -- 3+ household size
FROM [outputs].[hh_characteristics]
WHERE
    [run_id] = @run_id
    AND [year] = @year
    AND [metric] LIKE 'Household Size%'
GROUP BY [mgra]
ORDER BY [mgra]