-- SQL script to check consistency between householders and household population that 
-- is 15 and over. Note we are not using the typical definition of "adult" here, which
-- would be something like 18 and over. We are instead using the exact Census 
-- definition of "Householder", which can be household population 15 and over. See the
-- Census website for additional details:
-- https://www.census.gov/glossary/?term=Householder
DECLARE @run_id INTEGER = :run_id;

SELECT
    [householder_aged_hhp].[year],
    [householder_aged_hhp].[mgra],
    [householder_aged_hhp],
    [hh_size_1]
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
            [value] AS [hh_size_1]
        FROM [outputs].[hh_characteristics]
        WHERE [run_id] = @run_id
            AND [metric] = 'Household Size - 1'
    ) AS [hhs1]
    ON [householder_aged_hhp].[year] = [hhs1].[year]
    AND [householder_aged_hhp].[mgra] = [hhs1].[mgra]
WHERE [householder_aged_hhp] < [hh_size_1]
