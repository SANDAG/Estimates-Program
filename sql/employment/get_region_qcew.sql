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
SELECT
    [fn_get_sandag_employment].[ownership_title],
    [fn_get_sandag_employment].[industry_code],
	ROUND(SUM([month1_emplvl] + [month2_emplvl] + [month3_emplvl])/12.0, 0) AS [jobs]
--INTO [#qcew_result_set]
FROM [socioec_data].[bls].[qcew_by_area_quarterly]
INNER JOIN [socioec_data].[bls].[industry_code]
	ON [qcew_by_area_quarterly].[naics_id] = [industry_code].[naics_id]
INNER JOIN [socioec_data].[bls].[ownership_titles]
	ON [qcew_by_area_quarterly].[own_code] = [ownership_titles].[ownership_code]
CROSS APPLY [socioec_data].[bls].[fn_get_sandag_employment]([ownership_title], [industry_code])
WHERE
    [area_fips] = '06073'
    AND [year] = @year
    AND [fn_get_sandag_employment].[ownership_title] IS NOT NULL
    AND [fn_get_sandag_employment].[industry_code] IS NOT NULL
    -- Remove the "Private" ownership only categories
    -- These are published directly in the annual QCEW
    AND [fn_get_sandag_employment].[ownership_title] != 'Private'
GROUP BY
    [fn_get_sandag_employment].[ownership_title],
    [fn_get_sandag_employment].[industry_code]

    UNION ALL

-- Calculate directly derived employment categories using annual data --------
SELECT
    [fn_get_sandag_employment].[ownership_title],
    [fn_get_sandag_employment].[industry_code],
	ROUND(SUM([annual_avg_emplvl]), 0) AS [jobs]
FROM [socioec_data].[bls].[qcew_by_area_annual]
INNER JOIN [socioec_data].[bls].[industry_code]
	ON [qcew_by_area_annual].[naics_id] = [industry_code].[naics_id]
INNER JOIN [socioec_data].[bls].[ownership_titles]
	ON [qcew_by_area_annual].[own_code] = [ownership_titles].[ownership_code]
CROSS APPLY [socioec_data].[bls].[fn_get_sandag_employment]([ownership_title], [industry_code])
WHERE
    [area_fips] = '06073'
    AND [year] = @year
    AND [fn_get_sandag_employment].[ownership_title] IS NOT NULL
    AND [fn_get_sandag_employment].[industry_code] IS NOT NULL
    -- "Private" ownership only categories
    -- Are published directly in the annual QCEW
    AND [fn_get_sandag_employment].[ownership_title] = 'Private'
GROUP BY
    [fn_get_sandag_employment].[ownership_title],
    [fn_get_sandag_employment].[industry_code]

ORDER BY
    [ownership_title],
    [industry_code]