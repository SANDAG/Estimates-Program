/*
Compare two Estimates runs and return any records wherein values for run "a"
do not match or are not present in run "b". Note that run "a" is considered
the baseline run and run "b" the comparison run. If run "b" contains any
records not already present in run "a" those records will be ignored. When no
records are returned that indicates no differences exist between the runs.
*/

-- Initialize the baseline and comparison run identifiers
DECLARE @baseline INTEGER = 224;
DECLARE @comparison INTEGER = 233;


-- Check comparison is valid -------------------------------------------------
-- Both runs are complete
IF EXISTS (SELECT [run_id] FROM [metadata].[run] WHERE [complete] = 0 AND [run_id] IN (@baseline, @comparison))
BEGIN
	THROW 50000, 'Both provided [run_id]s must be complete', 1;
END

-- Both runs use the same MGRA series
IF ((SELECT [series] FROM [metadata].[run] WHERE [run_id] = @baseline) != (SELECT [series] FROM [metadata].[run] WHERE [run_id] = @comparison))
BEGIN
	THROW 50000, 'The provided [run_id]s must use the same MGRA series', 1;
END

-- Check that there is overlap between start/end years
IF NOT (
	(SELECT [start_year] FROM [metadata].[run] WHERE [run_id] = @baseline) <= (SELECT [end_year] FROM [metadata].[run] WHERE [run_id] = @comparison)
	AND (SELECT [start_year] FROM [metadata].[run] WHERE [run_id] = @comparison) <= (SELECT [end_year] FROM [metadata].[run] WHERE [run_id] = @baseline)
)
BEGIN
	THROW 50000, 'The provided [run_id]s must contain at least one overlapping year', 1;
END


-- Check all inputs are identical --------------------------------------------

-- Check Age/Sex/Ethnicity controls
SELECT
	[baseline].[year],
	[baseline].[pop_type],
	[baseline].[age_group],
	[baseline].[sex],
	[baseline].[ethnicity],
	[baseline].[value] AS [baseline],
	[comparison].[value] AS [comparison]
FROM (
	SELECT * FROM [inputs].[controls_ase]
	WHERE [run_id] = @baseline
) AS [baseline]
LEFT OUTER JOIN (
	SELECT * FROM [inputs].[controls_ase]
	WHERE [run_id] = @comparison
) AS [comparison]
ON
	[baseline].[year] = [comparison].[year]
	AND [baseline].[pop_type] = [comparison].[pop_type]
	AND [baseline].[age_group] = [comparison].[age_group]
	AND [baseline].[sex] = [comparison].[sex]
	AND [baseline].[ethnicity] = [comparison].[ethnicity]
WHERE
	[baseline].[value] != [comparison].[value]
	OR [comparison].[value] IS NULL
ORDER BY
	[baseline].[year],
	[baseline].[pop_type],
	[baseline].[age_group],
	[baseline].[sex],
	[baseline].[ethnicity]


-- Check Jobs controls
SELECT
	[baseline].[year],
	[baseline].[ownership_title],
	[baseline].[industry_code],
	[baseline].[value] AS [baseline],
	[comparison].[value] AS [comparison]
FROM (
	SELECT * FROM [inputs].[controls_jobs]
	WHERE [run_id] = @baseline
) AS [baseline]
LEFT OUTER JOIN (
	SELECT * FROM [inputs].[controls_jobs]
	WHERE [run_id] = @comparison
) AS [comparison]
ON
	[baseline].[year] = [comparison].[year]
	AND [baseline].[ownership_title] = [comparison].[ownership_title]
	AND [baseline].[industry_code] = [comparison].[industry_code]
WHERE
	[baseline].[value] != [comparison].[value]
	OR [comparison].[value] IS NULL
ORDER BY
	[baseline].[year],
	[baseline].[ownership_title],
	[baseline].[industry_code]


-- Check Jurisdiction controls
SELECT
	[baseline].[year],
	[baseline].[jurisdiction],
	[baseline].[metric],
	[baseline].[value] AS [baseline],
	[comparison].[value] AS [comparison]
