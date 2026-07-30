/*
    Get LEHD LODES data mapped to SANDAG employment categories.

    The mapping below used for [CNS01] to [CNS20] to [niacs_code] (2-digit NAICS) in WAC 
    section of the document linked below. The mapping for [SEG] and [TYPE] are included in 
    the OD section of document linked below.
        https://lehd.ces.census.gov/doc/help/onthemap/LODESTechDoc.pdf
    For any other LEHD LODES data questions check: https://lehd.ces.census.gov/data/

    SANDAG employment categories are defined here:
        https://github.com/SANDAG/Estimates-Program/issues/281

    This result set cannot be used to determine raw employment counts or aggregated
    across ownerships as data is purposefully duplicated with the State and Local
    Government categories due to limitations of the LEHD LODES data.
*/

SET NOCOUNT ON;
-- Initialize parameters -----------------------------------------------------
DECLARE @year INTEGER = :year;  
DECLARE @msg NVARCHAR(25) = 'LODES data does not exist';
DECLARE @lodes_version INTEGER = 2 -- lodes v8.4

-- Send error message if no data exists --------------------------------------
IF NOT EXISTS (
    SELECT TOP (1) *
    FROM [socioec_data].[lehd].[lodes_8_wac]
    WHERE 
        [SEG] = 'S000' -- 'S000' = 'Total number of jobs'
        AND [TYPE] = 'JT00' -- 'JT00' = 'All Jobs'
        AND [version] = @lodes_version
        AND [YEAR] = @year
)
BEGIN
    SELECT @msg AS [msg]
