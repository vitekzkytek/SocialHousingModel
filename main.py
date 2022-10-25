import pandas as pd
import numpy as np
idx = pd.IndexSlice 

from supply import simulate_apartment_stock
from demand import simulate_hh_stock
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
        
        # remove ending interventions from ongoing interventions
        hhs.loc[yr, [('ongoing_intervention',h) for h in HH_RISKS]] = (hhs.loc[yr-1].loc['ongoing_intervention'] - ending_interventions.sum(axis=1)).loc[HH_RISKS].to_list()
                
        # and the rest put outside
        hhs.loc[yr, [('outside',h) for h in HH_RISKS]] = (hhs.loc[yr-1].loc['outside'] + ending_interventions.sum(axis=1) + number_of_returnees.unstack().sum()).loc[HH_RISKS].to_list()

    return hhs, returnees
    
def generate_interventions(
    apartments: pd.DataFrame, 
    relapse_rates: pd.DataFrame,
    intervention_shares: pd.DataFrame,
    low_risk_to_high_risk_transfer_share: float,
    high_risk_to_low_risk_transfer_share: float,
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

def simulate_social_housing(
    private_yearly_apartments,
    municipal_apartments_today,
    municipal_yearly_new_apartments,
    municipal_existing_availability_rate,
    municipal_new_availability_rate,
    active_current_hh_in_need,
    active_yearly_new_hh,
    inactive_current_hh_in_need,
    inactive_yearly_new_hh,
    apartment_relapse_rate,
    apartment_returnee_delay,
    private_years_of_support,
    municipal_years_of_support,
    private_apartment_cost,
    municipal_apartment_cost,
    soft_relapse_rate,
    soft_intervention_share,
    active_self_help_share,
    inactive_self_help_share,
    self_help_relapse_rate,
    years
):
    apartments = simulate_apartment_stock(
        private_yearly_apartments=private_yearly_apartments,
        municipal_apartments_today = municipal_apartments_today,
        municipal_yearly_new_apartments = municipal_yearly_new_apartments,
        municipal_existing_availability_rate = municipal_existing_availability_rate,
        municipal_new_availability_rate = municipal_new_availability_rate,
        years=years
    )
    
    hhs = simulate_hh_stock(
        active_current_hh_in_need=active_current_hh_in_need,
        active_yearly_new_hh=active_yearly_new_hh,
        inactive_current_hh_in_need=inactive_current_hh_in_need,
        inactive_yearly_new_hh=inactive_yearly_new_hh,
        years=years
    )
    
    interventions = generate_interventions(
        apartments=apartments,
        hhs=hhs,
        apartment_relapse_rate=apartment_relapse_rate,
        apartment_returnee_delay=apartment_returnee_delay,
        soft_relapse_rate=soft_relapse_rate,
        soft_intervention_share=soft_intervention_share,
        active_self_help_share=active_self_help_share,
        inactive_self_help_share=inactive_self_help_share,
        self_help_relapse_rate=self_help_relapse_rate,
        years=years
    )
    
    hhs_stats = generate_hhs_stats(
        hhs=hhs, 
        interventions=interventions,
        private_years_of_support=private_years_of_support,
        municipal_years_of_support=municipal_years_of_support,
        private_apartment_cost=private_apartment_cost,
        municipal_apartment_cost=municipal_apartment_cost
    ) #TODO apartment_costs
    
    return interventions, hhs_stats
