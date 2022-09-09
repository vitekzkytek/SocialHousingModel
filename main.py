import pandas as pd
idx = pd.IndexSlice 

from supply import simulate_apartment_stock
from demand import simulate_hh_stock


def generate_flows(apartments, hhs, relapse_rate, returnee_delay, years):
    
    flows = pd.Series(index=pd.MultiIndex.from_product([years,['private','municipal'],['active','inactive']], names=('year', 'apartment','hh')),dtype=float)

    def fill_flows(yr, flows, apartments, hhs, apartment_type, hh_type):
        apartments_assigned_until_now = flows.loc[idx[:yr,apartment_type,:]].sum() 
        total_stock_of_apartments = apartments.loc[yr,(apartment_type,'entry_cumsum')] 
        available_apartments = total_stock_of_apartments - apartments_assigned_until_now

        hhs_assigned_until_now = flows.loc[idx[:yr,:,hh_type]].sum()     
        stock_of_newcomers = hhs.loc[yr,(hh_type,'entry_cumsum')]
        stock_of_returnees = hhs.loc[:yr,(hh_type,'returnees')].sum()
        hhs_in_need = stock_of_newcomers + stock_of_returnees - hhs_assigned_until_now

        assignment = min(available_apartments, hhs_in_need)
        flows.loc[(yr,apartment_type, hh_type)] = assignment

        return flows

    for yr in years:

        active_returnees = flows.loc[idx[yr-returnee_delay, :,'active']].sum() * relapse_rate if yr >= relapse_rate else 0
        inactive_returnees = flows.loc[idx[yr-returnee_delay, :,'inactive']].sum() * relapse_rate if yr >= relapse_rate else 0

        hhs.loc[yr,('active','returnees')] = active_returnees
        hhs.loc[yr,('inactive','returnees')] = inactive_returnees

        flows = fill_flows(yr, flows, apartments, hhs, 'private', 'active')
        flows = fill_flows(yr, flows, apartments, hhs, 'municipal', 'inactive')
        flows = fill_flows(yr, flows, apartments, hhs, 'private', 'inactive')
        flows = fill_flows(yr, flows, apartments, hhs, 'municipal', 'active')
        
    return flows


def generate_hhs_stats(hhs, flows, private_years_of_support, municipal_years_of_support, apartment_cost):
    def hhs_stats(hhs,flows,hh_type,private_years_of_support,municipal_years_of_support):
        total_cumsum = hhs[hh_type].entry_cumsum + hhs[hh_type].returnees.cumsum()

        supported = flows.loc[idx[:,:,hh_type]].unstack()

        outside_cumsum = pd.DataFrame({
            'private':supported.private.shift(private_years_of_support).cumsum(),
            'municipal':supported.municipal.shift(municipal_years_of_support).cumsum()
        })

        currently_in_municipal = supported.municipal.rolling(municipal_years_of_support,center=False, min_periods=1).sum()
        currently_in_private = supported.private.rolling(private_years_of_support,center=False, min_periods=1).sum()
        queue = total_cumsum - currently_in_municipal - currently_in_private - outside_cumsum.sum(axis=1)

        df = pd.DataFrame({
            (hh_type,'in_queue'):queue,
            (hh_type,'currently_in_municipal'):currently_in_municipal,
            (hh_type,'currently_in_private'):currently_in_private,
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
    relapse_rate,
    returnee_delay,
    private_years_of_support,
    municipal_years_of_support,
    apartment_cost,
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
    
    flows = generate_flows(
        apartments=apartments,
        hhs=hhs,
        relapse_rate=relapse_rate,
        returnee_delay=returnee_delay,
        years=years
    )
    
    hhs_stats = generate_hhs_stats(
        hhs=hhs, 
        flows=flows,
        private_years_of_support=private_years_of_support,
        municipal_years_of_support=municipal_years_of_support,
        apartment_cost=apartment_cost
    ) #TODO apartment_costs
    
    return flows, hhs_stats
