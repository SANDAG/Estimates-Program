/*
Get BLS QCEW jobs by ownership at aggregation level 73 (Supersector). Ensure
that all ownerships and supersectors are represented, filling in 0s where
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
    -- Create shell table of all ownership and supersector combinations
    DROP TABLE IF EXISTS [#tt_shell]
    SELECT [ownership_title], [supersector], [domain]
    INTO [#tt_shell]
    FROM (
        VALUES
            ('Federal Government'),
            ('State Government'),
            ('Local Government'),
            ('Private')
    ) AS [tt1] ([ownership_title])
    CROSS JOIN (
        SELECT DISTINCT [supersector], [domain]
        FROM [socioec_data].[bls].[naics_aggregation]
    ) AS [supersector];


    -- Get Annual QCEW totals by ownership and supersector
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
            AND [area_fips] = '06073'  -- San Diego County
            AND [agglvl_code] = 73  -- Aggregation level 73 (Supersector)
    )
    SELECT
        [#tt_shell].[ownership_title],
        [#tt_shell].[supersector],
        [#tt_shell].[domain],
        ISNULL([annual_avg_emplvl], 0) AS [jobs],
        ISNULL([disclosure_code], '') AS [disclosure_code]
    FROM [#tt_shell]
    LEFT OUTER JOIN [qcew]
        ON [#tt_shell].[ownership_title] = [qcew].[ownership_title]
        AND [#tt_shell].[supersector] = [qcew].[industry_code]
    ORDER BY
        [ownership_title],
        [supersector],
        [domain]

    DROP TABLE IF EXISTS [#tt_shell]
END