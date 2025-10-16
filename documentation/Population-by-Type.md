# Population by Type Module

# Inputs

| Input                                      | Module Source          | Usage                                                                      |
|--------------------------------------------|------------------------|----------------------------------------------------------------------------| 
| MGRA cross-reference (`[inputs].[mgra]`)   | Startup                | Used to merge MGRA-level values with census tract rates and city controls  |
| Special MGRAs (`[inputs].[special_mgras]`) | Startup                | Identifies "Group Quarters - Institutional Correctional Facilities"        |
| Point geometry group quarters by type      | External (LUDU)        | Generate counts of group quarters by type within each MGRA                 |
| City total group quarters controls         | External (DOF)         | Apply to group quarters to match total group quarters by city              |
| Households in each MGRA (`[outputs].[hh]`) | Housing and Households | Used to generate household population                                      |
| Census tract average household size        | External (ACS)         | Apply to households to create household population                         |
| City household population controls         | External (DOF)         | Adjust household population to match household population by city          |

## MGRA cross-reference (`[inputs].[mgra]`)
See [Startup](/documentation/Startup.md#mgra-geography-and-cross-reference-inputsmgra).

## Special MGRAs (`[inputs].[special_mgras]`)
See [Startup](/documentation/Startup.md#special-mgras-inputsspecial_mgras).

## Point geometry group quarters by type
MGRA group quarters by type is aggregated from SANDAG's point geometry group quarters dataset to the MGRA-level. To ensure that group quarters by type is assigned to the correct MGRA, a spatial join is used to match the group quarters point geometries to MGRA polygons. The special MGRAs table (`[inputs].[special_mgras]`) is used to identify instances of "Group Quarters - Other" that should be mapped to "Group Quarters - Institutional Correctional Facilities".

## City total group quarters controls

City-level total group quarters controls are directly pulled from the [California Department of Finance (DOF) Estimates](https://dof.ca.gov/forecasting/demographics/estimates/). For years 2010-2019, data is pulled from the most recent E-8 product at the time. For years 2020+, data is pulled from the most recent E-5 product at the time.

## Households in each MGRA (`[outputs].[hh]`)
See [Housing and Households](/documentation/Housing-and-Households.md#households-by-structure-type-in-each-mgra-outputshh).

## Census tract average household size

Average household size is derived from two American Community Survey (ACS) tables, [B25032 | TENURE BY UNITS IN STRUCTURE](https://data.census.gov/table/ACSDT5Y2020.B25032?q=B25032), and [B09019 | HOUSEHOLD TYPE (INCLUDING LIVING ALONE) BY RELATIONSHIP](https://data.census.gov/table/ACSDT5Y2020.B09019?q=B09019). The first table provides households. The seconds table provides household population. Dividing the two provides census tract average household size.

```math
\forall t \in \text{San Diego Tracts}; \text{Household Size}_t = \frac{\text{Household Population}_t}{\text{Households}_t}
```

To avoid division by zero errors, the average household size is set to `NULL` if households are zero within a census tract. This can lead to conflict between ACS data and SANDAG's LUDU. Within a census tract, the ACS may have no housing units, no households, and a `NULL` average household size while SANDAG's LUDU contains housing units. In this situation, the regional average household size is used.

```math
\text{Regional Household Size} = \frac{\sum \text{Household Population}}{\sum \text{Households}}
```

## City household population controls

City-level household population controls are directly pulled from the [California Department of Finance (DOF) Estimates](https://dof.ca.gov/forecasting/demographics/estimates/). For years 2010-2019, data is pulled from the most recent E-8 product at the time. For years 2020+, data is pulled from the most recent E-5 product at the time.

# Outputs

## Population by housing type in each MGRA
MGRA population by housing type. Group quarters housing types calculated by aggregating group quarters points to MGRAs and controlling overall group quarters at the city-level to controls from the DOF. Household population calculated by taking MGRA households, applying census tract average household sizes, and controlling household population at the city-level to controls from the DOF.

### Group Quarters population by housing type in each MGRA (`[outputs].[gq]`)
Each row of this table contains the following information:

| Column             | Description                                                      |
|--------------------|------------------------------------------------------------------|
| `[run_id]`         | Estimates run identifier                                         |
| `[year]`           | Year within estimates run                                        |
| `[mgra]`           | The Master Geographic Reference Area (MGRA)                      |
| `[gq_type]`        | Group quarters housing type                                      |
| `[value]`          | Number of persons living in group quarters                       |

### Household population in each MGRA (`[outputs].[hhp]`)
Each row of this table contains the following information:

| Column             | Description                                                      |
|--------------------|------------------------------------------------------------------|
| `[run_id]`         | Estimates run identifier                                         |
| `[year]`           | Year within estimates run                                        |
| `[mgra]`           | The Master Geographic Reference Area (MGRA)                      |
| `[value]`          | Household population                                             |

# Navigation

* [Home Page](README.md)
* [Startup](Startup.md)
* [Housing and Households](Housing-and-Households.md)
* Population by Type
* [Population by Age/Sex/Ethnicity](Population-by-Age-Sex-Ethnicity.md)
    * [Regional Age/Sex/Ethnicity Controls by Housing Type](ase/Regional-Age-Sex-Ethnicity-Controls-By-Housing-Type.md)
    * [Census Tract Age/Sex/Ethnicity Seed](ase/Census-Tract-Age-Sex-Ethnicity-Seed.md)
* [Household Characteristics](Household-Characteristics.md)
* [Staging](Staging.md)
* [Utility](Utility.md)