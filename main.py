import pandas as pd
import numpy as np
idx = pd.IndexSlice

from supply import simulate_apartment_stock
idx = pd.IndexSlice
import pdb

HH_RISKS = ['low','high']
INTERVENTION_TYPES = ['guaranteed','municipal','mop_payment','self_help','consulting']
HH_STATUSES = INTERVENTION_TYPES + ['queue'] + [f'outside_{it}' for it in INTERVENTION_TYPES]


def fill_apartment_interventions(yr: int, interventions: pd.Series, apartments: pd.DataFrame, hhs:pd.DataFrame, apartment_type: str, hh_risk: str) -> pd.Series:
    '''
    Assign `hh_type` households into `apartment_type` apartments for year `yr`. 

    All households that can be assigned to available apartments are assigned
    '''

    # Number of households that are currently waiting for an intervention
    hhs_in_need = hhs.loc[yr, ('queue', hh_risk)]

    # Number of apartments that were assigned up to this moment (note that no apartment can be used twice)
    apartments_assigned_until_now = interventions.loc[:yr,idx[apartment_type,:]].sum().sum()
    # Derive number of available apartments
    total_stock_of_apartments = apartments.loc[yr,apartment_type] 
    available_apartments = total_stock_of_apartments - apartments_assigned_until_now

    assignment = min(available_apartments, hhs_in_need)

    #if (hhs.loc[yr, (apartment_type,hh_risk)] + assignment) < 0:
    #    pdb.set_trace()
    interventions.loc[yr,(apartment_type, hh_risk)] = assignment
        
    # Remove from queue
    hhs.loc[yr, ('queue', hh_risk)] -= assignment
    
    #last_year = hhs.loc[yr-1, (apartment_type, hh_risk)] if yr > 0 else 0
    hhs.loc[yr, (apartment_type, hh_risk)] += assignment 
    
    return interventions, hhs

def fill_share_of_queue_intervention(yr: int, interventions: pd.Series, hhs: pd.DataFrame, intervention_shares: pd.DataFrame, hh_risk: str, intervention_type: str) -> pd.Series:
    '''
    Assign soft/one off interventions coming from social housing system to certain share of households that are currently waiting for an intervention
    '''

    # Number of households that are currently waiting for an intervention
    hhs_in_need = hhs.loc[yr, ('queue', hh_risk)]
    
    # number of hhs to receive queue intervention
    intervened = hhs_in_need * intervention_shares.loc[hh_risk, intervention_type]
    
    # Record interventions
    interventions.loc[yr, (intervention_type, hh_risk)] = intervened
    # Remove from queue
    #last_year = hhs.loc[yr, (intervention_type, hh_risk)] if yr > 0 else 0
    hhs.loc[yr, ('queue', hh_risk)] -= intervened
    
    #if (hhs.loc[yr, (intervention_type,hh_risk)] + intervened) < 0:
    #    pdb.set_trace()

    hhs.loc[yr, (intervention_type, hh_risk)] += intervened 
    
    return hhs, interventions

def determine_hhs_queue(yr, hhs, returnees, interventions, relapse_rates, years_of_support, hhs_inflow):
    
    # startyears of interventions that end this year (np.nan if none)
    years_of_interest = (yr - years_of_support).apply(lambda x: x if x >= 0 else np.nan).dropna()

    if not years_of_interest.empty:
        # Find ending interventions - accounting for years of interest nans!
                
        ending_interventions = pd.Series(0,index=pd.MultiIndex.from_product([INTERVENTION_TYPES, HH_RISKS], names=('intervention_type', 'hh_risk')))
        ending = interventions[years_of_interest.index].apply(lambda col: col.loc[years_of_interest.loc[col.name[0]]])
        ending_interventions.loc[ending.index] = ending
        
        # TODO handle error of identifying ongoing intervention when years_of_interest is missing. does not identify any. becase ending
        
        ongoing_interventions = hhs.loc[yr - 1, ending_interventions.index] - ending_interventions
        
        hhs.loc[yr, ongoing_interventions.index] = ongoing_interventions

        # New inflow to queue
        hhs.loc[yr, [('queue',h) for h in HH_RISKS]] = (hhs.loc[yr-1].loc['queue'] + hhs_inflow.loc[HH_RISKS,'yearly_growth']).loc[HH_RISKS].to_list()

        # Returnees back to queue
        number_of_returnees = ending_interventions * relapse_rates.unstack().loc[ending_interventions.index]
        returnees.loc[yr] = number_of_returnees
        
        # All returnees are high risks
        hhs.loc[yr, ('queue','high')] = hhs.loc[yr, ('queue','high')] + number_of_returnees.sum() 
        
        # and put the rest outside
        outside_cols = {it: f'outside_{it}' for it in INTERVENTION_TYPES}

        new_outside = (ending_interventions - number_of_returnees).rename(outside_cols)
        
        new_outside.index = new_outside.index.rename(level='intervention_type',names='hh_status')

        hhs.loc[yr, outside_cols.values()] = (hhs.loc[yr-1,outside_cols.values()] + new_outside).fillna(0)
        
    return hhs, returnees
    
