#!/usr/bin/env python

import pathlib # for a join
from functools import partial  # for setting Run_Number. In Jonathan Future World, Run_Number is set by dtk_pre_proc based on generic param_sweep_value...

# idmtools ...
from idmtools.assets import Asset, AssetCollection  #
from idmtools.builders import SimulationBuilder
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment
from idmtools_platform_comps.utils.python_requirements_ac.requirements_to_asset_collection import RequirementsToAssetCollection
from idmtools_models.templated_script_task import get_script_wrapper_unix_task

# emodpy
from emodpy.emod_task import EMODTask
from emodpy.utils import EradicationBambooBuilds
from emodpy.bamboo import get_model_files

import control_params
import manifest

# ****************************************************************
#  Read experiment info from a config (py) file
#  Add Eradication as an asset (Experiment level)
#  Add Custom file as an asset (Simulation level)
#  Add the local asset directory to the task
#  Use builder to sweep simulations
#  How to run dtk_pre_process.py as pre-process
#  Save experiment info to file
# ****************************************************************

def update_sim_random_seed(simulation, value):
    simulation.task.config.parameters.Run_Number = value
    return {"Run_Number": value}

def print_params():
    """
    Just a useful convenience function for the user.
    """
    # Display exp_name and nSims
    # TBD: Just loop through them
    print("exp_name: ", control_params.exp_name)
    print("nSims: ", control_params.nSims)

def set_param_fn( config ):

    # Simulation Setup
    config.parameters.Base_Population_Scale_Factor = control_params.Base_Population_Scale_Factor
    config.parameters.Base_Year = control_params.Base_Year
    config.parameters.Enable_Demographics_Reporting = control_params.Enable_Demographics_Reporting
    config.parameters.Individual_Sampling_Type = control_params.Individual_Sampling_Type
    config.parameters.Simulation_Timestep = control_params.Simulation_Timestep 
    config.parameters.Load_Balance_Filename = control_params.Load_Balance_Filename
    config.parameters.Node_Grid_Size = control_params.Node_Grid_Size
    config.parameters.Random_Number_Generator_Policy = control_params.Random_Number_Generator_Policy
    config.parameters.Random_Number_Generator_Type = control_params.Random_Number_Generator_Type
    config.parameters.Simulation_Duration = control_params.Simulation_Duration 

    # config hacks until schema fixes arrive
    config.parameters.pop( "Serialized_Population_Filenames" )
    config.parameters.pop( "Serialization_Time_Steps" )
    config.parameters.Report_HIV_Event_Channels_List = []
    config.parameters.Male_To_Female_Relative_Infectivity_Ages = [] # 15,25,35 ]
    config.parameters.Male_To_Female_Relative_Infectivity_Multipliers = [] # 5, 1, 0.5 ]
    # This one is crazy! :(
    config.parameters.Maternal_Infection_Transmission_Probability = 0

    import conf
    conf.set_config(config)

    return config

def timestep_from_year( year ):
    return (year-control_params.Base_Year)*365

def build_camp():
    """
    Build a campaign input file for the DTK using emod_api.
    Right now this function creates the file and returns the filename. If calling code just needs an asset that's fine.
    """
    import emod_api.campaign as camp
    camp.set_schema( manifest.schema_file )
    import emodpy_hiv.interventions.outbreak as ob
    event = ob.seed_infections(camp, start_day = timestep_from_year(control_params.Base_Year + 1), coverage = 0.075, target_properties = "Risk:MEDIUM")
    camp.add( event )
    return camp


def build_demog():
    """
    Build a demographics input file for the DTK using emod_api.
    Right now this function creates the file and returns the filename. If calling code just needs an asset that's fine.
    Also right now this function takes care of the config updates that are required as a result of specific demog settings. We do NOT want the emodpy-disease developers to have to know that. It needs to be done automatically in emod-api as much as possible.
    TBD: Pass the config (or a 'pointer' thereto) to the demog functions or to the demog class/module.

    """
    import emodpy_hiv.demographics.HIVDemographics as Demographics # OK to call into emod-api

    demog = Demographics.from_template_node( lat=0, lon=0, pop=10000, name=1, forced_id=1 )
    return demog

def general_sim( erad_path, ep4_scripts ):
    """
    This function is designed to be a parameterized version of the sequence of things we do 
    every time we run an emod experiment. 
    """
    print_params()

    # Create a platform
    # Show how to dynamically set priority and node_group
    platform = Platform("Calculon", node_group="idm_48cores", priority="Highest") 
    pl = RequirementsToAssetCollection( platform, requirements_path=manifest.requirements ) 

    task = EMODTask.from_default2(config_path="config.json", eradication_path=manifest.eradication_path, campaign_builder=build_camp, demog_builder=None, schema_path=manifest.schema_file, param_custom_cb=set_param_fn, ep4_custom_cb=None)

    #task.common_assets.add_asset( demog_path )

    print("Adding asset dir...")
    task.common_assets.add_directory(assets_directory=manifest.assets_input_dir)

    # Set task.campaign to None to not send any campaign to comps since we are going to override it later with
    # dtk-pre-process.
    print("Adding local assets (py scripts mainly)...")

    if ep4_scripts is not None:
        for asset in ep4_scripts:
            pathed_asset = Asset(pathlib.PurePath.joinpath(manifest.ep4_path, asset), relative_path="python")
            task.common_assets.add_asset(pathed_asset)

    # Create simulation sweep with builder
    builder = SimulationBuilder()
    builder.add_sweep_definition( update_sim_random_seed, range(control_params.nSims) )

    # create experiment from builder
    experiment  = Experiment.from_builder(builder, task, name=control_params.exp_name) 

    # The last step is to call run() on the ExperimentManager to run the simulations.
    experiment.run(wait_until_done=True, platform=platform)

    #other_assets = AssetCollection.from_id(pl.run())
    #experiment.assets.add_assets(other_assets)

    # Check result
    if not experiment.succeeded:
        print(f"Experiment {experiment.uid} failed.\n")
        exit()

    print(f"Experiment {experiment.uid} succeeded.")

    # Save experiment id to file
    with open("COMPS_ID", "w") as fd:
        fd.write(experiment.uid.hex)
    print()
    print(experiment.uid.hex)
    assert experiment.succeeded
    

def run_test( erad_path ):
    general_sim( erad_path, manifest.my_ep4_assets )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    # parser.add_argument('-v', '--use_vpn', action='store_true',
    #                     help='get model files from Bamboo(needs VPN)')
    parser.add_argument('-v', '--use_vpn', type=str, default='No', choices=['No', "Yes"],
                        help='get model files from Bamboo(needs VPN) or Pip installation(No VPN)')
    args = parser.parse_args()
    if args.use_vpn.lower() == "yes":
        from enum import Enum, Flag, auto
        class MyEradicationBambooBuilds(Enum): # EradicationBambooBuilds
            HIV_LINUX = "DTKHIVONGOING-SCONSRELLNXSFT"

        plan = MyEradicationBambooBuilds.HIV_LINUX
        get_model_files( plan, manifest, False )
    else:
        import emod_hiv.bootstrap as dtk
        dtk.setup(pathlib.Path(manifest.eradication_path).parent)

    run_test( manifest.eradication_path )