FROM (
	SELECT * FROM [inputs].[controls_jurisdiction]
	WHERE [run_id] = @baseline
) AS [baseline]
LEFT OUTER JOIN (
	SELECT * FROM [inputs].[controls_jurisdiction]
	WHERE [run_id] = @comparison
) AS [comparison]
ON
	[baseline].[year] = [comparison].[year]
	AND [baseline].[jurisdiction] = [comparison].[jurisdiction]
	AND [baseline].[metric] = [comparison].[metric]
WHERE
	[baseline].[value] != [comparison].[value]
	OR [comparison].[value] IS NULL
ORDER BY
	[baseline].[year],
	[baseline].[jurisdiction],
	[baseline].[metric]


-- Check Tract controls
SELECT
	[baseline].[year],
	[baseline].[tract],
	[baseline].[metric],
	[baseline].[value] AS [baseline],
	[comparison].[value] AS [comparison]
FROM (
	SELECT * FROM [inputs].[controls_tract]
	WHERE [run_id] = @baseline
) AS [baseline]
LEFT OUTER JOIN (
	SELECT * FROM [inputs].[controls_tract]
	WHERE [run_id] = @comparison
) AS [comparison]
ON
	[baseline].[year] = [comparison].[year]
	AND [baseline].[tract] = [comparison].[tract]
	AND [baseline].[metric] = [comparison].[metric]
WHERE
	[baseline].[value] != [comparison].[value]
	OR [comparison].[value] IS NULL
ORDER BY
	[baseline].[year],
	[baseline].[tract],
	[baseline].[metric]


-- Check all outputs are identical -------------------------------------------

-- Check Age/Sex/Ethnicity population
SELECT
	[baseline].[year],
	[baseline].[mgra],
	[baseline].[pop_type],
	[baseline].[age_group],
	[baseline].[sex],
	[baseline].[ethnicity],
	[baseline].[value] AS [baseline],
	[comparison].[value] AS [comparison]
FROM (
	SELECT * FROM [outputs].[ase]
	WHERE [run_id] = @baseline
) AS [baseline]
LEFT OUTER JOIN (
	SELECT * FROM [outputs].[ase]
	WHERE [run_id] = @comparison
) AS [comparison]
ON
	[baseline].[year] = [comparison].[year]
	AND [baseline].[mgra] = [comparison].[mgra]
	AND [baseline].[pop_type] = [comparison].[pop_type]
	AND [baseline].[age_group] = [comparison].[age_group]
	AND [baseline].[sex] = [comparison].[sex]
	AND [baseline].[ethnicity] = [comparison].[ethnicity]
WHERE
	[baseline].[value] != [comparison].[value]
	OR [comparison].[value] IS NULL
ORDER BY
	[baseline].[year],
	[baseline].[mgra],
	[baseline].[pop_type],
	[baseline].[age_group],
	[baseline].[sex],
	[baseline].[ethnicity]


-- Check Group Quarters population
SELECT
	[baseline].[year],
	[baseline].[mgra],
	[baseline].[gq_type],
	[baseline].[value] AS [baseline],
	[comparison].[value] AS [comparison]
FROM (
	SELECT * FROM [outputs].[gq]
	WHERE [run_id] = @baseline
) AS [baseline]
LEFT OUTER JOIN (
	SELECT * FROM [outputs].[gq]
	WHERE [run_id] = @comparison
) AS [comparison]
ON
	[baseline].[year] = [comparison].[year]
	AND [baseline].[mgra] = [comparison].[mgra]
	AND [baseline].[gq_type] = [comparison].[gq_type]
WHERE
	[baseline].[value] != [comparison].[value]
	OR [comparison].[value] IS NULL
ORDER BY
	[baseline].[year],
	[baseline].[mgra],
	[baseline].[gq_type]


-- Check Households
SELECT
	[baseline].[year],
	[baseline].[mgra],
	[baseline].[structure_type],
	[baseline].[value] AS [baseline],
	[comparison].[value] AS [comparison]
