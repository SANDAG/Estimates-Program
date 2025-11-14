# Housing and Households Module

# Inputs

| Input                                          | Module Source   | Usage                                                                          |
|------------------------------------------------|-----------------|--------------------------------------------------------------------------------| 
| MGRA cross-reference (`[inputs].[mgra]`)       | Startup         | Used to merge MGRA values with census tract rates and city controls            |
| Point geometry housing stock by land use       | External (LUDU) | Generate counts of housing units by structure type within each MGRA            |
| Census tract occupancy rates by structure type | External (ACS)  | Apply to housing units to create households by structure type within each MGRA |
| City total occupancy rate controls             | External (DOF)  | Adjust households to match overall occupancy rate by city                      |

## MGRA cross-reference (`[inputs].[mgra]`)
See [Startup](/documentation/Startup.md#mgra-geography-and-cross-reference-inputsmgra).

## Point geometry housing stock by land use

MGRA housing stock by structure type is aggregated from SANDAG's point geometry Land Use and Dwelling Unit Inventory (LUDU) dataset to the MGRA-level. To ensure that housing stock is assigned to the correct MGRA, a spatial join is used to match LUDU point geometries to MGRA polygons. As LUDU contains land use codes instead of structure types, a mapping between the two is used and shown below. Note that just because a land use is listed does not imply there are housing units for that land use in a given year. Land use code definitions are maintained by SANDAG's Geographic Information Systems (GIS) team with the most recent definitions [available here](https://www.sandag.org/regional-plan/sustainable-growth-and-development/land-use).

| Land Use Code (inclusive) | Land Use Description                                            | Structure Type                |
|---------------------------|-----------------------------------------------------------------|-------------------------------|
| 1000 to 1119              | Spaced Rural Residential and Single Family Residential Detached | Single Family - Detached      |
| 1120 to 1199              | Single Family Attached and Residential Without Units            | Single Family - Multiple Unit |
| 1200 to 1299              | Multifamily Residential                                         | Multifamily                   |
| 1300                      | Mobile Home                                                     | Mobile Home                   |
| 1401 to 1409              | Group Quarters                                                  | Multifamily                   |
| 1501 to 1503              | Hotel/Motel/Resort                                              | Multifamily                   |
| 2000 to 2105              | Heavy Industry and Light Industry                               | Single Family - Multiple Unit |
| 2201 to 2301              | Extractive Industry and Junkyards/Dumps/Landfills               | Single Family - Detached      |
| 4101 to 4120              | Airports and Other Transportation                               | Single Family - Detached      |
| 5000 to 6003              | Commercial and Office                                           | Single Family - Multiple Unit |
| 6100 to 6109              | Public Services                                                 | Single Family - Detached      |
| 6501 to 6509              | Hospitals                                                       | Single Family - Multiple Unit |
| 6701 to 6703              | Military Use                                                    | Single Family - Detached      |
| 6805 to 6809              | Schools                                                         | Single Family - Multiple Unit |
| 7200 to 7211              | Commercial Recreation                                           | Single Family - Detached      |
| 7601 to 7609              | Parks                                                           | Single Family - Detached      |
| 8000 to 8003              | Agriculture                                                     | Single Family - Detached      |
| 9700 to 9709              | Mixed use                                                       | Multifamily                   |

## Census tract occupancy rates by structure type

Occupancy rates are derived from two American Community Survey (ACS) tables, [B25024 | UNITS IN STRUCTURE](https://data.census.gov/table/ACSDT5Y2020.B25024?q=B25024) and [B25032 | TENURE BY UNITS IN STRUCTURE](https://data.census.gov/table/ACSDT5Y2020.B25032?q=B25032). The first table provides housing structures by structure type. The second table provides households by structure type. Dividing the two provides census tract occupancy rates by structure type.

```math
\forall t \in \text{San Diego Tracts}, \forall st \in \text{Structure Types}; \text{Occupancy Rate}_{t,st} = \frac{\text{Households}_{t,st}}{\text{Housing Structures}_{t,st}}
```

To avoid division by zero errors, the occupancy rate is set to `NULL` if housing structures are zero within a census tract and structure type. This can lead to conflict between ACS data and SANDAG's LUDU. Within a census tract and structure type, the ACS may have no housing units and a `NULL` occupancy rate while SANDAG's LUDU contains housing units. In this situation, the regional occupancy rate by structure type is used.

```math
\forall st \in \text{Structure Types}; \text{Regional Occupancy Rate}_{st} = \frac{\sum \text{Households}_{st}}{\sum \text{Housing Structures}_{st}}
```

## City total occupancy rate controls

City-level total occupancy controls are directly pulled from the [California Department of Finance (DOF) Estimates](https://dof.ca.gov/forecasting/demographics/estimates/). For years 2010-2019, data is pulled from the most recent E-8 product at the time. For years 2020+, data is pulled from the most recent E-5 product at the time. Note the DOF provides vacancy rates, so occupancy rates are derived by simple subtraction.

```math
\forall c \in \text{San Diego Cities}; \text{Occupancy Rate}_c = 1 - \text{Vacancy Rate}_c
```

# Outputs

## Housing by structure type in each MGRA (`[outputs].[hs]`)
MGRA housing stock by structure type. Generated from SANDAG's LUDU point layer, mapping land use codes to structure types.

Each row of this table contains the following information:

| Column             | Description                                                      |
|--------------------|------------------------------------------------------------------|
| `[run_id]`         | Estimates run identifier                                         |
| `[year]`           | Year within estimates run                                        |
| `[mgra]`           | The Master Geographic Reference Area (MGRA)                      |
| `[structure_type]` | Housing unit structure type                                      |
| `[value]`          | Number of housing units                                          |

## Households by structure type in each MGRA (`[outputs].[hh]`)
MGRA households by structure type. Calculated by applying census tract occupancy rates by structure type to MGRA housing stock by structure type and controlling overall occupancy rates at the city-level to controls from the DOF.

Each row of this table contains the following information:

| Column             | Description                                                      |
|--------------------|------------------------------------------------------------------|
| `[run_id]`         | Estimates run identifier                                         |
| `[year]`           | Year within estimates run                                        |
| `[mgra]`           | The Master Geographic Reference Area (MGRA)                      |
| `[structure_type]` | Housing unit structure type household resides in                 |
| `[value]`          | Number of households                                             |

# Navigation

* [Home Page](README.md)
* [Startup](Startup.md)
* Housing and Households
* [Population by Type](Population-by-Type.md)
* [Population by Age/Sex/Ethnicity](Population-by-Age-Sex-Ethnicity.md)
    * [Regional Age/Sex/Ethnicity Controls by Housing Type](ase/Regional-Age-Sex-Ethnicity-Controls-By-Housing-Type.md)
    * [Census Tract Age/Sex/Ethnicity Seed](ase/Census-Tract-Age-Sex-Ethnicity-Seed.md)
* [Household Characteristics](Household-Characteristics.md)
* [Staging](Staging.md)
* [Utility](Utility.md)