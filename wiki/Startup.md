# Inputs

The Startup module has no inputs.

# Outputs

## MGRA Geography and Cross-Reference (`[inputs].[mgra]`)

Create the Master Geographic Reference Area (MGRA) geography and cross-reference, used for every year of an Estimates run. The MGRA is the base unit of geography and nests within the larger geographies used by the Estimates Program. As of now, these geographies are the census tracts and jurisdictions within San Diego County. Cross-references are pulled from SANDAG's internal `[GeoAnalyst]` database, which contains the documentation and methodology used to generate the cross-references.

## Special MGRAs (`[inputs].[special_mgras]`)

MGRAs may contain special kinds of population and must be treated differently. Currently, only one type of special MGRA population is accounted for by SANDAG's Estimates Program, defined in this output table: 
1. MGRAs with prison population, aka `Group Quarters - Institutional Correctional Facilities`, that have age and/or sex restrictions due to being strictly juvenile, adult, male, or female only facilities.

Each row of this table contains the following information:

| Column         | Description                                                      |
|----------------|------------------------------------------------------------------|
| `[mgra15]`     | The Series 15 MGRA the age/sex restrictions are applied to       |
| `[start_year]` | The year inclusive that restrictions start being applied to      |
| `[end_year]`   | The year inclusive that restrictions stop being applied to       |
| `[pop_type]`   | The housing type restrictions are applied to                     |
| `[sex]`        | (Optional) The sex the population must be                        |
| `[min_age]`    | (Optional) The minimum age inclusive the population can be       |
| `[max_age]`    | (Optional) The maximum age inclusive the population can be       |
