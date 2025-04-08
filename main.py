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

# Loop through the years first
for year in utils.RUN_INSTRUCTIONS["years"]:
    print(f"Running {year}...")

    # Go through each module in the correct order for the specififed year

    # Startup module
    if utils.RUN_INSTRUCTIONS["startup"]:
        print("\tRunning Startup module...")

    # Housing and Households module
    if utils.RUN_INSTRUCTIONS["housing_and_households"]:
        print("\tRunning Housing and Households module...")

    # Population module
    if utils.RUN_INSTRUCTIONS["population"]:
        print("\tRunning Population module...")

    # Population by Age/Sex/Ethnicity module
    if utils.RUN_INSTRUCTIONS["population_by_ase"]:
        print("\tRunning Population by Age/Sex/Ethnicity module...")

    # Household Characteristics module
    if utils.RUN_INSTRUCTIONS["household_characteristics"]:
        print("\tRunning Household Characteristics module...")

    # Staging module
    if utils.RUN_INSTRUCTIONS["staging"]:
        print("\tRunning Staging module...")

    # Diagnostic print for this year
    print(f"Finished running {year}\n")

# Final print for completion
print("Completed")
