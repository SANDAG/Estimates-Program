-- Initialize parameters -----------------------------------------------------
DECLARE @year integer = :year; 

SELECT 
    [year],
    [industry_code],
    SUM([annual_avg_emplvl]) AS jobs
FROM [socioec_data].[bls].[qcew_by_area_annual]
INNER JOIN [socioec_data].[bls].[industry_code]
    ON [qcew_by_area_annual].[naics_id] = [industry_code].[naics_id]
WHERE [area_fips] = '06073'
    AND [year] = @year
    AND [industry_code] IN ('11', '21', '22', '23', '31-33', '42', '44-45', '48-49', '51', '52', '53', '54', '55', '56', '61', '62', '71', '721', '722', '81', '92')
GROUP BY [year], [industry_code]