END
ELSE
BEGIN
    -- Get LEHD LODES jobs by ownership and industry code (NAICS) ------------
    WITH [lodes_data] AS (
        -- Build the return table of QCEW control Totals by industry_code (NAICS) ---
        SELECT 
            -- https://github.com/SANDAG/Estimates-Program/issues/193
            CASE
                WHEN [w_geocode] = '060730106012030' THEN '060730106012027'
                WHEN [w_geocode] IN ('060730183012003', '060730183012004') 
                    THEN '060730183012010'
                ELSE [w_geocode]
            END AS [block],
            CASE
                WHEN [TYPE] = 'JT00' THEN 'Total Covered'
                WHEN [TYPE] = 'JT02' THEN 'Private'
                WHEN [TYPE] = 'JT04' THEN 'Federal Government'
                ELSE NULL
            END AS [ownership_title],
            [industry_code],
            SUM([value]) AS [jobs]
        FROM [socioec_data].[lehd].[lodes_8_wac]
        CROSS APPLY (
            VALUES
                ('11',   [CNS01]),
                ('21',   [CNS02]),
                ('22',   [CNS03]),
                ('23',   [CNS04]),
                ('31-33',[CNS05]),
                ('42',   [CNS06]),
                ('44-45',[CNS07]),
                ('48-49',[CNS08]),
                ('51',   [CNS09]),
                ('52',   [CNS10]),
                ('53',   [CNS11]),
                ('54',   [CNS12]),
                ('55',   [CNS13]),
                ('56',   [CNS14]),
                ('61',   [CNS15]),
                ('62',   [CNS16]),
                ('71',   [CNS17]),
                ('72',   [CNS18]),  -- LEHD LODES does not allow a 721/722 split
                ('81',   [CNS19]),
                ('92',   [CNS20])
        ) AS u([industry_code], [value]) 
        WHERE 
            [SEG] = 'S000' -- 'S000' = 'Total number of jobs' 
            AND [TYPE] IN ('JT00', 'JT02', 'JT04')
            AND [version] = @lodes_version
            AND [YEAR] = @year
        GROUP BY  
            -- https://github.com/SANDAG/Estimates-Program/issues/193
            CASE
                WHEN [w_geocode] = '060730106012030' THEN '060730106012027'
                WHEN [w_geocode] IN ('060730183012003', '060730183012004') 
                    THEN '060730183012010'
                ELSE [w_geocode]
            END,
            CASE
                WHEN [TYPE] = 'JT00' THEN 'Total Covered'
                WHEN [TYPE] = 'JT02' THEN 'Private'
                WHEN [TYPE] = 'JT04' THEN 'Federal Government'
                ELSE NULL
            END,
            [industry_code]
    ),
    -- Private-only SANDAG employment categories -----------------------------
    [private] AS (
        SELECT
            [block],
            [ownership_title],
            [industry_code],
            [jobs]
        FROM [lodes_data]
        WHERE
            [ownership_title] = 'Private'
            AND [industry_code] IN (
                '11',
                '21',
                '22',
                '23',
                '31-33',
                '42',
                '44-45',
                '48-49',
                '51',
                '52',
                '53',
                '54',
                '55',
                '56',
                '81'
            )
    ),
    -- All Ownership SANDAG employment categories ----------------------------
    [total_covered] AS (
        SELECT
            [block],
            [ownership_title],
            [industry_code],
            [jobs]
        FROM [lodes_data]
        WHERE
            [ownership_title] = 'Total Covered'
            AND [industry_code] IN (
                '61',
                '62',
                '71',
                '72'  -- LEHD LODES does not allow a 721/722 split
            )
    ),
    -- Federal Government SANDAG employment categories -----------------------
    [federal_government] AS (
        SELECT
            [block],
            [ownership_title],
            'GOV' AS [industry_code],
            SUM([jobs]) AS [jobs]
        FROM [lodes_data]
        WHERE
            [ownership_title] = 'Federal Government'
            -- Remove Total Covered SANDAG employment categories
            AND [industry_code] NOT IN (
                '61',
                '62',
                '71',
                '72'  -- LEHD LODES does not allow a 721/722 split
            )
        GROUP BY
            [block],
            [ownership_title]
    ),
    -- State and Local Government SANDAG employment categories ---------------
    -- LEHD LODES only differentiates between Private and Federal
    -- So we will use this for both the "State Government" and "Local Government"
    [state_local_government] AS (
        SELECT
            [tt_total].[block],
            [tt_total].[jobs] - ISNULL([tt_federal].[jobs], 0) AS [jobs]
        FROM (
            SELECT
                [block],
                SUM([jobs]) AS [jobs]
            FROM [lodes_data]
            WHERE
                [ownership_title] = 'Total Covered'
                AND [industry_code] NOT IN (
                    '61',
                    '62',
                    '71',
                    '72'  -- LEHD LODES does not allow a 721/722 split
                )
            GROUP BY [block]
        ) AS [tt_total]
        LEFT OUTER JOIN (
            SELECT
                [block],
                SUM([jobs]) AS [jobs]
            FROM [lodes_data]
            WHERE
                [ownership_title] = 'Federal Government'
                AND [industry_code] NOT IN (
                    '61',
                    '62',
                    '71',
                    '72'  -- LEHD LODES does not allow a 721/722 split
                )
            GROUP BY [block]
        ) AS [tt_federal]
            ON [tt_total].[block] = [tt_federal].[block]
    )
    -- Combine all ownership categories together and return result set -------
    SELECT @year AS [year], [block], [ownership_title], [industry_code], [jobs] FROM [private]
        UNION ALL
    SELECT @year AS [year], [block], [ownership_title], [industry_code], [jobs] FROM [total_covered]
        UNION ALL
    SELECT @year AS [year], [block], [ownership_title], 'GOV' AS [industry_code], [jobs] FROM [federal_government]
        UNION ALL
    SELECT @year AS [year], [block], 'State Government' AS [ownership_title], 'GOV' AS [industry_code], [jobs] FROM [state_local_government]
        UNION ALL
    SELECT @year AS [year], [block], 'Local Government' AS [ownership_title], 'GOV' AS [industry_code], [jobs] FROM [state_local_government]
    ORDER BY [block], [industry_code]

END