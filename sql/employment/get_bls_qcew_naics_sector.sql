/*
Get BLS QCEW jobs by ownership at aggregation level 74 (NAICS Sector). Ensure
that all ownerships and naics sectors are represented, filling in 0s where
appropriate. An indicator of data suppression is returned along with the data.
*/

SET NOCOUNT ON;
-- Initialize parameters -----------------------------------------------------
DECLARE @year integer = :year; 
DECLARE @msg nvarchar(25) = 'QCEW data does not exist';

-- Send error message if no data exists --------------------------------------
IF NOT EXISTS (
    SELECT TOP (1) *
    FROM [socioec_data].[bls].[qcew_by_area_annual]
    WHERE [year] = @year
)
SELECT @msg AS [msg]
ELSE
BEGIN
	-- Create shell table of all ownership and naics sector combinations
	DROP TABLE IF EXISTS [#tt_shell]
	SELECT [ownership_title], [naics_sector], [supersector], [domain]
	INTO [#tt_shell]
	FROM (
		SELECT [ownership_title] FROM (
			VALUES
				('Federal Government'),
				('State Government'),
				('Local Government'),
				('Private')
		) AS [tt1] ([ownership_title])
	) AS [ownership_title]
	CROSS JOIN (
		SELECT DISTINCT [naics_sector], [supersector], [domain]
		FROM [socioec_data].[bls].[naics_aggregation]
	) AS [naics_sector];


	-- Get Annual QCEW totals by ownership and naics sector
	WITH [qcew] AS (
		SELECT
			[ownership_title],
			[industry_code],
			[annual_avg_emplvl],
			[disclosure_code]
		FROM [socioec_data].[bls].[qcew_by_area_annual]
		INNER JOIN [socioec_data].[bls].[industry_code]
			ON [qcew_by_area_annual].[naics_id] = [industry_code].[naics_id]
		INNER JOIN [socioec_data].[bls].[ownership_titles]
			ON [qcew_by_area_annual].[own_code] = [ownership_titles].[ownership_code]
		WHERE
			[year] = @year
			AND [area_fips] = '06073'
			AND [agglvl_code] = 74
	)
	SELECT
		[#tt_shell].[ownership_title],
		[#tt_shell].[naics_sector],
		[#tt_shell].[supersector],
		[#tt_shell].[domain],
		ISNULL([annual_avg_emplvl], 0) AS [jobs],
		ISNULL([disclosure_code], '') AS [disclosure_code]
	FROM [#tt_shell]
	LEFT OUTER JOIN [qcew]
		ON [#tt_shell].[ownership_title] = [qcew].[ownership_title]
		AND [#tt_shell].[naics_sector] = [qcew].[industry_code]
	ORDER BY
		[ownership_title],
		[naics_sector],
		[supersector],
		[domain]
END