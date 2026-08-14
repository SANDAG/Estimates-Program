/*
Get California Confidential EDD jobs by Ownership and 2-digit NAICS sector.
Ensure that all ownerships and naics sectors are represented, filling in 0s
and missing entries with a small constant to ensure scaling to match BLS
QCEW sums does not fail.

Note this needs to be run on the GIS server as the OPENQUERY string length
limit is reached running from the Estimates server, the EMPCORE tables contain
CLR data types, and the Linked Server connection is not set up to use SQL RPC.
This pattern also moves the most complex queries out of dynamic SQL leaving
the simplest shell table creation query in dynamic SQL.

There is no EDD point-level data for 2016 in EMPCORE and 2014 data has no
ownership values. Therefore, both return 'EDD point-level data does not exist'.

For 2017 and later, the EDD data is available through a view that allows for
the calculation of average jobs per month across the year, for the months
where data is available. For 2010-2013, the "adjusted employment" value is
used, which is a legacy calculation of unknown origin representing the only
available employment data for those years. For 2014-2016, the average of three
months of employment data is used, which we believe may be quarter 3 data, but
this is not confirmed.
*/


SET NOCOUNT ON;
-- Initialize parameters and return table ------------------------------------
DECLARE @year INTEGER = :year;
DECLARE @estimates_server NVARCHAR(20) = :estimates_server;
DECLARE @msg NVARCHAR(45) = 'EDD point-level data does not exist';
DECLARE @qry NVARCHAR(MAX)

