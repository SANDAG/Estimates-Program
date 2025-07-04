/*
This query gets MGRA level households which have already been created by the Housing and
Households module

This SQL script is used in both the Population module and the Household Characteristics
module.
*/


SET NOCOUNT ON;
-- Initialize parameters and return table ------------------------------------
DECLARE @run_id integer = :run_id;
DECLARE @year integer = :year;
DECLARE @mgra_version nvarchar(10) = :mgra_version;

-- Pull the data from the relevant table
SELECT
    [run_id],
    [year],
    [hh].[mgra],
    [tract],
    [city],
    SUM([value]) AS [hh]
FROM [outputs].[hh]
LEFT OUTER JOIN (
    SELECT
        [mgra],
        CASE
            WHEN @year BETWEEN 2010 AND 2019 THEN [2010_census_tract]
            WHEN @year BETWEEN 2020 AND 2029 THEN [2020_census_tract]
            ELSE NULL
        END AS [tract],
        CASE
            WHEN @mgra_version = 'mgra15' THEN [cities_2020]
            ELSE NULL
        END AS [city]
    FROM [inputs].[mgra]
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
    [city]
