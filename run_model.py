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
from emodpy_hiv.interventions.cascade_helpers import *
import emodpy_hiv.interventions.utils as hiv_utils

import control_params
import manifest
import campaign_knobs as ck

# ****************************************************************
#  Read experiment info from a config (py) file
#  Add Eradication as an asset (Experiment level)
#  Add Custom file as an asset (Simulation level)
#  Add the local asset directory to the task
#  Use builder to sweep simulations
#  How to run dtk_pre_process.py as pre-process
#  Save experiment info to file
# ****************************************************************

ART_eligible_tag="Accessibility:Easy"

def _add_sti_by_risk_and_coverage( camp, risk, coverage, include_ongoing=True ):
    """
    Internal function to do the "dirty work" to support add_sti_coinfection_complex.
    1) Add a 'scheduled' campaign event to give some %age of people in a given risk group an STI (co-)infection.
    2) Optionally add a 'triggered' campaign event (at STIDebut) to give some %age of people in a given risk group an STI (co-)infection.
    """
    import emodpy_hiv.interventions.modcoinf as coinf
    set_sti_coinf = coinf.new_intervention( camp )
    set_sti_coinf["Intervention_Name"] = "Pick_Up_A_Nasty"
    signal = hiv_utils.broadcast_event_immediate( camp, "CaughtNonHIVSTI" )

    event = comm.ScheduledCampaignEvent( camp, Start_Day=1, Event_Name="STI Co-Infection Setup", Intervention_List=[set_sti_coinf,signal], Property_Restrictions=risk, Demographic_Coverage=coverage )
    event.Event_Coordinator_Config.pop( "Targeting_Config" )
    camp.add( event )

    if include_ongoing:
        add_triggered_event( camp, in_trigger="STIDebut", out_iv=[set_sti_coinf,signal], coverage=coverage, target_risk=risk, event_name="STI Co-Infection Setup" )


def add_sti_coinfection_complex( camp, low_coverage=0.1, med_coverage=0.3, high_coverage=0.3 ):
    """
    # ScheduledCampaignEvent @ t=0:
    Folks with Risk=LOW get one prob (10%) of STI CoInf
    Folks with Risk=MED or HIGH get another prob (30%) of STI CoInf

    TriggeredCampaigEvent @ OnDebut:
        Same thing as above.
    """
    _add_sti_by_risk_and_coverage( camp, "Risk:LOW", low_coverage, include_ongoing=True )
    _add_sti_by_risk_and_coverage( camp, "Risk:MEDIUM", med_coverage, include_ongoing=True )
    _add_sti_by_risk_and_coverage( camp, "Risk:HIGH", high_coverage, include_ongoing=True )
    

