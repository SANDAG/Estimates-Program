This module contains shared functionality between all other modules, which consists of two different rounding/integerization functions and a helper function for dealing with un-released years of 5-year American Community Survey (ACS) datasets.

## One-dimensional rounding/integerization (`integerize_1d()`)

### Input data

The input to this function is any one-dimensional list of data, an optional integer control value, an optional methodology (default value `weighted_random`), and an optional random number generator (type: `numpy.random.Generator`, typically created by calling `numpy.random.default_rng(seed=42)`. Additionally, the following conditions must hold:
* All numeric input data must be non-negative
* If no optional integer control value is provided, then the one-dimensional list of data must exactly sum to a non-negative integer value
* The optional methodology must be one of `largest`, `smallest`, `largest_difference`, or `weighted_random`
* The optional random number generator is used if and only if the chosen methodology is `weighted_random`

### Output data

The output of this function is one-dimensional data of the same shape as the input list of data, such that the following conditions all hold:
* The sum of the output data exactly matches either (1) the optional control value or (2) the sum of the input data assuming it was a non-negative integer value
* All output data consists of only non-negative integer values
* The output is deterministic with respect to the input data. In other words, assuming input data is not changed, the output data will always be exactly the same

### Algorithm

There are four different methodologies, used in `integerize_1d()`. Each methodology uses the exact same workflow, but differ in the metric used to resolve rounding error:
1. Validate input data. In other words, ensure that (1) valid rounding error methodology was chosen, (2) a seeded random generator was input, if necessary for the chosen rounding error methodology, and (3) all input data is of the correct type and contains no negative values
2. Get the control value. If not input, then the control value is the sum of the original input data
3. Control input data to the control value. The input data is simply scaled by a percent change in order to exactly equal the control. Note that data at this point is still decimal
4. Round data upwards. In theory, rounding up helps to preserve the diversity of data by allowing tiny values to still remain present, as opposed to being rounded down to nothingness. 
5. Resolve rounding error using one of the four methodologies (`largest`, `smallest`, `largest_difference`, or `weighted_random`)

For each methodology, start by computing the amount of rounding error (aka `e`) by subtracting the sum of the post-rounding values and the control value. The following facts always hold true for `e`:
* `e` is a non-negative integer. Since we always round up, each data point can result in deviations in the range of `[0, 1)`. The sum of non-negative values is also non-negative. Additionally, since the pre/post-rounding data both sum to a non-negative integer, the sum of the difference must also be a non-negative integer
* `e` is less than or equal to the number of non-zero data points in the post-rounding data. If a data point is zero, rounding up does nothing. Thus, if we consider the number of non-zero data points (`n`), each each non-zero data point can result in deviations in the range of `[0, 1)`, then the maximum deviation is in the range of `[0*n, 1*n)`. In other words, the maximum possible deviation of `n` is guaranteed to be less than `e`

Now with `e` in hand, we choose a set of data points to decrease by one in order to resolve rounding error. This is where the differing methodologies comes into play:
1. 'largest': Choose the `e` largest data points and decrease them by one
2. 'smallest': Choose the `e` smallest non-zero data points and decrease them by one
3. 'largest_difference': Compute the difference between pre/post-rounding values. Choose the `e` data points which had the largest difference between pre and post-rounding values
4. 'weighted_random': The default methodology. Compute the difference between pre/post-rounding values. Using a seeded random generator, choose `e` data points without replacement while using the difference as weights. Or in other words, the larger the difference between pre and post-rounding values, the more likely the data point is to be chosen

In case of ties, all methodologies break ties by taking either the first occurrence (`smallest`) or the last occurrence (`largest` and `largest_difference`) . The `weighted_random` methodology will never have ties as it uses random sampling

### Why is `weighted_random` the default methodology?

`weighted_random` is the default methodology simply because all other methodologies, i.e. `largest`, `smallest`, and `largest_difference` all suffer from the same ailment that causes widespread data shifts. Specifically, these methodologies consistently choose the exact same categories to adjust, which causes extremely visible shifts once data has been aggregated. Since these data shifts are easiest to discuss with respect to population by age/sex/ethnicity (ASE), I'll be using ASE language here. Just keep in mind that this effect happens with all variables, not just with ASE.

ASE data is created by applying Census Tract level ASE distributions to MGRA population counts, after which the data is passed into the 1D integerizer. In ASE data, there are (`20` age groups x `2` sexes x `7` race/ethnicity categories =) `280` total categories, which further implies that each category has on average (`1` / `280` =) `.36%` of the population. When you consider further that the race/ethnicity category is highly skewed towards Hispanic and NH-White, the other race/ethnicity categories are even smaller. For example, for [Census Tract `169.02` in 2020](https://data.census.gov/table/ACSDT5Y2020.B03002?q=B03002&g=1400000US06073016902), which roughly corresponds to Barona, an area with higher than average NH-AIAN (American Indian and Alaska Native) population, the NH-AIAN race/ethnicity category has around `14%` of the population, which means each of the `80` age/sex categories have on average `.17%` of the population.

Let's hypothetically use the `smallest` methodology. Let's assume an MGRA in Census Tract `169.02` has a population of `100` people. When the Census Tract rate is applied to the MGRA, naturally, the NH-AIAN always be among the smallest ASE categories. Thus, when the 1D integerizer chooses the smallest categories to adjust for rounding error, the NH-AIAN category will consistently be chosen. For this MGRA, it doesn't really matter since a `-1` is well within rounding error. But if Census Tract `169.02` has 50 MGRAs that all decide independently to decrease NH-AIAN, now this Census Tract has a `-50` change in NH-AIAN, which is a change that obviously shows up.

If instead, we used the `largest_difference` methodology, a similar issue would occur. Because NH-AIAN is consistently the smallest ASE category across all Census Tracts, they will also consistently need to be rounded up the most, which means that they will consistently be decreased. If instead, we used the `largest` methodology, similar but opposite problem would occur. Now, instead of consistently choosing NH-AIAN categories, the 1D integerizer would now consistently choose Hispanic or NH-White, which means we would size large unexpected shifts in those categories instead of in NH-AIAN.

Additionally, keep in mind that this ASE balancing is all a zero-sum game, that a negative change in NH-AIAN in some MGRAs must be reflected by the opposite change in other MGRAs. Then, the following table shows these changes:
| Methodology | Primary Change | Secondary Change |
| --- | --- | --- |
| `smallest` | The smallest categories (typically NH-AIAN) will consistently be decreased across all MGRAs in the county | A decrease in NH-AIAN across all MGRAs in the county forces a significant amount of NH-AIAN into MGRAs where NH-AIAN is not the smallest category |
| `largest_difference` | The categories that were rounded up the most (typically NH-AIAN) will consistently be decreased across all MGRAs in the county | A decrease in NH-AIAN across all MGRAs in the county heavily concentrates NH-AIAN into MGRAs where NH-AIAN is not the category with the most rounding up |
| `largest` | The largest categories (typically Hispanic or NH-White) will consistently be decrease across all MGRAs in the county | A decrease in Hispanic/NH-White across all MGRAs in the county forces a significant amount of Hispanic/NH-White into MGRAs where Hispanic/NH-White is not the largest category |

None of the above changes are acceptable, as they result in ASE data can deviate from the ACS beyond the listed margins of errors. Therefore, the `weighted_random` methodology is used instead. The main difference of course being that the `weighted_random` methodology does not consistently choose the exact same ASE categories, only that it mostly does so.

In other words, in some Census Tracts, `smallest` and `largest_difference` will always choose NH-AIAN as the smallest category. This means that in Census Tracts which should have a tiny but non-zero amount of NH-AIAN, they are instead set to zero when adjusting for rounding error. `weighted_random` on the other hand, as it is a probabilistic method, will usually but not always choose NH-AIAN as the category, which means that some MGRAs keep their NH-AIAN and the Census Tract ends up with a tiny but non-zero amount of NH-AIAN, as it should be. So, when using `weighted_random`, every Census Tract should have a distribution which better matches the ACS, and therefore when aggregated should better match the regional controls, which means less re-distribution needs to be done.

## Two-dimensional rounding/integerization (`integerize_2d()`)

The input to this function is any two-dimensional array of data, a one-dimensional list of row controls, a one-dimensional list of column controls, an optional "condition" parameter, and an optional list of integer "nearest_neighbors" to use for the "Nearest Neighbor" allocation strategy.

After some basic input data validation, column data is rounded preserving column control totals using the `integerize_1d` function, then rounding error is corrected to match the row controls.

Preserving column control totals while correcting rounding error for row controls is done using an integer reallocation process. Rows with positive deviations have their smallest non-zero column decreased in increments of -1. Rows with negative deviations have their largest non-zero column that was previously decreased for rows with positive deviations increased in increments of +1. This is repeated until all rows are either equal to or less than their row control total, depending on the "condition" parameter.

For rows with negative deviations, is not always possible to find non-zero columns that were decreased for rows with positive deviations. Subsequently, the non-zero requirement is relaxed to a "Nearest Neighbors" strategy, a more flexible alternative. Under this strategy, zero-valued columns with non-zero columns in a "neighborhood" around them are eligible for increase. Multiple values for the "neighborhood" are explored as each fail, provided by the "nearest_neighbors" input parameter. If all "neighborhood" values fail, the non-zero requirement is completely abandoned and all columns that were decreased for rows with positive deviations are allowed. As the "Nearest Neighbors" strategy looks in a neighborhood of nearby columns, column ordering in the array is a critical component to the strategy.

Both the "Nearest Neighbors" and abandonment of the non-zero requirement can lead to values being increased in columns that are implausible for the row. For example, in the "Population by Age Sex Ethnicity" module, a row defined as a MGRA containing male-only adult persons may have female or juvenile values increased if the function cannot reallocate to non-zero columns. This necessitates the use of an additional "balancer" in the "Population by Age Sex Ethnicity" module for special MGRAs.

## Dealing with un-released ACS 5-year Detailed Tables (`read_sql_query_acs()`)

This function is a wrapper for `pd.read_sql_query` with an extension built in that handles requests for ACS 5-year Detailed Tables data that are currently not released. Essentially, all SQL scripts dealing with ACS data have an `IF/ELSE` statement at the top which checks for the existence of data. If the data for the specified table/year could not be found, then an error message is returned. This function detects the presence of the error message and re-runs the query using the previous year instead. 

### A Note on ACS 5-year Detailed Tables

The Estimates Program uses a large number of ACS 5-year Detailed Tables, typically by combining two or more tables together in order to get the distribution of some variable within a census tract. For example, to compute the distribution of households by household income for a census tract, the households by household income table is combined with the total households table. This provides highly granular and specific data for each estimate year of the Estimates Program.

The year of the estimate determines the ACS 5-year release to use. An estimate made for 2020 will use the 2016-2020 ACS 5-year, an estimate made for 2021 will use the 2017-2021 ACS 5-year, and so on and so forth. SANDAG's Estimates Program and the Census Bureau have different release schedules. SANDAG typically releases estimates data at a roughly six-month time lag from year end, while the Census Bureau typically releases ACS 5-year Detailed Tables at a roughly one-year time lag from year end ([see the ACS data release schedule](https://www.census.gov/programs-surveys/acs/news/data-releases.html)).

For example, in the summer of 2025, SANDAG aims to release estimates years up to 2024, but the Census Bureau plans to release the ACS 5-year 2020-2024 Detailed Tables in December 2025. With no alternative data source, SANDAG's Estimates Program reverts to using the ACS 5-year 2019-2023 release for estimate year 2024.