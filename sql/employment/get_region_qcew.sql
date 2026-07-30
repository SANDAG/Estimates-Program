/*
    This SQL query calculates annual employment averages for SANDAG employment
    categories from the BLS QCEW for a given year. SANDAG employment categories
    are built from a combination of ownership and 2-digit industry codes,
    excepting for the exclusion of unclassifed NAICS 99 and the split of NAICS 72
    into 721 and 722. SANDAG employment categories are as follows:

        Total Covered - 61,62,71,721,722
        Private - 11,21,22,23,31-33,42,44-45,48-49,51,52,53,54,55,56,81
        Federal/State/Local Government - see Private industries above + NAICS 92

    For SANDAG employment categories not directly derived from published
    BLS QCEW annual averages we use summations of monthly employment totals
    published quarterly to aggregate into SANDAG employment categories and perform
    averaging and integerization at the final reporting step per guidance received
    from BLS QCEW staff. See https://github.com/SANDAG/BLS/issues/55.
    There are all the SANDAG employment categories that combine ownership
    categories.

        Total Covered - 61,62,71,721,722
        Federal/State/Local Government - see Private industries above + NAICS 92

    For SANDAG employment categories that are directly derived from published BLS
    QCEW annual averages we use those numbers directly as they are calculated by
    the BLS using unreleased microdata that is more accurate than the rounded
    quarterly monthly data. These are all the "Private" ownership only categories.

        Private - 11,21,22,23,31-33,42,44-45,48-49,51,52,53,54,55,56,81

    This is able to be done for years 2022-2025 as no suppression exists at the 
    aggregation levels required to create SANDAG employment categories. Data prior
    to 2022 requires controlling at higher aggregation levels to fill in 
    gaps created by data suppression.
*/

SET NOCOUNT ON;
-- Initialize parameters and return table ------------------------------------
-- Set year of BLS QCEW data to create SANDAG employment categories
DECLARE @year INTEGER = :year;

-- Data suppression limits this query to 2022-2025 only
IF @year < 2022 OR @year > 2025 THROW 5000, 'Data suppression prevents calculation prior to 2022', 1;

-- Drop temporary table holding final result set
DROP TABLE IF EXISTS [#qcew_result_set];


-- Calculate custom SANDAG employment categories using quarterly data --------
WITH [qtr_data] AS (
    SELECT
        CASE
            WHEN [industry_code] IN (
                '61',
                '62',
                '71',
                '721',
                '722'
            ) THEN 'Total Covered'
            ELSE [ownership_title]
        END AS [ownership_title],
        CASE
            WHEN [ownership_title] = 'Private' AND [industry_code] IN (
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
            ) THEN [industry_code]
            WHEN [industry_code] IN (
                '61',
                '62',
                '71',
                '721',
                '722'
            ) THEN [industry_code]
            WHEN [ownership_title] = 'Federal Government' THEN NULL
            WHEN [ownership_title] = 'State Government' THEN NULL
            WHEN [ownership_title] = 'Local Government' THEN NULL
        END AS [industry_code],
	    [month1_emplvl] + [month2_emplvl] + [month3_emplvl] AS [jobs]
    FROM [socioec_data].[bls].[qcew_by_area_quarterly]
    INNER JOIN [socioec_data].[bls].[industry_code]
	    ON [qcew_by_area_quarterly].[naics_id] = [industry_code].[naics_id]
    INNER JOIN [socioec_data].[bls].[ownership_titles]
	    ON [qcew_by_area_quarterly].[own_code] = [ownership_titles].[ownership_code]
    WHERE
        [area_fips] = '06073'
        AND [year] = @year
        -- Restrict to Private, Federal, State, Local ownership
        AND [ownership_title] IN (
            'Private',
            'Federal Government',
            'State Government',
            'Local Government'
        )
        -- Restrict to two-digit NAICS codes
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
            '61',
            '62',
            '71',
            '721',
            '722',
            '81',
            '92'
        )
)
SELECT
    [ownership_title],
    [industry_code],
    -- Averaging and rounding occurs at final reporting step
    -- See https://github.com/SANDAG/BLS/issues/55
    ROUND(SUM([jobs])/12.0, 0) AS [jobs]
INTO [#qcew_result_set]
FROM [qtr_data]
GROUP BY
    [ownership_title],
    [industry_code]
-- Remove the "Private" ownership only categories
-- These are published directly in the annual QCEW
HAVING [ownership_title] != 'Private'
ORDER BY
    [ownership_title],
    [industry_code];


-- Calculate directly derived employment categories using annual data --------
WITH [annual_data] AS (
    SELECT
        CASE
            WHEN [industry_code] IN (
                '61',
                '62',
                '71',
                '721',
                '722'
            ) THEN 'Total Covered'
            ELSE [ownership_title]
        END AS [ownership_title],
        CASE
            WHEN [ownership_title] = 'Private' AND [industry_code] IN (
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
            ) THEN [industry_code]
            WHEN [industry_code] IN (
                '61',
                '62',
                '71',
                '721',
                '722'
            ) THEN [industry_code]
            WHEN [ownership_title] = 'Federal Government' THEN NULL
            WHEN [ownership_title] = 'State Government' THEN NULL
            WHEN [ownership_title] = 'Local Government' THEN NULL
        END AS [industry_code],
	    [annual_avg_emplvl] AS [jobs]
    FROM [socioec_data].[bls].[qcew_by_area_annual]
    INNER JOIN [socioec_data].[bls].[industry_code]
	    ON [qcew_by_area_annual].[naics_id] = [industry_code].[naics_id]
    INNER JOIN [socioec_data].[bls].[ownership_titles]
	    ON [qcew_by_area_annual].[own_code] = [ownership_titles].[ownership_code]
    WHERE
        [area_fips] = '06073'
        AND [year] = @year
        -- Restrict to Private, Federal, State, Local ownership
        AND [ownership_title] IN (
            'Private',
            'Federal Government',
            'State Government',
            'Local Government'
        )
        -- Restrict to two-digit NAICS codes
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
            '61',
            '62',
            '71',
            '721',
            '722',
            '81',
            '92'
        )
)
INSERT INTO [#qcew_result_set]
SELECT
    [ownership_title],
    [industry_code],
    -- Averaging and rounding occurs at final reporting step
    -- See https://github.com/SANDAG/BLS/issues/55
    ROUND(SUM([jobs]), 0) AS [jobs]
FROM [annual_data]
GROUP BY
    [ownership_title],
    [industry_code]
HAVING [ownership_title] = 'Private'
ORDER BY
    [ownership_title],
    [industry_code]


-- Return combined result set
SELECT
    @year AS [year],
    [ownership_title],
    [industry_code],
    [jobs]
FROM [#qcew_result_set]
ORDER BY
    [ownership_title],
    [industry_code]