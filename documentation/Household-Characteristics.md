# Household Characteristics Module

# Inputs

| Input                                                 | Module Source          | Usage                                                             |
|-------------------------------------------------------|------------------------|-------------------------------------------------------------------| 
| MGRA cross-reference (`[inputs].[mgra]`)              | Startup                | Used to merge MGRA-level values with census tract rates           |
| Households in each MGRA (`[outputs].[hh]`)            | Housing and Households | Used to generate household characteristics                        |
| Household population in each MGRA (`[outputs].[hhp]`) | Housing and Households | Used to balance household size implied household population       |
| Census tract household income distribution            | External (ACS)         | Apply to households to create households by income categories     |
| Census tract households by size distribution          | External (ACS)         | Apply to households to create households by size categories       |

## MGRA cross-reference (`[inputs].[mgra]`)
See [Startup](/documentation/Startup.md#mgra-geography-and-cross-reference-inputsmgra).

## Households in each MGRA (`[outputs].[hh]`)
See [Housing and Households](/documentation/Housing-and-Households.md#households-by-structure-type-in-each-mgra-outputshh).

## Household population in each MGRA (`[outputs].[hhp]`)
See [Population by Type](/documentation/Population-by-Type.md#household-population-in-each-mgra-outputshhp).

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

# Navigation

* [Home Page](README.md)
* [Startup](Startup.md)
* [Housing and Households](Housing-and-Households.md)
* [Population by Type](Population-by-Type.md)
* [Population by Age/Sex/Ethnicity](Population-by-Age-Sex-Ethnicity.md)
    * [Regional Age/Sex/Ethnicity Controls by Housing Type](ase/Regional-Age-Sex-Ethnicity-Controls-By-Housing-Type.md)
    * [Census Tract Age/Sex/Ethnicity Seed](ase/Census-Tract-Age-Sex-Ethnicity-Seed.md)
* Household Characteristics
* [Staging](Staging.md)
* [Utility](Utility.md)