FROM (
	SELECT * FROM [outputs].[hh]
	WHERE [run_id] = @baseline
) AS [baseline]
LEFT OUTER JOIN (
	SELECT * FROM [outputs].[hh]
	WHERE [run_id] = @comparison
) AS [comparison]
ON
	[baseline].[year] = [comparison].[year]
	AND [baseline].[mgra] = [comparison].[mgra]
	AND [baseline].[structure_type] = [comparison].[structure_type]
WHERE
	[baseline].[value] != [comparison].[value]
	OR [comparison].[value] IS NULL
ORDER BY
	[baseline].[year],
	[baseline].[mgra],
	[baseline].[structure_type]


-- Check Household characteristics
SELECT
	[baseline].[year],
	[baseline].[mgra],
	[baseline].[metric],
	[baseline].[value] AS [baseline],
	[comparison].[value] AS [comparison]
FROM (
	SELECT * FROM [outputs].[hh_characteristics]
	WHERE [run_id] = @baseline
) AS [baseline]
LEFT OUTER JOIN (
	SELECT * FROM [outputs].[hh_characteristics]
	WHERE [run_id] = @comparison
) AS [comparison]
ON
	[baseline].[year] = [comparison].[year]
	AND [baseline].[mgra] = [comparison].[mgra]
	AND [baseline].[metric] = [comparison].[metric]
WHERE
	[baseline].[value] != [comparison].[value]
	OR [comparison].[value] IS NULL
ORDER BY
	[baseline].[year],
	[baseline].[mgra],
	[baseline].[metric]


-- Check Household population
SELECT
	[baseline].[year],
	[baseline].[mgra],
	[baseline].[value] AS [baseline],
	[comparison].[value] AS [comparison]
FROM (
	SELECT * FROM [outputs].[hhp]
	WHERE [run_id] = @baseline
) AS [baseline]
LEFT OUTER JOIN (
	SELECT * FROM [outputs].[hhp]
	WHERE [run_id] = @comparison
) AS [comparison]
ON
	[baseline].[year] = [comparison].[year]
	AND [baseline].[mgra] = [comparison].[mgra]
WHERE
	[baseline].[value] != [comparison].[value]
	OR [comparison].[value] IS NULL
ORDER BY
	[baseline].[year],
	[baseline].[mgra]


-- Check Housing Stock
SELECT
	[baseline].[year],
	[baseline].[mgra],
	[baseline].[structure_type],
	[baseline].[value] AS [baseline],
	[comparison].[value] AS [comparison]
FROM (
	SELECT * FROM [outputs].[hs]
	WHERE [run_id] = @baseline
) AS [baseline]
LEFT OUTER JOIN (
	SELECT * FROM [outputs].[hs]
	WHERE [run_id] = @comparison
) AS [comparison]
ON
	[baseline].[year] = [comparison].[year]
	AND [baseline].[mgra] = [comparison].[mgra]
	AND [baseline].[structure_type] = [comparison].[structure_type]
WHERE
	[baseline].[value] != [comparison].[value]
	OR [comparison].[value] IS NULL
ORDER BY
	[baseline].[year],
	[baseline].[mgra],
	[baseline].[structure_type]


-- Check Jobs
SELECT
	[baseline].[year],
	[baseline].[mgra],
	[baseline].[ownership_title],
	[baseline].[industry_code],
	[baseline].[value] AS [baseline],
	[comparison].[value] AS [comparison]
FROM (
	SELECT * FROM [outputs].[jobs]
	WHERE [run_id] = @baseline
) AS [baseline]
LEFT OUTER JOIN (
	SELECT * FROM [outputs].[jobs]
	WHERE [run_id] = @comparison
) AS [comparison]
ON
	[baseline].[year] = [comparison].[year]
	AND [baseline].[mgra] = [comparison].[mgra]
	AND [baseline].[ownership_title] = [comparison].[ownership_title]
	AND [baseline].[industry_code] = [comparison].[industry_code]
WHERE
	[baseline].[value] != [comparison].[value]
	OR [comparison].[value] IS NULL
ORDER BY
	[baseline].[year],
	[baseline].[mgra],
	[baseline].[ownership_title],
	[baseline].[industry_code]