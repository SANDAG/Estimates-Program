/*
This query gets MGRA level households which have already been created by the Housing and
Households module

This SQL script is used in both the Population module and the Household Characteristics
module.
*/


SET NOCOUNT ON;
-- Initialize parameters and return table ------------------------------------
DECLARE @run_id INTEGER = :run_id;
DECLARE @year INTEGER = :year;
DECLARE @series INTEGER = (SELECT [series] FROM [metadata].[run] WHERE [run_id] = @run_id);

-- Pull the data from the relevant table
SELECT
    [run_id],
    [year],
    [hh].[mgra],
    [tract],
    [jurisdiction],
    SUM([value]) AS [hh]
FROM [outputs].[hh]
LEFT OUTER JOIN (
    SELECT
        [mgra].[mgra],
        [tract],
        [jurisdiction]
    FROM [inputs].[mgra]
    INNER JOIN [demographic_warehouse].[dim].[mgra] AS [dw_mgra]
        ON [mgra].[mgra] = [dw_mgra].[mgra]
        AND [dw_mgra].[series] = @series
    INNER JOIN [demographic_warehouse].[dim].[mgra_xref]
        ON [dw_mgra].[mgra_id] = [mgra_xref].[mgra_id]
        AND [mgra_xref].[xref_year] = @year
    WHERE [run_id] = @run_id
) AS [tracts]
    ON [hh].[mgra] = [tracts].[mgra]
WHERE [run_id] = @run_id
    AND [year] = @year
GROUP BY
    [run_id],
    [year],
    [hh].[mgra],
    [tract],
    [jurisdiction]
