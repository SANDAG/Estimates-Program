# Main control flow for the SANDAG Estimates Program. For runtime instructions, refer
# to the repository README.md. For methodology and other documentation, refer to the
# Wiki which can be found at https://github.com/SANDAG/Estimates-Program/wiki

###########
# Imports #
###########

import python.utils as utils

################
# Control flow #
################

# Run through each module one by one
if utils.CONFIG["debug"]["startup"]:
    print("Running Startup module...")
    for year in utils.CONFIG["debug"]["startup"]:
        print(f"\t{year}")
        pass
if utils.CONFIG["debug"]["housing_and_households"]:
    print("Running Housing and Households module...")
    for year in utils.CONFIG["debug"]["housing_and_households"]:
        print(f"\t{year}")
        pass
if utils.CONFIG["debug"]["population"]:
    print("Running Population module...")
    for year in utils.CONFIG["debug"]["population"]:
        print(f"\t{year}")
        pass
if utils.CONFIG["debug"]["population_by_ase"]:
    print("Running Population by Age/Sex/Ethnicity module...")
    for year in utils.CONFIG["debug"]["population_by_ase"]:
        print(f"\t{year}")
        pass
if utils.CONFIG["debug"]["household_characteristics"]:
    print("Running Household Characteristics module...")
    for year in utils.CONFIG["debug"]["household_characteristics"]:
        print(f"\t{year}")
        pass
if utils.CONFIG["debug"]["staging"]:
    print("Running Staging module...")
    for year in utils.CONFIG["debug"]["staging"]:
        print(f"\t{year}")
        pass
print("Complete")