def add_csw( camp ):
    # STIDebut -(HIVDelay)-> Uptake -(PVC)-> Dropout (PVC)
    male_delayed_uptake = hiv_utils.broadcast_event_delayed( camp, "CSW_Uptake", delay={ "Delay_Period": ck.CSW_Male_Uptake_Delay } )
    female_delayed_uptake = hiv_utils.broadcast_event_delayed( camp, "CSW_Uptake", delay={ "Delay_Period": ck.CSW_Male_Uptake_Delay } )

    # 1: STIDebut->Uptake delay (males)
    add_triggered_event( camp, in_trigger="STIDebut", out_iv=male_delayed_uptake, event_name="Male CSW Debut->Uptake", coverage=ck.CSW_Male_Uptake_Coverage, target_sex="Male" )

    # 2: STIDebut->Uptake delay (females)
    add_triggered_event( camp, in_trigger="STIDebut", out_iv=female_delayed_uptake, event_name="Female CSW Debut->Uptake", coverage=ck.CSW_Female_Uptake_Coverage, target_sex="Female" )

    # 4: Uptake->Dropout delay (males)
    male_delayed_dropout = hiv_utils.broadcast_event_delayed( camp, "CSW_Dropout", delay={ "Delay_Period": ck.CSW_Male_Dropout_Delay } )
    female_delayed_dropout = hiv_utils.broadcast_event_delayed( camp, "CSW_Dropout", delay={ "Delay_Period": ck.CSW_Female_Dropout_Delay } )

    add_triggered_event( camp, in_trigger="CSW_Uptake", out_iv=male_delayed_dropout, event_name="Male CSW Uptake->Dropout", coverage=ck.CSW_Male_Dropout_Coverage, target_sex="Male" )

    # 5: Uptake->Dropout delay (females)
    add_triggered_event( camp, in_trigger="CSW_Uptake", out_iv=female_delayed_dropout, event_name="Female CSW Uptake->Dropout", coverage=ck.CSW_Female_Dropout_Coverage, target_sex="Female" )
     
    # 3: Actually do the CSW Uptake (via PropertyValueChanger)
    pvc_go_high = comm.PropertyValueChanger( camp, Target_Property_Key="Risk", Target_Property_Value="HIGH", New_Property_Value="" )
    add_triggered_event( camp, in_trigger="CSW_Uptake", out_iv=pvc_go_high, event_name="CSW Uptake" )

    # 6: Actually do the CSW Dropout (via PropertyValueChanger)
    pvc_go_med = comm.PropertyValueChanger( camp, Target_Property_Key="Risk", Target_Property_Value="MEDIUM", New_Property_Value="" )
    add_triggered_event( camp, in_trigger="CSW_Dropout", out_iv=pvc_go_high, event_name="CSW Dropout" )


def _distribute_psk_tracker_by_age_and_sex( camp, min_age, max_age, sex, tvmap ):
    """
    Internal function to do the 'dirty work' to support 'add_pos_status_known_tracker'.
    """
    # First, give everyone who enters the HIV Latent stage a property that lets 
    # us target them with a "Faux Tested" intervention AND property.
    import emodpy_hiv.interventions.reftracker as reftracker
    # Listen for LatentStage events and set PositiveStatus
    pvc_psk = comm.PropertyValueChanger( camp, Target_Property_Key="TestingStatus", Target_Property_Value="ELIGIBLE", New_Property_Value="" )
    add_triggered_event( camp, in_trigger="HIVInfectionStageEnteredLatent", out_iv=pvc_psk, event_name="Set Eligible for Pos Status Known" )

    # Now, here's what we're going to do...
    # 1) Give out something like the above, that triggers off of HIVInfectionStageEnteredLatent and set an IP for targeting.
    # 2) Give out a ref tracker that filters on the target IP above but distributes a Placebo/MedicalRecord with the name "PositiveStatusKnown" or something. This also sets an IP InterventionStatus:ARTEligible or something nasty. The placebo can be a delay or no-effect vaccine or something for now.
    status_known_medrec = comm.HSB( camp, Tendency=0, Name="PositiveStatusKnown" )
    status_known_medrec.New_Property_Value=ART_eligible_tag # Placeholder for "InterventionStatus:ARTEligible
    event = reftracker.DistributeIVByRefTrack( camp, Start_Day=1, Intervention=status_known_medrec, TVMap=tvmap, Property_Restrictions="TestingStatus:ELIGIBLE", Target_Age_Min=min_age, Target_Age_Max=max_age, Target_Gender=sex )
    camp.add( event )


def add_pos_status_known_tracker( camp ):
    """
    Put some subset of people who have entered latent infection stage into "Positive status known" 'state',
    which makes them ART-eligible. Drive this from data instead of creating a complex cascade that
    uses actually testing, etc. These coverages can vary by age group, sex, and simulation date.
    """
    tvmap = { 1990: 0.1, 2000: 0.2, 2010: 0.6, 2020: 0.8 }
    _distribute_psk_tracker_by_age_and_sex( camp, ck.PSK_Male_Age_Lower_Bound, ck.PSK_Male_Age_Upper_Bound, "Male", tvmap )
    _distribute_psk_tracker_by_age_and_sex( camp, ck.PSK_Female_Age_Lower_Bound, ck.PSK_Female_Age_Upper_Bound, "Female", tvmap )


