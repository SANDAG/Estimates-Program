/*
Get BLS QCEW jobs by ownership at aggregation level 72 (Domain). Ensure that
all ownerships and domains are represented, filling in 0s where appropriate.
Note that the process to create BLS QCEW regional SANDAG employment categories
relies on this aggregation level containing all non-suppressed values so an
error is thrown if any suppressed values are encountered.

As of 2010-2025, no suppressed values have been encountered at this aggregation
level for San Diego County. If this occurs in the future, the process to create
BLS QCEW regional SANDAG employment categories will need to be revised to start
at the next higher aggregation level (agglvl_code=71 or 70).
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
	-- Ensure no records are suppressed
	IF EXISTS (
		SELECT *
		FROM [socioec_data].[bls].[qcew_by_area_annual]
		WHERE
			[year] = @year
			AND [area_fips] = '06073'
			AND [agglvl_code] = 72
			AND [disclosure_code] = 'N'
	) THROW 50000, 'Control totals using [agglvl_code]=72 are suppressed', 1;


	-- Create shell table of all ownership and domain combinations
	DROP TABLE IF EXISTS [#tt_shell]
	SELECT [ownership_title], [domain]
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
		SELECT DISTINCT [domain]
		FROM [socioec_data].[bls].[naics_aggregation]
	) AS [domain];


	-- Get Annual QCEW totals by ownership and domain
	WITH [qcew] AS (
		SELECT
			[ownership_title],
			[industry_code],
			[annual_avg_emplvl]
		FROM [socioec_data].[bls].[qcew_by_area_annual]
		INNER JOIN [socioec_data].[bls].[industry_code]
			ON [qcew_by_area_annual].[naics_id] = [industry_code].[naics_id]
		INNER JOIN [socioec_data].[bls].[ownership_titles]
			ON [qcew_by_area_annual].[own_code] = [ownership_titles].[ownership_code]
		WHERE
			[year] = @year
			AND [area_fips] = '06073'
			AND [agglvl_code] = 72
	)
	SELECT
		[#tt_shell].[ownership_title],
		[#tt_shell].[domain],
		ISNULL([annual_avg_emplvl], 0) AS [jobs]
	FROM [#tt_shell]
	LEFT OUTER JOIN [qcew]
		ON [#tt_shell].[ownership_title] = [qcew].[ownership_title]
		AND [#tt_shell].[domain] = [qcew].[industry_code]
	ORDER BY
		[ownership_title],
		[domain]
END