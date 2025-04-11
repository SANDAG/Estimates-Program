/*
This query takes the already created MGRA-level housing stock by structure 
type and transforms the data from long-format into wide-format for ease of
use by the Python program that calculates MGRA-level households.
*/

-- Initialize parameters -----------------------------------------------------
DECLARE @run_id integer = :run_id;
DECLARE @year integer = :year;
DECLARE @mgra_version nvarchar(10) = :mgra_version;

SELECT
	[run_id],
	[year],
	[hs].[mgra],
	[census_tract],
	[city],
	[structure_type],
	[value]
FROM [outputs].[hs]
LEFT OUTER JOIN (
	SELECT
		[mgra],
		[2020_census_tract] AS [census_tract],  -- TODO: use CASE statement reverting to [2010_census_tract] for years 2010-2019
        CASE WHEN @mgra_version = 'mgra15' THEN [cities_2020] ELSE NULL END AS [city]
	FROM [inputs].[mgra]
	WHERE [run_id] = @run_id
) AS [tracts]
	ON [hs].[mgra] = [tracts].[mgra]
WHERE
	[run_id] = @run_id
	AND [year] = @year