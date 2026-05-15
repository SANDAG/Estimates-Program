-- Initialize parameters -----------------------------------------------------
DECLARE @year INTEGER = :year;
DECLARE @series INTEGER = :series;


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
    AND [series] = @series