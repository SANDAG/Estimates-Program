-- Initialize parameters -----------------------------------------------------
DECLARE @year integer = :year;
DECLARE @mgra_version integer = :mgra_version;


-- Get special MGRAs ---------------------------------------------------------
SELECT
    [mgra],
    [pop_type],
    [sex],
    [min_age],
    [max_age]
FROM [inputs].[special_mgras]
WHERE
    @year BETWEEN [start_year] AND [end_year]
    AND [series] = @mgra_version