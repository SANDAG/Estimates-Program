/*
Get LEHD LODES data.

The mapping below used for [CNS01] to [CNS20] to [niacs_code] (2-digit NAICS) in WAC 
section of the document linked below. The mapping for [SEG] and [TYPE] are included in 
the OD section of document linked below.

https://lehd.ces.census.gov/doc/help/onthemap/LODESTechDoc.pdf

For any other LEHD LODES data questions check: https://lehd.ces.census.gov/data/
*/

-- Initialize parameters -----------------------------------------------------
DECLARE @year integer = :year;  
DECLARE @msg nvarchar(25) = 'LODES data does not exist';

-- Send error message if no data exists --------------------------------------
IF NOT EXISTS (
    SELECT TOP (1) *
    FROM [socioec_data].[lehd].[lodes_8_wac]
    WHERE 
        [SEG] = 'S000' -- 'S000' = 'Total number of jobs'
        AND [TYPE] = 'JT00' -- 'JT00' = 'All Jobs'
        AND [version] = 2 -- lodes v8.4
        AND [YEAR] = @year
)
BEGIN
    SELECT @msg AS [msg]
END
ELSE
BEGIN
    -- Build the return table of QCEW control Totals by naics_code (NAICS) ---
    SELECT 
        [YEAR] AS [year],
        -- https://github.com/SANDAG/Estimates-Program/issues/193
        CASE
            WHEN [w_geocode] = '060730106012030' THEN '060730106012027'
            WHEN [w_geocode] IN ('060730183012003', '060730183012004') 
                THEN '060730183012010'
            ELSE [w_geocode]
        END AS [block],
        [naics_code],
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
            ('72',   [CNS18]),
            ('81',   [CNS19]),
            ('92',   [CNS20])
    ) AS u([naics_code], [value]) 
    WHERE 
        [SEG] = 'S000' -- 'S000' = 'Total number of jobs' 
        AND [TYPE] = 'JT00' -- 'JT00' = 'All Jobs' 
        AND [version] = 2 -- lodes v8.4
        AND [YEAR] = @year
    GROUP BY 
        [YEAR], 
        -- https://github.com/SANDAG/Estimates-Program/issues/193
        CASE
            WHEN [w_geocode] = '060730106012030' THEN '060730106012027'
            WHEN [w_geocode] IN ('060730183012003', '060730183012004') 
                THEN '060730183012010'
            ELSE [w_geocode]
        END, 
        [naics_code]
    ORDER BY 
        [year],
        [block],
        [naics_code]
END
------------------------------------------------------------------------------