def generate_interventions(
    apartments: pd.DataFrame, 
    relapse_rates: pd.DataFrame,
    intervention_shares: pd.DataFrame,
    hhs_inflow: pd.DataFrame,
    years_of_support: pd.Series,
    years: np.ndarray
) -> pd.DataFrame:
    '''
    Generates interventions within the social housing system. 
    
    5 types of interventions are simulated:
        - `private`: household is assigned to private apartment
        - `municipal`: household is assigned to municipal apartment
        - `soft`: household is assigned a soft intervention
        - `consulting_help`: hhs finds a stable housing outside of social housing system
        - `self_help`: household gets out of housing emergency by other means than social housing system and/or soft intervention
        
    Interventions are done on three groups of households
        - `low_risk`
        - `high_risk`
        - `in_danger`
        
    The interventions are computed sequentially, taking into account all of the previous interventions. 
    
    Each year the interventions are done in the following order: 
    1. Apartment-returnees back to the system (so that they can be intervened)
    2. Soft interventions returnees back to the system 
    3. Self-helps (active, inactive)
    4. Soft interventions (active, inactive)
    5. Active households to private apartments
    6. Inactive households to municipal apartments
    7. Inactive households to private apartments
    8. Active households to municipal apartments
    '''    
    #phases = ['year_start','new_inflow','new_returnees','before_status_change','year_end']
    
    # Pregenerate table for households
    hhs = pd.DataFrame(0,index=years, columns=pd.MultiIndex.from_product([HH_STATUSES, HH_RISKS], names=('hh_status', 'hh_risk')),dtype=float)

    # Pregenerate Interventions and Returnees (Returnees only for tracking purpose)
    interventions = pd.DataFrame(index=years,columns=pd.MultiIndex.from_product([INTERVENTION_TYPES, HH_RISKS], names=('intervention_type', 'hh_risk')),dtype=float)
    returnees = pd.DataFrame(index=years, columns=pd.MultiIndex.from_product([INTERVENTION_TYPES,HH_RISKS], names=('intervention_type', 'hh_risk')),dtype=float)
     
    #hhs.loc[0, [('total',h) for h in HH_RISKS]] = hhs_inflow.loc[HH_RISKS,'current_level'].to_list()
    hhs.loc[0, [('queue',h) for h in HH_RISKS]] = hhs_inflow.loc[HH_RISKS,'current_level'].to_list() #hhs.loc[0, [('total',h) for h in HH_RISKS]]
    
    for yr in years:
        # Determine number of households in the queue
        hhs, returnees = determine_hhs_queue(
                yr = yr,
                hhs = hhs,
                returnees = returnees,
                interventions = interventions, 
                relapse_rates = relapse_rates, 
                years_of_support = years_of_support,
                hhs_inflow = hhs_inflow
            )

        for intervention_type in ['self_help','consulting','mop_payment']:
            for hh_risk in HH_RISKS:
                hhs, interventions = fill_share_of_queue_intervention(
                    yr = yr, 
                    interventions = interventions,
                    hhs = hhs,
                    intervention_shares = intervention_shares,
                    hh_risk = hh_risk, 
                    intervention_type = intervention_type
                )
                
        # Priority assignments of apartments
        interventions, hhs = fill_apartment_interventions(yr, interventions, apartments, hhs, 'guaranteed', 'low')
        interventions, hhs = fill_apartment_interventions(yr, interventions, apartments, hhs, 'municipal', 'high')
        
        # Secondary assignments of apartments
        interventions, hhs = fill_apartment_interventions(yr, interventions, apartments, hhs, 'guaranteed', 'high')
        interventions, hhs = fill_apartment_interventions(yr, interventions, apartments, hhs, 'municipal', 'low')
        
    return interventions, hhs, returnees


