/*
Get BLS QCEW jobs by ownership at aggregation level 75 (NAICS 3-digit). This
is only for codes 721 and 722 as NAICS sector 72 is the only sector SANDAG
splits out into three digit NAICS. Ensure that all ownerships are represented,
filling in 0s where appropriate. An indicator of data suppression is returned
along with the data.
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
	-- Create shell table of all ownership and naics 3-digit combinations
	-- Only 721 and 722 are of interest
	DROP TABLE IF EXISTS [#tt_shell]
	SELECT [ownership_title], [naics3], [naics_sector], [supersector], [domain]
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
	) AS [naics_sector]
	INNER JOIN (
		SELECT [naics3] FROM (
			VALUES
				('721'),
				('722')
		) AS [tt2] ([naics3])
	) AS [naics3]
	ON [naics_sector].[naics_sector] = '72';


	-- Get Annual QCEW totals by ownership and naics 3-digit for 721 and 722
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
			AND [agglvl_code] = 75
			AND [industry_code] IN ('721', '722')
	)
	SELECT
		[#tt_shell].[ownership_title],
		[#tt_shell].[naics3],
		[#tt_shell].[naics_sector],
		[#tt_shell].[supersector],
		[#tt_shell].[domain],
		ISNULL([annual_avg_emplvl], 0) AS [jobs],
		ISNULL([disclosure_code], '') AS [disclosure_code]
	FROM [#tt_shell]
	LEFT OUTER JOIN [qcew]
		ON [#tt_shell].[ownership_title] = [qcew].[ownership_title]
		AND [#tt_shell].[naics3] = [qcew].[industry_code]
	ORDER BY
		[ownership_title],
		[naics3],
		[naics_sector],
		[supersector],
		[domain]
END