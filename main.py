import pandas as pd
import numpy as np
idx = pd.IndexSlice 

from supply import simulate_apartment_stock
from demand import simulate_hh_stock
import pdb

def get_hhs_in_need(yr:int, interventions: pd.Series, hhs:pd.DataFrame, hh_type: str) -> int:
    '''
    From flows and hhs data computes number of households of given `hh_type` waiting for intervention in the given year
    '''

    # Number of hhs that received any type of intervention up to this moment (including already assigned interventions in this year)
    hhs_intervened_until_now = interventions.loc[idx[:yr,:,hh_type]].sum()

    # The total stock of households in the given year
    stock_of_newcomers = hhs.loc[yr,(hh_type,'entry_cumsum')]

    # The total stock of returnees up to the given year
    stock_of_returnees = hhs.loc[:yr,(hh_type,'returnees')].sum()

    return stock_of_newcomers + stock_of_returnees - hhs_intervened_until_now

def fill_apartment_interventions(yr: int, interventions: pd.Series, apartments: pd.DataFrame, hhs:pd.DataFrame, apartment_type: str, hh_type: str) -> pd.Series:
    '''
    Assign `hh_type` households into `apartment_type` apartments for year `yr`. 

    All households that can be assigned to available apartments are assigned
    '''

    # Number of households that are currently waiting for an intervention
    hhs_in_need = get_hhs_in_need(yr, interventions, hhs, hh_type)

    # Number of apartments that were assigned up to this moment (note that no apartment can be used twice)
    apartments_assigned_until_now = interventions.loc[idx[:yr,apartment_type,:]].sum()

    # Derive number of available apartments
    total_stock_of_apartments = apartments.loc[yr,(apartment_type,'entry_cumsum')] 
    available_apartments = total_stock_of_apartments - apartments_assigned_until_now

    assignment = min(available_apartments, hhs_in_need)

    interventions.loc[(yr,apartment_type, hh_type)] = assignment

    return interventions

def fill_soft_interventions(yr: int, interventions: pd.Series, hhs: pd.DataFrame, hh_type: str, soft_intervention_share: float) -> pd.Series:
    '''
    Assign soft/one off interventions coming from social housing system to certain share of households that are currently waiting for an intervention
    '''
    # Number of households that are currently waiting for an intervention
    hhs_in_need = get_hhs_in_need(yr, flows, hhs, hh_type)

    soft_interventions = hhs_in_need * soft_intervention_share
    interventions.loc[(yr, 'soft', hh_type)] = soft_interventions

    return interventions

def fill_self_help(yr, interventions, hhs, hh_type, self_help_share):
    '''
    Assign self-help (i.e coming from outside of the social housing system) to certain share of households that are currently waiting for an intervention
    '''
    
    # Number of households that are currently waiting for an intervention    
    hhs_in_need = get_hhs_in_need(yr, interventions, hhs, hh_type)
    self_helps = hhs_in_need * self_help_share
    
    interventions.loc[(yr, 'self_help', hh_type)] = self_helps

    return interventions

def generate_interventions(
    apartments: pd.DataFrame, 
    hhs: pd.DataFrame, 
    apartment_relapse_rate: float, 
    apartment_returnee_delay: int, 
    soft_relapse_rate: float, 
    soft_intervention_share: float, 
    active_self_help_share: float, 
    inactive_self_help_share: float, 
    self_help_relapse_rate: float,
    years: np.ndarray
) -> pd.DataFrame:
    '''
    Generates interventions within the social housing system. 
    
    4 types of interventions are simulated:
        - `private`: household is assigned to private apartment
        - `municipal`: household is assigned to municipal apartment
        - `soft`: household is assigned a soft intervention
        - `self_help`: household gets out of housing emergency by other means than social housing system and/or soft intervention
        
    Interventions are done on two groups of households
        - `active`
        - `inactive.
        
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

    # Interventions are filled in the pregenerated pd.Series with multi-index with 3 dimensions - year, intervention type and hh type. Here only NaN are values, will be filled during settlement
    interventions = pd.Series(index=pd.MultiIndex.from_product([years,['private','municipal','soft','self_help'],['active','inactive']], names=('year', 'intervention','hh')),dtype=float)

    for yr in years:
        active_apartment_returnees = interventions.loc[idx[yr-apartment_returnee_delay, ['private','municipal'],'active']].sum() * apartment_relapse_rate if yr >= apartment_returnee_delay else 0
        inactive_apartment_returnees = interventions.loc[idx[yr-apartment_returnee_delay, ['private','municipal'],'inactive']].sum() * apartment_relapse_rate if yr >= apartment_returnee_delay else 0

        active_soft_returnees = interventions.loc[idx[yr-1, 'soft','active']] * soft_relapse_rate if yr > 0 else 0
        inactive_soft_returnees = interventions.loc[idx[yr-1, 'soft','inactive']] * soft_relapse_rate if yr > 0 else 0
        
        active_self_help_returnees = interventions.loc[idx[yr-1, 'self_help','active']] * self_help_relapse_rate if yr > 0 else 0
        inactive_self_help_returnees = interventions.loc[idx[yr-1, 'self_help','inactive']] * self_help_relapse_rate if yr > 0 else 0

        hhs.loc[yr,('active','returnees')] = active_apartment_returnees + active_soft_returnees + active_self_help_returnees
        hhs.loc[yr,('inactive','returnees')] = inactive_apartment_returnees + inactive_soft_returnees + inactive_self_help_returnees

        interventions = fill_self_help(yr, interventions, hhs, 'active', active_self_help_share)
        interventions = fill_self_help(yr, interventions, hhs, 'inactive', inactive_self_help_share)

        interventions = fill_soft_interventions(yr, interventions, hhs, 'active', soft_intervention_share)
        interventions = fill_soft_interventions(yr, interventions, hhs, 'inactive', soft_intervention_share)
        
        interventions = fill_apartment_flows(yr, interventions, apartments, hhs, 'private', 'active')
        interventions = fill_apartment_flows(yr, interventions, apartments, hhs, 'municipal', 'inactive')
        interventions = fill_apartment_flows(yr, interventions, apartments, hhs, 'private', 'inactive')
        interventions = fill_apartment_flows(yr, interventions, apartments, hhs, 'municipal', 'active')
        
    return interventions


def generate_hhs_stats(hhs, flows, private_years_of_support, municipal_years_of_support, apartment_cost):
    def hhs_stats(hhs,flows,hh_type,private_years_of_support,municipal_years_of_support):
        total_cumsum = hhs[hh_type].entry_cumsum + hhs[hh_type].returnees.cumsum()

        supported = flows.loc[idx[:,:,hh_type]].unstack('intervention')
        
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
        hhs_stats(hhs,flows,'active', private_years_of_support, municipal_years_of_support),
        hhs_stats(hhs,flows,'inactive', private_years_of_support, municipal_years_of_support)
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
    apartment_cost,
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
        flows=flows,
        private_years_of_support=private_years_of_support,
        municipal_years_of_support=municipal_years_of_support,
        apartment_cost=apartment_cost
    ) #TODO apartment_costs
    
    return interventions, hhs_stats
