-- Initialize parameters -----------------------------------------------------
DECLARE @mgra_version nvarchar(10) = :mgra_version;


SELECT
    [from_zone] AS [block],
    CAST([to_zone] AS INT) AS [mgra],
    [allocation_pct] 
FROM [GeoAnalyst].[geography].[fn_xref_zones](
    CASE WHEN @mgra_version = 'mgra15' THEN 18 ELSE NULL END
    )