-- Create shell table of all ownership and naics sector combinations
DROP TABLE IF EXISTS [#tt_shell];
CREATE TABLE [#tt_shell] (
    [ownership_title] NVARCHAR(20) NOT NULL,
    [naics3] NVARCHAR(3) NULL,
    [naics_sector] NVARCHAR(5) NOT NULL,
    [supersector] NVARCHAR(4) NOT NULL,
    [domain] NVARCHAR(3) NOT NULL,
    CONSTRAINT [ixuq_tt_shell] UNIQUE ([ownership_title], [naics3], [naics_sector], [supersector], [domain])
);

SET @qry = '
    INSERT INTO [#tt_shell]
    SELECT
        [ownership_title],
        [naics3],
        [naics_sector],
        [supersector],
        [domain]
    FROM (
	    SELECT [ownership_title] FROM (
		    VALUES
			    (''Federal Government''),
			    (''State Government''),
			    (''Local Government''),
			    (''Private'')
	    ) AS [tt1] ([ownership_title])
    ) AS [ownership_title]
    CROSS JOIN (
	    SELECT *
	    FROM OPENQUERY([' + @estimates_server + '], ''
            SELECT DISTINCT [naics_sector], [supersector], [domain]
            FROM [socioec_data].[bls].[naics_aggregation]
        '')
    ) AS [naics_sector]
    LEFT OUTER JOIN (
        SELECT [naics3] FROM (
            VALUES
                (''721''),
                (''722'')
        ) AS [tt2] ([naics3])
    ) AS [naics3]
    ON [naics_sector].[naics_sector] = ''72''
'
EXECUTE(@qry)

-- Create temporary table for EDD data
DROP TABLE IF EXISTS [#edd];
CREATE TABLE [#edd] (
    [ownership_title] NVARCHAR(20) NOT NULL,
    [industry_code] NVARCHAR(5) NOT NULL,
    [jobs] FLOAT NOT NULL,
    CONSTRAINT [pk_tt_edd] PRIMARY KEY ([ownership_title], [industry_code])
);


-- Get SANDAG GIS team EDD dataset -------------------------------------------
IF @year >= 2017
BEGIN
    INSERT INTO [#edd]
    SELECT
        [ownership_title],
        ISNULL([industry_code], '99') AS [industry_code],
        SUM(1.0 * [emp_total]/[emp_valid]) AS [jobs]
    FROM (
        SELECT
            CASE
                WHEN [ownership].[description] = 'Local government' THEN 'Local Government'
                WHEN [ownership].[description] = 'Federal government' THEN 'Federal Government'
                WHEN [ownership].[description] = 'Private sector' THEN 'Private'
                WHEN [ownership].[description] = 'State government' THEN 'State Government'
                ELSE NULL  -- filters out "Unknown" ownership records
            END AS [ownership_title],
            CASE
                WHEN LEFT([naics_code], 2) IN ('31','32','33') THEN '31-33'
                WHEN LEFT([naics_code], 2) IN ('44','45') THEN '44-45'
                WHEN LEFT([naics_code], 2) IN ('48','49') THEN '48-49'
                -- There are records in 2011-2012 tagged as "Self Employed" with [naics_code] = "72"
                -- There are records in all years with [naics_code] = "999999" as a NULL placeholder
                WHEN [naics_code] = '72' OR LEFT([naics_code], 2) = '99' THEN NULL
                WHEN LEFT([naics_code], 2) = '72' THEN LEFT([naics_code], 3)
                -- NULL records are mapped to NULL despite falling into this ELSE condition
                -- Keep these records for total EDD jobs xref even if industry code is NULL
                ELSE LEFT([naics_code], 2)
            END AS [industry_code],
            -- Do not consider NULL and 0 records in the dataset
            CASE WHEN [emp_m1] > 0 THEN 1 ELSE 0 END 
                + CASE WHEN [emp_m2] > 0 THEN 1 ELSE 0 END 
                + CASE WHEN [emp_m3] > 0 THEN 1 ELSE 0 END 
                + CASE WHEN [emp_m4] > 0 THEN 1 ELSE 0 END 
                + CASE WHEN [emp_m5] > 0 THEN 1 ELSE 0 END 
                + CASE WHEN [emp_m6] > 0 THEN 1 ELSE 0 END 
                + CASE WHEN [emp_m7] > 0 THEN 1 ELSE 0 END 
                + CASE WHEN [emp_m8] > 0 THEN 1 ELSE 0 END 
                + CASE WHEN [emp_m9] > 0 THEN 1 ELSE 0 END 
                + CASE WHEN [emp_m10] > 0 THEN 1 ELSE 0 END 
                + CASE WHEN [emp_m11] > 0 THEN 1 ELSE 0 END 
                + CASE WHEN [emp_m12] > 0 THEN 1 ELSE 0 END 
            AS [emp_valid],
            ISNULL([emp_m1], 0) 
                + ISNULL([emp_m2], 0) 
                + ISNULL([emp_m3], 0) 
                + ISNULL([emp_m4], 0) 
                + ISNULL([emp_m5], 0) 
                + ISNULL([emp_m6], 0) 
                + ISNULL([emp_m7], 0) 
                + ISNULL([emp_m8], 0) 
                + ISNULL([emp_m9], 0) 
                + ISNULL([emp_m10], 0) 
                + ISNULL([emp_m11], 0) 
                + ISNULL([emp_m12], 0)
            AS [emp_total]
        FROM [EMPCORE].[ca_edd].[vi_ca_edd_employment]
        INNER JOIN [EMPCORE].[ca_edd].[ownership]
            ON [vi_ca_edd_employment].[ownership_id] = [ownership].[ownership_id]
        WHERE [year] = @year
    ) AS [tt]
    WHERE
        [emp_valid] > 0
        AND [emp_total] > 0
        AND [ownership_title] IN (
            'Federal Government',
            'Local Government',
            'Private',
            'State Government'
        )
    GROUP BY [ownership_title], [industry_code]
END
ELSE IF @year BETWEEN 2010 AND 2013
BEGIN
    INSERT INTO [#edd]
    SELECT
        [ownership_title],
        ISNULL([industry_code], '99') AS [industry_code],
        SUM([jobs]) AS [jobs]
    FROM (
        SELECT
            CASE
                WHEN [ownership].[description] = 'Local government' THEN 'Local Government'
                WHEN [ownership].[description] = 'Federal government' THEN 'Federal Government'
                WHEN [ownership].[description] = 'Private sector' THEN 'Private'
                WHEN [ownership].[description] = 'State government' THEN 'State Government'
                ELSE NULL  -- filters out "Unknown" ownership records
            END AS [ownership_title],
            CASE
                WHEN LEFT([code], 2) IN ('31','32','33') THEN '31-33'
                WHEN LEFT([code], 2) IN ('44','45') THEN '44-45'
                WHEN LEFT([code], 2) IN ('48','49') THEN '48-49'
                -- there are records in 2011-2012 tagged as "Self Employed" with [code] = '72'
                -- there are records in all years with [code] = '999999' as a NULL placeholder
                WHEN [code] = '72' OR LEFT([code], 2) = '99' THEN NULL
                WHEN LEFT([code], 2) = '72' THEN LEFT([code], 3)
                -- NULL records are mapped to NULL despite falling into this ELSE condition
                -- Keep these records for total EDD jobs xref even if industry code is NULL
                ELSE LEFT([code], 2)
            END AS [industry_code],
            [employment] * ISNULL([headquarters].[share], 1) AS [jobs]
        FROM [EMPCORE].[ca_edd].[businesses]
        LEFT OUTER JOIN [EMPCORE].[ca_edd].[naics]
            ON [businesses].[naics_id] = [naics].[naics_id]
        LEFT JOIN [EMPCORE].[ca_edd].[headquarters]
            ON [businesses].[year] = [headquarters].[year]
            AND [businesses].[emp_id] = [headquarters].[emp_id]
        INNER JOIN (
            SELECT [year], [emp_id], [employment]
            FROM [EMPCORE].[ca_edd].[employment]
            WHERE 
                [month_id] = 14  -- adjusted employment
                AND [employment] > 0
                AND [year] = @year
        ) AS [employment]
            ON [businesses].[year] = [employment].[year]
            AND [businesses].[emp_id] = [employment].[emp_id]
        INNER JOIN [EMPCORE].[ca_edd].[ownership]
            ON [businesses].[ownership_id] = [ownership].[ownership_id]
        -- In 2010 there are 95k "Self Employed" records with [code] = NULL
        -- Subsequent years assign codes to these records
        -- They are removed here to avoid an enormous "99" code category
        -- See https://github.com/SANDAG/BLS/issues/58#issuecomment-5246348671
        WHERE ([dba] != 'Self Employed' AND [code] IS NOT NULL)
    ) AS [tt]
    WHERE
        [jobs] > 0
        AND [ownership_title] IN (
            'Federal Government',
            'Local Government',
            'Private',
            'State Government'
        )
    GROUP BY [ownership_title], [industry_code]
END
ELSE IF @year BETWEEN 2014 AND 2016
BEGIN
    INSERT INTO [#edd]
    SELECT
        [ownership_title],
        ISNULL([industry_code], '99') AS [industry_code],
        SUM([jobs]) AS [jobs]
    FROM (
        SELECT
            CASE
                WHEN [ownership].[description] = 'Local government' THEN 'Local Government'
                WHEN [ownership].[description] = 'Federal government' THEN 'Federal Government'
                WHEN [ownership].[description] = 'Private sector' THEN 'Private'
                WHEN [ownership].[description] = 'State government' THEN 'State Government'
                ELSE NULL  -- filters out "Unknown" ownership records
            END AS [ownership_title],
            CASE
                WHEN LEFT([code], 2) IN ('31','32','33') THEN '31-33'
                WHEN LEFT([code], 2) IN ('44','45') THEN '44-45'
                WHEN LEFT([code], 2) IN ('48','49') THEN '48-49'
                -- there are records in 2011-2012 tagged as "Self Employed" with [code] = '72'
                -- there are records in all years with [code] = '999999' as a NULL placeholder
                WHEN [code] = '72' OR LEFT([code], 2) = '99' THEN NULL
                WHEN LEFT([code], 2) = '72' THEN LEFT([code], 3)
                -- NULL records are mapped to NULL despite falling into this ELSE condition
                -- Keep these records for total EDD jobs xref even if industry code is NULL
                ELSE LEFT([code], 2)
            END AS [industry_code],
            [employment] * ISNULL([headquarters].[share], 1) AS [jobs]
        FROM [EMPCORE].[ca_edd].[businesses]
        LEFT OUTER JOIN [EMPCORE].[ca_edd].[naics]
            ON [businesses].[naics_id] = [naics].[naics_id]
        LEFT JOIN [EMPCORE].[ca_edd].[headquarters]
            ON [businesses].[year] = [headquarters].[year]
            AND [businesses].[emp_id] = [headquarters].[emp_id]
        INNER JOIN (
            SELECT
                [year],
                [emp_id],
                -- 15, 16, 17 are months from [employment] table where data was
                -- stored in [emp1], [emp2], [emp3] but actual month unknown
                -- check [EMPCORE].[ca_edd].[month] for more detail
                1.0 * ((ISNULL([15], 0) + ISNULL([16], 0) + ISNULL([17], 0)) 
                    /
                    (CASE WHEN [15] IS NOT NULL THEN 1 ELSE 0 END 
                        + CASE WHEN [16] IS NOT NULL THEN 1 ELSE 0 END 
                        + CASE WHEN [17] IS NOT NULL THEN 1 ELSE 0 END
                    ))
                AS [employment]
            FROM [EMPCORE].[ca_edd].[employment]
            PIVOT(SUM([employment]) FOR [month_id] IN ([15], [16], [17])) AS [pivot]
            WHERE
                [year] = @year AND
                ([15] IS NOT NULL OR [16] IS NOT NULL OR [17] IS NOT NULL)
        ) AS [employment]
            ON [businesses].[year] = [employment].[year]
            AND [businesses].[emp_id] = [employment].[emp_id]
        INNER JOIN [EMPCORE].[ca_edd].[ownership]
            ON [businesses].[ownership_id] = [ownership].[ownership_id]
    ) AS [tt]
    WHERE
        [jobs] > 0
        AND [ownership_title] IN (
            'Federal Government',
            'Local Government',
            'Private',
            'State Government'
        )
    GROUP BY [ownership_title], [industry_code]
END


-- Send error message if no data exists --------------------------------------
IF NOT EXISTS (
    SELECT TOP (1) * FROM [#edd]
)
SELECT @msg AS [msg]
ELSE
BEGIN
    -- Return EDD data by naics sector with 0s/NULLs filled in ---------------
    SELECT
        [#tt_shell].[ownership_title],
        [#tt_shell].[naics3],
        [#tt_shell].[naics_sector],
        [#tt_shell].[supersector],
        [#tt_shell].[domain],
        -- Fill in 0-category jobs with default value of 1 divided by the # of records
        -- To ensure scaling to match suppressed BLS QCEW values does not fail
        CASE
            WHEN [jobs] = 0 OR [jobs] IS NULL THEN 1.0/(SELECT COUNT(*) FROM [#tt_shell])
            ELSE [jobs]
        END AS [jobs]
    FROM [#tt_shell]
    LEFT OUTER JOIN [#edd]
        ON [#tt_shell].[ownership_title] = [#edd].[ownership_title]
        AND (
            ([#tt_shell].[naics_sector] != '72' AND [#tt_shell].[naics_sector] = [#edd].[industry_code])
            OR ([#tt_shell].[naics_sector] = '72' AND [#tt_shell].[naics3] = [#edd].[industry_code])
        )
    ORDER BY
        [#tt_shell].[ownership_title],
        [#tt_shell].[naics_sector],
        [#tt_shell].[naics3]
END

DROP TABLE IF EXISTS [#tt_shell];
DROP TABLE IF EXISTS [#edd];