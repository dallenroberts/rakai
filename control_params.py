## Simulation Controls
Base_Population_Scale_Factor = 0.05
Base_Year = 1960.5
Simulation_Timestep = 30.4166666666667 ## Default, but most EMOD HIV models use 30.4166666666667
Simulation_Duration = 60*365.0 # maybe this should be a team-wide default? Rakai uses 20700
nSims = 10

## Simulation Metadata
exp_name="HIV Demo"

## Other
Enable_Demographics_Reporting = 0  # just because I don't like our default for this
Individual_Sampling_Type = "FIXED_SAMPLING"
Load_Balance_Filename = ""
Node_Grid_Size = 0.009 
Random_Number_Generator_Policy = "ONE_PER_NODE"
Random_Number_Generator_Type = "USE_AES_COUNTER"