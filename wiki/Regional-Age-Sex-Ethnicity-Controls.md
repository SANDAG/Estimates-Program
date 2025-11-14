# Inputs

| Input                                                   | Module Source          | Usage                                                             |
|---------------------------------------------------------|------------------------|-------------------------------------------------------------------| 
| Regional population by housing type (`[outputs].[gq]` and `[outputs].[hhp]`) | Population by Type | Used to calculate group quarters age/sex/ethnicity by type and the household population age/sex/ethnicity as remainder |
| Regional age/sex/ethnicity distributions for group quarters by type | External (ACS) | Applied to group quarters population by type to get group quarters age/sex/ethnicity by type |
| Regional age/sex/ethnicity controls for total population | External (DOF) | Used to calculate household population age/sex/ethnicity as remainder |

## Regional population by housing type (`[outputs].[gq]` and `[outputs].[hhp]`)
See [Population by Type](https://github.com/SANDAG/Estimates-Program/wiki/Population-by-Type).

## Regional age/sex/ethnicity distributions for group quarters by type
The regional age/sex/ethnicity distributions for group quarters by type are calculated using the 5-year American Community Survey (ACS) Public Use Microdata Sample (PUMS) for the given estimates year (e.g., 2020 uses the 2016-2020 PUMS, 2021 the 2017-2021 PUMS, ...). For documentation, including field definitions, see the [PUMS Documentation](https://www.census.gov/programs-surveys/acs/microdata/documentation.html).

Age/sex/ethnicity is encoded using the fields `[AGEP]`, `[SEX]`, `[HISP]`, and `[RAC1P]`.

Group quarters population is identified as follows:
| Estimates year(s) | Definition                  |
|:-----------------:|-----------------------------|
| 2010              | `[RELP] IN ('14','15')`     |
| 2011              | `[RELP] IN ('13',14')`      |
| 2012-2018         | `[RELP] IN ('16','17')`     |
| 2016-2023         | `[RELSHIPP] IN ('37','38')` |

Further filtering is done to identify specific GQ types:
| Estimates year(s) | Group Quarters Type                   | Definition                                           |
| :----------------:|---------------------------------------|------------------------------------------------------|
| 2010              | College                               | `[SCHG] IN ('6', '7')`                               |
|                   | Military                              | `[ESR] IN ('4','5')`                                 |
|                   | Institutional Correctional Facilities | `[RELP] = '14' AND [AGEP] >= 10`                     |
|                   | Other                                 | all other group quarters persons                     |
|                   |                                       |                                                      |
| 2011              | College                               | `[SCHG] IN ('6', '7')`                               |
|                   | Military                              | `[ESR] IN ('4','5')`                                 |
|                   | Institutional Correctional Facilities | `[RELP] = '13' AND [AGEP] >= 10`                     |
|                   | Other                                 | all other group quarters persons                     |
|                   |                                       |                                                      |
| 2012-2018         | College                               | `[SCHG] IN ('15', '16')`                             |
|                   | Military                              | `[ESR] IN ('4','5')`                                 |
|                   | Institutional Correctional Facilities | `[RELP] = '16' AND [DIS] = '2' AND [AGEP] >= 10`     |
|                   | Other                                 | all other group quarters persons                     |
|                   |                                       |                                                      |
| 2019-2023         | College                               | `[SCHG] IN ('15', '16')`                             |
|                   | Military                              | `[ESR] IN ('4','5')`                                 |
|                   | Institutional Correctional Facilities | `[RELSHIPP] = '37' AND [DIS] = '2' AND [AGEP] >= 10` |
|                   | Other                                 | all other group quarters persons                     |

## Regional age/sex/ethnicity controls for total population
The regional age/sex/ethnicity controls for total population are derived from the most recent [California Department of Finance (DOF) Projections](https://dof.ca.gov/forecasting/demographics/projections/) P-3 product available at the time. 

# Outputs
The regional age/sex/ethnicity controls for total population from the DOF are scaled to match the total population, derived from the estimates output of regional population by housing type ([see Population by Type](https://github.com/SANDAG/Estimates-Program/wiki/Population-by-Type)). Subsequently, regional group quarters age/sex/ethnicity population by type is calculated by applying the distributions from the 5-year ACS PUMS to the regional population by housing type. Finally, regional household age/sex/ethnicity population is calculated as the remainder of the scaled regional age/sex/ethnicity controls for total population and the regional group quarters age/sex/ethnicity population by type.

While not an official output of the module, the regional age/sex/ethnicity controls by housing type are stored in the `[inputs].[controls_ase]` table for review and debugging purposes.