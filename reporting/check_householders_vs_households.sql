-- SQL script to check consistency between householders and households. Basically, every
-- household needs at least one household population of householder age, which is 15+.
-- See the Census website for additional details:
-- https://www.census.gov/glossary/?term=Householder
DECLARE @run_id INTEGER = :run_id;

SELECT
    [householder_aged_hhp].[year],
    [householder_aged_hhp].[mgra],
    [householder_aged_hhp],
    [hh]
FROM (
        SELECT
            [year],
            [mgra],
            SUM([value]) AS [householder_aged_hhp]
        FROM [outputs].[ase]
        WHERE [run_id] = @run_id
            AND [pop_type] = 'Household Population'
            AND [age_group] NOT IN ('Under 5', '5 to 9', '10 to 14')
        GROUP BY [year], [mgra]
    ) AS [householder_aged_hhp]
LEFT JOIN (
        SELECT
            [year],
            [mgra],
            SUM([value]) AS [hh]
        FROM [outputs].[hh]
        WHERE [run_id] = @run_id
        GROUP BY [year], [mgra]
    ) AS [hh]
    ON [householder_aged_hhp].[year] = [hh].[year]
    AND [householder_aged_hhp].[mgra] = [hh].[mgra]
WHERE [householder_aged_hhp] < [hh]