import pandas as pd
import numpy as np
idx = pd.IndexSlice 

from supply import simulate_apartment_stock

idx = pd.IndexSlice

import pdb

HH_STATUSES = ['queue', 'ongoing_intervention', 'outside']
HH_RISKS = ['low','high']
INTERVENTION_TYPES = ['guaranteed','municipal','mop_payment','self_help','consulting']


def fill_apartment_interventions(yr: int, interventions: pd.Series, apartments: pd.DataFrame, hhs:pd.DataFrame, apartment_type: str, hh_risk: str) -> pd.Series:
    '''
    Assign `hh_type` households into `apartment_type` apartments for year `yr`. 

    All households that can be assigned to available apartments are assigned
    '''

    # Number of households that are currently waiting for an intervention
    hhs_in_need = hhs.loc[yr, ('queue', hh_risk)]

    # Number of apartments that were assigned up to this moment (note that no apartment can be used twice)
    apartments_assigned_until_now = interventions.loc[idx[:yr,apartment_type,:]].sum()

    # Derive number of available apartments
    total_stock_of_apartments = apartments.loc[yr,apartment_type] 
    available_apartments = total_stock_of_apartments - apartments_assigned_until_now

    assignment = min(available_apartments, hhs_in_need)
    
    interventions.loc[(yr,apartment_type, hh_risk)] = assignment
    
    # Remove from queue
    hhs.loc[yr, ('queue', hh_risk)] -= assignment
    hhs.loc[yr, ('ongoing_intervention', hh_risk)] += assignment
    
    return interventions

def fill_share_of_queue_intervention(yr: int, interventions: pd.Series, hhs: pd.DataFrame, intervention_shares: pd.DataFrame, hh_risk: str, intervention_type: str) -> pd.Series:
    '''
    Assign soft/one off interventions coming from social housing system to certain share of households that are currently waiting for an intervention
    '''

    # Number of households that are currently waiting for an intervention
    hhs_in_need = hhs.loc[yr, ('queue', hh_risk)]
    
    # number of hhs to receive queue intervention
    intervened = hhs_in_need * intervention_shares.loc[hh_risk, intervention_type]
    
    # Record interventions
    interventions.loc[(yr, intervention_type, hh_risk)] = intervened

    # Remove from queue
    hhs.loc[yr, ('queue', hh_risk)] = hhs_in_need - intervened
    hhs.loc[yr, ('ongoing_intervention', hh_risk)] += intervened
    
    return hhs, interventions


def determine_hhs_queue(yr, hhs, returnees, interventions, relapse_rates, years_of_support, hhs_inflow):
    # todo determine queue on the beginning of each round - returnees, inflow, transfer of status for each intervention types

    years_of_interest = (yr - years_of_support).apply(lambda x: x if x >= 0 else np.nan).dropna()

    if not years_of_interest.empty:
        ending_interventions = interventions.unstack('intervention_type')[years_of_interest.index].apply(lambda col: col.loc[years_of_interest.loc[col.name]])
        number_of_returnees = (ending_interventions * relapse_rates[ending_interventions.columns]).T.stack()
        
        returnees.loc[yr] = number_of_returnees

        #queue compose of the last year queue, new inflow of hhs and returnees
        hhs.loc[yr, [('queue',h) for h in HH_RISKS]] = (hhs.loc[yr-1].loc['queue'] + hhs_inflow.loc[HH_RISKS,'yearly_growth'] + number_of_returnees.unstack().sum()).loc[HH_RISKS].to_list()
        
        # TODO Move part of last years' low-risk queue to this years high_risk queue
        
        # remove ending interventions from ongoing interventions
        hhs.loc[yr, [('ongoing_intervention',h) for h in HH_RISKS]] = (hhs.loc[yr-1].loc['ongoing_intervention'] - ending_interventions.sum(axis=1)).loc[HH_RISKS].to_list()
                
        # and the rest put outside
        hhs.loc[yr, [('outside',h) for h in HH_RISKS]] = (hhs.loc[yr-1].loc['outside'] + ending_interventions.sum(axis=1) + number_of_returnees.unstack().sum()).loc[HH_RISKS].to_list()

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
    interventions = pd.Series(index=pd.MultiIndex.from_product([years, INTERVENTION_TYPES, HH_RISKS], names=('year', 'intervention_type', 'hh_risk')),dtype=float)
    returnees = pd.DataFrame(index=years, columns=pd.MultiIndex.from_product([INTERVENTION_TYPES,HH_RISKS], names=('intervention_type', 'hh_risk')),dtype=float)
     
    hhs.loc[0, [('queue',h) for h in HH_RISKS]] = hhs_inflow.loc[HH_RISKS,'current_level'].to_list()
    
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
        interventions = fill_apartment_interventions(yr, interventions, apartments, hhs, 'guaranteed', 'low')
        interventions = fill_apartment_interventions(yr, interventions, apartments, hhs, 'municipal', 'high')

        # Secondary assignments of apartments
        interventions = fill_apartment_interventions(yr, interventions, apartments, hhs, 'guaranteed', 'high')
        interventions = fill_apartment_interventions(yr, interventions, apartments, hhs, 'municipal', 'low')
        
    return interventions, hhs, returnees

