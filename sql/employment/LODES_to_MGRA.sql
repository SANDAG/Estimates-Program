-- Initialize parameters -----------------------------------------------------
DECLARE @year integer = :year;  
DECLARE @mgra_version nvarchar(10) = :mgra_version; 


-- Send error message if no data exists --------------------------------------
IF NOT EXISTS (
    SELECT TOP (1) *
	FROM [socioec_data].[lehd].[lodes_8_wac]
    WHERE [SEG] = 'S000'
      AND [TYPE] = 'JT00'
      AND [version] = 2
      AND [YEAR] = @year
)
SELECT 'Data does not exist' AS [msg] 
ELSE
BEGIN


    -- All MGRAs 
    WITH [AllMGRAs] AS (
        SELECT DISTINCT CAST([zone] AS INT) AS [MGRA]
        FROM [GeoAnalyst].[geography].[zone]
        WHERE [geography_id] = 
            CASE 
                WHEN @mgra_version = 'mgra15' THEN 4 -- which mgra list to grab from table, here is where to add more mgra versions to grab
                ELSE NULL 
            END
    ),

    -- All industry codes (2 - Digit NAICS)
    [AllIndustries] AS (
        SELECT [industry_code]
        FROM (VALUES 
            ('11'),
            ('21'),
            ('22'),
            ('23'),
            ('31-33'),
            ('42'),
            ('44-45'),
            ('48-49'),
            ('51'),
            ('52'),
            ('53'),
            ('54'),
            ('55'),
            ('56'),
            ('61'),
            ('62'),
            ('71'),
            ('72'),
            ('81'),
            ('92')
        ) AS i(industry_code)
    ),

    -- Create the cross product = every MGRA × every industry_code
    [AllCombinations] AS (
        SELECT 
            [MGRA],
            [industry_code]
        FROM [AllMGRAs]
        CROSS JOIN [AllIndustries]
    ),
  
    -- aggregated Jobs data from LEHD LODES into MGRAs that exist in xwalk from Census Block to MGRA
    [AggregatedJobs] AS (
        SELECT 
            [YEAR],
            [MGRA],
            [industry_code],
            SUM([value]) AS [jobs]
        FROM [socioec_data].[lehd].[lodes_8_wac]
        INNER JOIN (
            SELECT 
                [xref_id],
                [from_zone_id],
                [block].[zone] AS [CTblock],
                [to_zone_id],
                CAST([MGRA15].[zone] AS INT) AS [MGRA],
                [allocation_pct]
            FROM [GeoAnalyst].[geography].[xref_zone]
            INNER JOIN [GeoAnalyst].[geography].[zone] AS [block]
                ON [xref_zone].[from_zone_id] = [block].[zone_id]
            INNER JOIN [GeoAnalyst].[geography].[zone] AS [MGRA15]
                ON [xref_zone].[to_zone_id] = [MGRA15].[zone_id]
            WHERE 
                -- This is where to specify which xref to use based on MGRA version
                -- Curretly only works using mgra15 but this is where to add if additional mgra versions to be used
            [xref_id] = 
                CASE 
                    WHEN @mgra_version = 'mgra15' THEN 18 
                    ELSE NULL 
                END
        ) AS [XREF]
            ON [lodes_8_wac].[w_geocode] = [XREF].[CTblock]
        CROSS APPLY (
            VALUES
                ('11',   [CNS01] * [allocation_pct]),
                ('21',   [CNS02] * [allocation_pct]),
                ('22',   [CNS03] * [allocation_pct]),
                ('23',   [CNS04] * [allocation_pct]),
                ('31-33',[CNS05] * [allocation_pct]),
                ('42',   [CNS06] * [allocation_pct]),
                ('44-45',[CNS07] * [allocation_pct]),
                ('48-49',[CNS08] * [allocation_pct]),
                ('51',   [CNS09] * [allocation_pct]),
                ('52',   [CNS10] * [allocation_pct]),
                ('53',   [CNS11] * [allocation_pct]),
                ('54',   [CNS12] * [allocation_pct]),
                ('55',   [CNS13] * [allocation_pct]),
                ('56',   [CNS14] * [allocation_pct]),
                ('61',   [CNS15] * [allocation_pct]),
                ('62',   [CNS16] * [allocation_pct]),
                ('71',   [CNS17] * [allocation_pct]),
                ('72',   [CNS18] * [allocation_pct]),
                ('81',   [CNS19] * [allocation_pct]),
                ('92',   [CNS20] * [allocation_pct])
        ) AS u([industry_code], [value])
        WHERE [SEG] = 'S000'
          AND [TYPE] = 'JT00'
          AND [version] = 2
          AND [YEAR] = @year
        GROUP BY [YEAR], [MGRA], [industry_code]
    )
  
    
    -- Final result: left join the aggregated jobs to the full combinations
    SELECT 
        @year AS [YEAR],    
        [AllCombinations].[MGRA],
        [AllCombinations].[industry_code],
        COALESCE([AggregatedJobs].[jobs], 0) AS [jobs]
    FROM [AllCombinations] 
    LEFT JOIN [AggregatedJobs] 
        ON [AggregatedJobs].[MGRA] = [AllCombinations].[MGRA]
       AND [AggregatedJobs].[industry_code] = [AllCombinations].[industry_code]
    ORDER BY [AllCombinations].[MGRA], [AllCombinations].[industry_code] 
END

