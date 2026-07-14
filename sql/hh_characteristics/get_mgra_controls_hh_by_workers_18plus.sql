/*
Get MGRA controls for persons aged 18+ used in households by number of workers.
This data is pulled from previously run modules.

It would be preferable to use 16+ as that is the age of eligibility for labor
force participation in the ACS but the Estimates Program uses 15 to 17 as an
age category so there is not an easy way to select only 16+.

Two input parameters are used
    run_id - the run identifier for this run
    year - the year parameter grabs the year of data to use
*/

-- Initialize parameters
DECLARE @run_id integer = :run_id;
DECLARE @year integer = :year;

-- Get population aged 18+
WITH [ase_data] AS (
    SELECT
        [mgra],
        SUM([value]) AS [value]
    FROM [outputs].[ase]
    WHERE
        [run_id] = @run_id
        AND [year] = @year
        AND [pop_type] = 'Household Population'
        AND [age_group] NOT IN (
            'Under 5',
            '5 to 9',
            '10 to 14',
            '15 to 17'
        )
    GROUP BY [mgra]
)
-- Ensure all MGRAs are included
SELECT
    @run_id AS [run_id],
    @year AS [year],
    [mgra].[mgra],
    ISNULL([value], 0) AS [persons_18plus]
FROM [inputs].[mgra]
LEFT OUTER JOIN [ase_data]
    ON [mgra].[mgra] = [ase_data].[mgra]
WHERE
    [mgra].[run_id] = @run_id
ORDER BY [mgra].[mgra]