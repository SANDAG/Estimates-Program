-- Initialize parameters -----------------------------------------------------
DECLARE @year integer = :year;  

-- Send error message if no data exists --------------------------------------
IF NOT EXISTS (
    SELECT TOP (1) *
	FROM [socioec_data].[lehd].[lodes_8_wac]
    WHERE [SEG] = 'S000'
      AND [TYPE] = 'JT00'
      AND [version] = 2
      AND [YEAR] = @year
)
SELECT 'LODES data does not exist' AS [msg] 
ELSE
BEGIN


    SELECT 
        [YEAR] AS [year],
        [w_geocode] AS [block],
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
            ('72',   [CNS18]),
            ('81',   [CNS19]),
            ('92',   [CNS20])
    ) AS u([industry_code], [value]) 
    WHERE [SEG] = 'S000'
        AND [TYPE] = 'JT00'
        AND [version] = 2
        AND [YEAR] = @year
    GROUP BY [YEAR], [w_geocode], [industry_code]
END
