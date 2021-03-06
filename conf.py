def config_reports( conf ):
    custom_event_list_for_later = [
      "ViralSuppressionYes",
      "ViralSuppressionNo",
      "DelayUntilBooster1",
      "ReceivedBooster",
      "Vaccinated",
      "ReceivedPrEP"
    ]
    conf.parameters.Report_Event_Recorder_Events = [
      "NewInfectionEvent",
      "HIVSymptomatic",
      # "StartTreatment",
      "StartedART",
      # "GetTested",
      # "HIVPositiveTest"
    ]
    conf.parameters.Report_HIV_ART = 1
    #conf.parameters.Report_HIV_ART_Start_Year = 2004
    #conf.parameters.Report_HIV_ART_Stop_Year = 10000
    conf.parameters.Report_HIV_ByAgeAndGender = 1
    conf.parameters.Report_HIV_ByAgeAndGender_Add_Relationships = 1
    conf.parameters.Report_HIV_ByAgeAndGender_Add_Transmitters = 1
    conf.parameters.Report_HIV_ByAgeAndGender_Collect_Age_Bins_Data = [
      0,
      5,
      10,
      15,
      20,
      25,
      30,
      35,
      40,
      45,
      50,
      55,
      60,
      100
    ]
    conf.parameters.Report_HIV_ByAgeAndGender_Collect_Circumcision_Data = 1
    conf.parameters.Report_HIV_ByAgeAndGender_Collect_Gender_Data = 1
    conf.parameters.Report_HIV_ByAgeAndGender_Collect_HIV_Data = 1
    #conf.parameters.Report_HIV_ByAgeAndGender_Collect_IP_Data = [ "ARTstate" ]
    conf.parameters.Report_HIV_ByAgeAndGender_Collect_Intervention_Data = []
    conf.parameters.Report_HIV_ByAgeAndGender_Collect_On_Art_Data = 1
    rhbaagecl_events_for_later = [
      "Program_VMMC",
      "Non_Program_MMC"
    ]
    conf.parameters.Report_HIV_ByAgeAndGender_Event_Counter_List = [ "NewInfectionEvent" ]
    conf.parameters.Report_HIV_ByAgeAndGender_Has_Intervention_With_Name = "Traditional_MC"
    conf.parameters.Report_HIV_ByAgeAndGender_Start_Year = 1980
    conf.parameters.Report_HIV_ByAgeAndGender_Stop_Year = 2199
    conf.parameters.Report_HIV_Event_Channels_List = [
      "NewInfectionEvent"
    ]
    conf.parameters.Report_HIV_Infection = 1
    conf.parameters.Report_HIV_Mortality = 1
    conf.parameters.Report_HIV_Period = 365
    conf.parameters.Report_Relationship_Start = 1
    conf.parameters.Report_Transmission = 1
    conf.parameters.Report_HIV_Infection_Start_Year = 1980
    conf.parameters.Report_HIV_Infection_Stop_Year = 2050
   
def config_non_schema_params( conf ):
    conf.parameters["Disable_IP_Whitelist"] = 1
    conf.parameters["Enable_Continuous_Log_Flushing"] = 0
    conf.parameters["logLevel_default"] = "WARNING"
    #conf.parameters.alpha__logLevel_Memory = "WARNING"
    #conf.parameters.logLevel_InfectionHIV = "ERROR"
    #conf.parameters.logLevel_Instrumentation = "ERROR"
    #conf.parameters.logLevel_Memory = "ERROR"
    #conf.parameters.logLevel_OutbreakIndividual = "ERROR"
    #conf.parameters.logLevel_Simulation = "ERROR"
    #conf.parameters.logLevel_SusceptibilityHIV = "ERROR"

def set_config ( conf ):

    conf.parameters.Demographics_Filenames = [
            "Rakai_Demographics_With_Properties.json", 
            "Accessibility_and_Risk_IP_Overlay.json", 
            "PFA_Overlay.json", 
            "Risk_Assortivity_Overlay.json"
        ]

    # 'Useless' params (not actually used by HIV) -- will be gone after merging in multi-parent depends-on solution from G-O.
    conf.parameters.Base_Incubation_Period = 0
    conf.parameters.Incubation_Period_Distribution = "FIXED_DURATION"
 
    # HIV Science Params
    conf.parameters.Simulation_Type = "HIV_SIM"
    conf.parameters.Base_Infectivity = 0.00031382269992254885
    conf.parameters.AIDS_Stage_Infectivity_Multiplier = 4.5
    conf.parameters.CD4_At_Death_LogLogistic_Heterogeneity = 0.7
    conf.parameters.CD4_At_Death_LogLogistic_Scale = 2.96
    conf.parameters.CD4_Post_Infection_Weibull_Heterogeneity = 0.2756
    conf.parameters.CD4_Post_Infection_Weibull_Scale = 560.43
    conf.parameters.Coital_Dilution_Factor_2_Partners = 0.75
    conf.parameters.Coital_Dilution_Factor_3_Partners = 0.6
    conf.parameters.Coital_Dilution_Factor_4_Plus_Partners = 0.45
    conf.parameters.Condom_Transmission_Blocking_Probability = 0.8
    conf.parameters.Days_Between_Symptomatic_And_Death_Weibull_Heterogeneity = 0.5
    conf.parameters.Days_Between_Symptomatic_And_Death_Weibull_Scale = 618.341625
    conf.parameters.Enable_Maternal_Infection_Transmission = 1
    conf.parameters.HIV_Age_Max_for_Adult_Age_Dependent_Survival = 50
    conf.parameters.Male_To_Female_Relative_Infectivity_Ages = [ 0, 15, 25 ]
    conf.parameters.Male_To_Female_Relative_Infectivity_Multipliers = [2.9976868182763963, 2.9976868182763963, 2.936393464131044 ]
    conf.parameters.Maternal_Infection_Transmission_Probability = 0.3
    conf.parameters.Maternal_Transmission_ART_Multiplier = 0.03334
    conf.parameters.Min_Days_Between_Adding_Relationships = 0
    conf.parameters.PFA_Burnin_Duration_In_Days = 5475
    conf.parameters.STI_Coinfection_Acquisition_Multiplier = 5.5
    conf.parameters.STI_Coinfection_Transmission_Multiplier = 5.5
    conf.parameters.Sexual_Debut_Age_Female_Weibull_Heterogeneity = 0.22002507694706103
    conf.parameters.Sexual_Debut_Age_Female_Weibull_Scale = 15.092122890359025
    conf.parameters.Sexual_Debut_Age_Male_Weibull_Heterogeneity = 0.1268087803455056
    conf.parameters.Sexual_Debut_Age_Male_Weibull_Scale = 15.582384534190258

    ## We will remove this parameter when demographics are set programmatically
    conf.parameters.Age_Initialization_Distribution_Type = "DISTRIBUTION_COMPLEX"
    conf.parameters.Enable_Natural_Mortality = 1
    conf.parameters.Death_Rate_Dependence = "NONDISEASE_MORTALITY_BY_YEAR_AND_AGE_FOR_EACH_GENDER"
    conf.parameters.Mortality_Time_Course = "DAILY_MORTALITY"
    conf.parameters.x_Other_Mortality = 1

    config_non_schema_params( conf )
    config_reports( conf )