def _distribute_art_by_ref_counter_by_age_and_sex( camp, art_coverage, min_age, max_age, sex, tvmap ):
    """
    Internal utility function to do the 'dirty work' to support distribute_art_by_ref_counter for a given
    min_age, max_age, and sex. art_coverage is simply for a demonstration campaign sweep.
    """
    import emodpy_hiv.interventions.reftracker as reftracker
    import emodpy_hiv.interventions.art as art
    import emodpy_hiv.interventions.artdropout as art_dropout

    new_art = art.new_intervention( camp )
    started_art_signal = hiv_utils.broadcast_event_immediate(camp, "Started_ART")
    delayed_dropout_iv = hiv_utils.broadcast_event_delayed( camp, "ART_Dropout", delay={ "Delay_Period": ck.ART_Duration } ) # make this duration a bit more sophisticated
    delayed_dropout_iv["Intervention_Name"] = "ART"
    mid = comm.MultiInterventionDistributor( camp, [ new_art, delayed_dropout_iv, started_art_signal ] )
    mid["Intervention_Name"] = "ART"
    # Old way of doing ART is ARTBasic + Delay->ARTDropout
    event = reftracker.DistributeIVByRefTrack( camp, Start_Day=1, Intervention=mid, TVMap=tvmap, Property_Restrictions=ART_eligible_tag, Target_Gender=sex, Target_Age_Min=min_age, Target_Age_Max=max_age )
    camp.add( event )

    ## ART Dropout
    dropout = art_dropout.new_intervention( camp )
    add_triggered_event( camp, in_trigger="ART_Dropout", out_iv=dropout, event_name="ART Dropout" )


def distribute_art_by_ref_counter( camp, art_coverage ):
    """
    For the ART:
    3) Give out a ref tracker that filters on the target IP InterventionStatus:ARTEligible and distributes ART.
    """
    tvmap = { 2004: art_coverage/10, 2010: art_coverage/2, 2020: art_coverage }
    _distribute_art_by_ref_counter_by_age_and_sex( camp, art_coverage, ck.ART_Male_Age_Lower_Bound, ck.ART_Male_Age_Upper_Bound, "Male", tvmap )
    _distribute_art_by_ref_counter_by_age_and_sex( camp, art_coverage, ck.ART_Female_Age_Lower_Bound, ck.ART_Female_Age_Upper_Bound, "Female", tvmap )
    
def update_sim_bic(simulation, value):
    """
        Update the value of a (scientific) configuration parameter, in this case Base_Infectivity_Constant 
        (which may or may not be part of this sim_type's parameters), as part of a sweep.
    """
    simulation.task.config.parameters.Base_Infectivity_Constant = value*0.1
    return {"Base_Infectivity": value}

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

def build_camp( art_coverage = 1.0 ):
    """
        Build a campaign input file for the DTK using emod_api type functions or helpers from this module. 
        Note that 'camp' is short for 'campaign'.
        You can name this function whatever you want, it just has to match what you pass in from_default2.
    """

    # Setup
    import emod_api.campaign as camp
    camp.set_schema( manifest.schema_file )

    # Seed infections
    event = ob.seed_infections(camp, start_day = timestep_from_year(control_params.Base_Year + 1), coverage = 0.075, target_properties = "Risk:MEDIUM")
    camp.add( event )

    add_sti_coinfection_complex(camp, ck.STI_Low_Risk_Coverage, ck.STI_Med_Risk_Coverage, ck.STI_High_Risk_Coverage)
    add_csw( camp )
    add_pos_status_known_tracker( camp )
    distribute_art_by_ref_counter( camp, art_coverage  )
    return camp


