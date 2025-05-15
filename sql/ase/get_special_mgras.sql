-- Initialize parameters -----------------------------------------------------
DECLARE @year integer = :year;
DECLARE @mgra_version nvarchar(10) = :mgra_version;


-- Get special MGRAs ---------------------------------------------------------
SELECT
    CASE WHEN @mgra_version = 'mgra15' THEN [mgra15] ELSE NULL END AS [mgra],
    [pop_type],
    [sex],
    [min_age],
    [max_age]
FROM [inputs].[special_mgras]
WHERE @year BETWEEN [start_year] AND [end_year]