def calculate_costs(interventions, hhs, years_of_support, social_assistences, intervention_costs):
    
    # Number of apartment interventions in given year
    
    entry_apartments = interventions.loc[:,idx[['guaranteed', 'municipal'],:]].groupby('intervention_type',axis=1).sum()

    # Number of apartments assigned in the given year (years_of_support included)
    yearly_apartments = pd.DataFrame({
         col: entry_apartments[col].rolling(years_of_support.loc[col], min_periods=1).sum() for col in ['guaranteed', 'municipal']
    })

    # Number of consultings - all interventions in 'guaranteed', 'municipal','consulting','mop_payment'
    consulting = interventions.loc[:,idx[['guaranteed', 'municipal','consulting','mop_payment'],:]].sum(axis=1).rename('consulting')

    # Number of Mops
    mops = interventions.loc[:,idx['mop_payment',:]].sum(axis=1).rename('mop_payment')

    # Number of social assistnces - defined by social_assistences table
    yearly_social_assistence = (entry_apartments.join(mops) * social_assistences.share)
    yearly_social_assistence = pd.DataFrame({
        col: (yearly_social_assistence[col]).rolling(int(social_assistences.years.loc[col]), min_periods=1).sum() for col in ['guaranteed', 'mop_payment','municipal']
    }).sum(axis=1).rename('social_assistance')

    # Rename columns
    entry_apartments.columns = [f'apartments_entry_{col}' for col in entry_apartments.columns]
    yearly_apartments.columns = [f'apartments_yearly_{col}' for col in yearly_apartments.columns] 

    ## Queue units
    queue = hhs.queue.sum(axis=1).rename('queue')
    
    
    costs_units = pd.concat([entry_apartments, yearly_apartments, consulting, mops,  yearly_social_assistence,queue],axis=1)

    # Convert units to costs ("lepení cenovek")
    costs = pd.DataFrame({
        'apartments_yearly_guaranteed': costs_units['apartments_yearly_guaranteed'] * intervention_costs.loc['yearly','guaranteed'],
        'apartments_entry_guaranteed': costs_units['apartments_entry_guaranteed'] * intervention_costs.loc['entry','guaranteed'],
        'apartments_yearly_municipal': costs_units['apartments_yearly_municipal'] * intervention_costs.loc['yearly','municipal'],
        'apartments_entry_municipal': costs_units['apartments_entry_municipal'] * intervention_costs.loc['entry','municipal'],
        'consulting': costs_units['consulting'] * intervention_costs.loc['entry','consulting'],
        'mop_payment': costs_units['mop_payment'] * intervention_costs.loc['entry','mop_payment'],
        'social_assistence': costs_units['social_assistance'] * intervention_costs.loc['yearly','social_assistance'],
        'queue_budget': costs_units['queue'] * intervention_costs.loc['yearly','queue_budget'],
        'queue_social': costs_units['queue'] * intervention_costs.loc['yearly','queue_social'],
    })    
    return costs, costs_units

def simulate_social_housing(
    guaranteed_yearly_apartments,
    municipal_apartments_today ,
    municipal_yearly_new_apartments,
    municipal_existing_availability_rate,
    municipal_new_availability_rate,
    relapse_rates,
    intervention_shares,
    hhs_inflow,
    years_of_support,
    social_assistences,
    intervention_costs,
    years,
    title
):
    apartments = simulate_apartment_stock(
        guaranteed_yearly_apartments=guaranteed_yearly_apartments,
        municipal_apartments_today = municipal_apartments_today,
        municipal_yearly_new_apartments = municipal_yearly_new_apartments,
        municipal_existing_availability_rate = municipal_existing_availability_rate,
        municipal_new_availability_rate = municipal_new_availability_rate,
        years=years,
    )
    
    interventions, hhs, returnees = generate_interventions(
        apartments = apartments,
        relapse_rates = relapse_rates,
        intervention_shares = intervention_shares,
        hhs_inflow =hhs_inflow,
        years_of_support = years_of_support,
        years = years
    )
    
    costs, costs_units = calculate_costs(
        interventions=interventions,
        hhs = hhs,
        years_of_support=years_of_support,
        social_assistences=social_assistences,
        intervention_costs=intervention_costs
    )
    
    return interventions, hhs, returnees, costs, costs_units