def build_demog():
    """
    Build a demographics input file for the DTK using emod_api.
    Right now this function creates the file and returns the filename. If calling code just needs an asset that's fine.
    Also right now this function takes care of the config updates that are required as a result of specific demog settings. We do NOT want the emodpy-disease developers to have to know that. It needs to be done automatically in emod-api as much as possible.
    TBD: Pass the config (or a 'pointer' thereto) to the demog functions or to the demog class/module.

    """
    import emodpy_hiv.demographics.HIVDemographics as Demographics # OK to call into emod-api
    import emod_api.demographics.Demographics as demo
    import emod_api.demographics.DemographicsTemplates as DT

    demog = Demographics.from_template_node( lat=0, lon=0, pop=100000, name=1, forced_id=1 )
    demog.SetEquilibriumAgeDistFromBirthAndMortRates()
    demog.fertility( "Malawi_Fertility_Historical.csv" )
    demog.mortality( "Malawi_male_mortality.csv", "Malawi_female_mortality.csv" )

    # demog = Demographics.from_template_node( lat=0, lon=0, pop=10000, name=1, forced_id=1 )

    demog.AddIndividualPropertyAndHINT( Property="Accessibility", Values=["Easy","Hard"], InitialDistribution=[0.0, 1.0] )
    demog.AddIndividualPropertyAndHINT( Property="Risk", Values=["LOW","MEDIUM","HIGH"], InitialDistribution=[ 0.6637418389, 0.3362581611, 0.0] )
    demog.AddIndividualPropertyAndHINT( Property="TestingStatus", Values=["INELIGIBLE","ELIGIBLE"], InitialDistribution=[1.0, 0 ] )

    ## Assortivity by risk
    demog.apply_assortivity( "COMMERCIAL", [ [1,1,1],[1,1,1],[1,1,1] ] )
    demog.apply_assortivity( "INFORMAL", [ [0.6097767084, 0.3902232916, 0],[0.3902232916,0.6097767084,0.6097767084],[0,0.6097767084,0.3902232916] ] )
    demog.apply_assortivity( "MARITAL", [ [0.6097767084, 0.3902232916, 0],[0.3902232916,0.6097767084,0.6097767084],[0,0.6097767084,0.3902232916] ] )
    demog.apply_assortivity( "TRANSITORY", [ [0.6097767084, 0.3902232916, 0],[0.3902232916,0.6097767084,0.6097767084],[0,0.6097767084,0.3902232916] ] )

    return demog


def art_coverage_test_sweep( simulation, sweep_param ):
    art_coverage = sweep_param/10.0
    build_campaign_partial = partial( build_camp, art_coverage )
    simulation.task.create_campaign_from_callback( build_campaign_partial )
    return {"ART_Target_Coverage": art_coverage }

def general_sim():
    """
    This function is designed to be a parameterized version of the sequence of things we do 
    every time we run an emod experiment. 
    """
    print_params()

    # Create a platform
    # Show how to dynamically set priority and node_group
    platform = Platform("Calculon", node_group="idm_48cores", priority="Highest") 
    # pl = RequirementsToAssetCollection( platform, requirements_path=manifest.requirements ) 

    task = EMODTask.from_default2(config_path="config.json", eradication_path=manifest.eradication_path, campaign_builder=build_camp, demog_builder=build_demog, schema_path=manifest.schema_file, param_custom_cb=set_param_fn, ep4_custom_cb=None)

    #task.common_assets.add_asset( demog_path )

    # print("Adding asset dir...")
    # task.common_assets.add_directory(assets_directory=manifest.assets_input_dir)

    task.set_sif( "dtk_centos.id" )

    # Set task.campaign to None to not send any campaign to comps since we are going to override it later with
    # dtk-pre-process.
    print("Adding local assets (py scripts mainly)...")

    # if ep4_scripts is not None:
    #     for asset in ep4_scripts:
    #         pathed_asset = Asset(pathlib.PurePath.joinpath(manifest.ep4_path, asset), relative_path="python")
    #         task.common_assets.add_asset(pathed_asset)

    # Create simulation sweep with builder
    builder = SimulationBuilder()
    builder.add_sweep_definition( art_coverage_test_sweep, range(control_params.nSims) )

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

    general_sim()
