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
	[tract],
	[city],
	[structure_type],
	[value]
FROM [outputs].[hs]
LEFT OUTER JOIN (
	SELECT
		[mgra],
		CASE WHEN @year BETWEEN 2010 AND 2019 THEN [2010_census_tract]
		     WHEN @year BETWEEN 2020 AND 2029 THEN [2020_census_tract]
			 ELSE NULL END AS [tract],
        CASE WHEN @mgra_version = 'mgra15' THEN [cities_2020] ELSE NULL END AS [city]
	FROM [inputs].[mgra]
	WHERE [run_id] = @run_id
) AS [tracts]
	ON [hs].[mgra] = [tracts].[mgra]
WHERE
	[run_id] = @run_id
	AND [year] = @year