def generate_hhs_stats(hhs, interventions, private_years_of_support, municipal_years_of_support, private_apartment_cost, municipal_apartment_cost):
    def hhs_stats(hhs,interventions,hh_type,private_years_of_support,municipal_years_of_support):
        total_cumsum = hhs[hh_type].entry_cumsum + hhs[hh_type].returnees.cumsum()

        supported = interventions.loc[idx[:,:,hh_type]].unstack('intervention')
        
        outside_cumsum = pd.DataFrame({
            'private':supported.private.shift(private_years_of_support).cumsum(),
            'municipal':supported.municipal.shift(municipal_years_of_support).cumsum(),
            'self_help':supported.shift(1).self_help.cumsum(),
            'soft':supported.shift(1).soft.cumsum()
        })

        currently_in_municipal = supported.municipal.rolling(municipal_years_of_support,center=False, min_periods=1).sum()
        currently_in_private = supported.private.rolling(private_years_of_support,center=False, min_periods=1).sum()
        recent_soft = supported.soft
        recent_self_help = supported.self_help        
        queue = total_cumsum - currently_in_municipal - currently_in_private - recent_soft - recent_self_help - outside_cumsum.sum(axis=1)
        
        df = pd.DataFrame({
            (hh_type,'in_queue'):queue,
            (hh_type,'currently_in_municipal'):currently_in_municipal,
            (hh_type,'currently_in_private'):currently_in_private,
            (hh_type,'recent_soft'):recent_soft,
            (hh_type,'recent_self_help'):recent_self_help,
            (hh_type,'outside'):outside_cumsum.sum(axis=1)
        })
        return df
    return pd.concat([
        hhs_stats(hhs,interventions,'active', private_years_of_support, municipal_years_of_support),
        hhs_stats(hhs,interventions,'inactive', private_years_of_support, municipal_years_of_support)
    ],axis=1)

def calculate_costs(interventions, years_of_support, intervention_costs):
    
    entry_apartments = interventions.loc[:,['guaranteed', 'municipal'],:].unstack('hh_risk').sum(axis=1).unstack('intervention_type')
    entry_apartments_costs = intervention_costs.loc['entry',['guaranteed', 'municipal']] * entry_apartments

    yearly_apartments = pd.DataFrame({
         col: entry_apartments[col].rolling(years_of_support.loc[col], min_periods=1).sum() for col in ['guaranteed', 'municipal']
    })

    yearly_apartments_costs = intervention_costs.loc['yearly',['guaranteed', 'municipal']] *  yearly_apartments

    consulting = interventions.loc[:,['guaranteed', 'municipal','consulting','mop_payment'],:].unstack(['hh_risk','intervention_type']).sum(axis=1).rename('consulting')
    consulting_costs = (consulting * intervention_costs.loc['entry','consulting']).rename('consulting_costs')

    mops = interventions.loc[:,'mop_payment',:].unstack('hh_risk').sum(axis=1).rename('mops')
    mops_costs = (mops * intervention_costs.loc['entry','mop_payment']).rename('mops_costs')

    social_assistance = yearly_apartments.sum(axis=1).rename('social_assistance')
    social_assistance_costs = (intervention_costs.loc['yearly','social_assistance'] *  yearly_apartments.sum(axis=1)).rename('social_assistance_costs')

    # Rename columns
    entry_apartments.columns = [f'apartments_entry_{col}' for col in entry_apartments.columns]
    entry_apartments_costs.columns = [f'apartments_entry_costs_{col}' for col in entry_apartments_costs.columns]
    yearly_apartments.columns = [f'apartments_yearly_{col}' for col in yearly_apartments.columns] 
    yearly_apartments_costs.columns = [f'apartments_yearly_costs_{col}' for col in yearly_apartments_costs.columns]

    costs = pd.concat([entry_apartments, entry_apartments_costs, yearly_apartments, yearly_apartments_costs, consulting, consulting_costs, mops, mops_costs, social_assistance, social_assistance_costs],axis=1)
    
    return costs

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
    intervention_costs,
    years
):
    apartments = simulate_apartment_stock(
        guaranteed_yearly_apartments=guaranteed_yearly_apartments,
        municipal_apartments_today = municipal_apartments_today,
        municipal_yearly_new_apartments = municipal_yearly_new_apartments,
        municipal_existing_availability_rate = municipal_existing_availability_rate,
        municipal_new_availability_rate = municipal_new_availability_rate,
        years=years
    )
    
    interventions, hhs, returnees = generate_interventions(
        apartments = apartments,
        relapse_rates = relapse_rates,
        intervention_shares = intervention_shares,
        hhs_inflow =hhs_inflow,
        years_of_support = years_of_support,
        years = years
    )
    
    costs = calculate_costs(
        interventions=interventions,
        years_of_support=years_of_support,
        intervention_costs=intervention_costs
    )
    return interventions, hhs, returnees, costs
