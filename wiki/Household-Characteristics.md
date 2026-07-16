# Inputs

| Input                                                     | Module Source                   | Usage                                                                |
|-----------------------------------------------------------|---------------------------------|----------------------------------------------------------------------| 
| MGRA Geography (`[inputs].[mgra]`)                        | Startup                         | Used to merge MGRA-level values with census tract rates              |
| MGRA Cross References                                     | Demographic Warehouse           | Provides cross reference from MGRAs to census tracts                 |
| Households in each MGRA (`[outputs].[hh]`)                | Housing and Households          | Used to generate household characteristics                           |
| Household population in each MGRA (`[outputs].[hhp]`)     | Housing and Households          | Used to balance household size implied household population          |
| Household population 18+ in each MGRA (`[outputs].[ase]`) | Population by Age Sex Ethnicity | Used to balance household workers implied worker population          |
| Census tract household income distribution                | External (ACS)                  | Apply to households to create households by income categories        |
| Census tract households by size distribution              | External (ACS)                  | Apply to households to create households by size categories          |
| Census tract households by workers distribution           | External (ACS)                  | Apply to households to create households by workers categories       |

## MGRA Geography (`[inputs].[mgra]`)
See [Startup](https://github.com/SANDAG/Estimates-Program/wiki/Startup).

## MGRA Cross References
See private SANDAG repository [Demographic Warehouse](https://github.com/SANDAG/demographic-warehouse).

## Households in each MGRA (`[outputs].[hh]`)
See [Housing and Households](https://github.com/SANDAG/Estimates-Program/wiki/Housing-and-Households).

## Household population in each MGRA (`[outputs].[hhp]`)
See [Housing and Households](https://github.com/SANDAG/Estimates-Program/wiki/Housing-and-Households).

## Household population 18+ in each MGRA (`[outputs].[ase]`)
See [Population by Age Sex Ethnicity](https://github.com/SANDAG/Estimates-Program/wiki/Population-by-Age-Sex-Ethnicity).

## Census tract household income distribution

The household income distribution is derived from American Community Survey (ACS) table [B19001 | HOUSEHOLD INCOME IN THE PAST 12 MONTHS](https://data.census.gov/table/ACSDT5Y2020.B19001?q=B19001). The table provides households by household income. Dividing each category by total households provides census tract household income distributions. The year of the ACS table provides the inflation-adjusted dollars year.

```math
\forall t \in \text{San Diego Tracts}, \forall hhi \in \text{Household Income Category}; \text{Distribution}_{t,hhi} = \frac{\text{Households in Income Category}_{t,hhi}}{\text{Households}_t}
```

To avoid division by zero errors, the household income distribution is set to `NULL` if the households are zero within a census tract. This can lead to conflict between ACS data and SANDAG's Land Use and Dwelling Unit Inventory (LUDU). Within a census tract, the ACS may have no housing units, no households, and a `NULL` household income distribution while SANDAG's LUDU contains housing units. In this situation, the regional household income distribution is used.

```math
\forall hhi \in \text{Household Income Category}; \text{Regional Household Income Distribution}_{hhi} = \frac{\sum \text{Households in Income Category}_{hhi}}{\sum \text{Households}}
```

## Census tract households by size distribution

The households by size distribution is derived from ACS table [B11016 | HOUSEHOLD TYPE BY HOUSEHOLD SIZE](https://data.census.gov/table/ACSDT5Y2020.B11016?q=B11016). The table provides households by household size category. Dividing each category by total households provides census tract households by size distributions.

```math
\forall t \in \text{San Diego Tracts}, \forall hhs \in \text{Household Size Category}; \text{Distribution}_{t,hhs} = \frac{\text{Households in Size Category}_{t,hhs}}{\text{Households}_t}
```

To avoid division by zero errors, the households by size distribution is set to `NULL` if the households are zero within a census tract. This can lead to conflict between ACS data and SANDAG's LUDU. Within a census tract, the ACS may have no housing units, no households, and a `NULL` households by size distribution while SANDAG's LUDU contains housing units. In this situation, the regional households by size distribution is used.

```math
\forall hhs \in \text{Household Size Category}; \text{Regional Household Size Distribution}_{hhs} = \frac{\sum \text{Households in Size Category}_{hhs}}{\sum \text{Households}}
```

## Census tract households by workers distribution

The households by workers distribution is derived from ACS table [B08202 | HOUSEHOLD SIZE BY NUMBER OF WORKERS IN HOUSEHOLD](https://data.census.gov/table/ACSDT5Y2020.B08202?q=B08202). The table provides households by number of workers category. Dividing each category by total households provides census tract households by workers distributions.

```math
\forall t \in \text{San Diego Tracts}, \forall hhs \in \text{Household Worker Category}; \text{Distribution}_{t,hhs} = \frac{\text{Households in Worker Category}_{t,hhs}}{\text{Households}_t}
```

To avoid division by zero errors, the households by workers distribution is set to `NULL` if the households are zero within a census tract. This can lead to conflict between ACS data and SANDAG's LUDU. Within a census tract, the ACS may have no housing units, no households, and a `NULL` households by workers distribution while SANDAG's LUDU contains housing units. In this situation, the regional households by workers distribution is used.

```math
\forall hhs \in \text{Household Worker Category}; \text{Regional Household Worker Distribution}_{hhs} = \frac{\sum \text{Households in Worker Category}_{hhs}}{\sum \text{Households}}
```

# Outputs (`[outputs].[hh_characteristics]`)

Each row of this table contains the following information:

| Column             | Description                                                      |
|--------------------|------------------------------------------------------------------|
| `[run_id]`         | Estimates run identifier                                         |
| `[year]`           | Year within estimates run                                        |
| `[mgra]`           | The Master Geographic Reference Area (MGRA)                      |
| `[metric]`         | Household characteristic category                                |
| `[value]`          | Number of households                                             |

## Households by income category in each MGRA
MGRA households by income category. Calculated by applying census tract distributions to households.

## Households by size category in each MGRA
MGRA households by size category. Calculated by applying census tract distributions to households. Adjusts size categories within MGRAs such that the implied household population range (min-max) contains the actual MGRA household population value.

For example, within a MGRA with 10 households of size one, 10 households of size two, ..., 10 households of size 7+, the minimum amount of household population would be 1x10 + 2x20 + ... + 7x10 = 280. The maximum amount of household population, assuming the 7+ category all average 11 people (see [issue #112](https://github.com/SANDAG/Estimates-Program/issues/112)), would be 1x10 + 2x20 + ... + 11x10 = 320. The actual amount of household population in this MGRA must be between these two values. If it is not, the households in size categories are adjusted until the condition is satisfied.

## Households by workers category in each MGRA
MGRA households by workers category. Calculated by applying census tract distributions to households. Adjusts workers categories within MGRAs such that the implied minimum worker population does not exceed the MGRA household population of persons aged 18+. Then adjusts households by workers categories such that they respect the households by size categories in each MGRA.

For example, within a MGRA with 10 households with 0 workers, 10 households with 1 workers, 10 households with 2 workers, 10 households with 3+ workers, the minimum implied household population of persons aged 18+ is 0x10 + 1x10 + 2x10 + 3x10 = 60. If the MGRA household population of persons aged 18+ is less than 60 then the households by workers categories are adjusted until the condition is satisfied. This is a soft constraint as we do not estimate the true number of workers in each MGRA.

The process then moves onto adjusting households by workers categories such that they respect the households by size categories in each MGRA. Again, within a MGRA with 10 households with 0 workers, 10 households with 1 workers, 10 households with 2 workers, 10 households with 3+ workers, this implies there are at least 10 households of size 2+ and 10 household of size 3+. The 0 and 1 worker households can be of any size 1+ and do not violate any households by size category conditions as the total households within each MGRA is respected. If the MGRA households by size categories aggregated to 2+ and 3+ are less than 10 then the households by workers categories are adjusted until the condition is satisfied.