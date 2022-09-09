import pandas as pd
idx = pd.IndexSlice 

from supply import simulate_apartment_stock
from demand import simulate_hh_stock
import pdb

def generate_flows(apartments, hhs, apartment_relapse_rate, apartment_returnee_delay, soft_relapse_rate, soft_intervention_share, years):
    
    flows = pd.Series(index=pd.MultiIndex.from_product([years,['private','municipal','soft_intervention'],['active','inactive']], names=('year', 'apartment','hh')),dtype=float)

    def fill_apartment_flows(yr, flows, apartments, hhs, apartment_type, hh_type):
        hhs_assigned_until_now = flows.loc[idx[:yr,:,hh_type]].sum()
        stock_of_newcomers = hhs.loc[yr,(hh_type,'entry_cumsum')]
        stock_of_returnees = hhs.loc[:yr,(hh_type,'returnees')].sum()
        #stock_of_soft_interventions = hhs.loc[:yr,(hh_type,'returnees')].sum()
        hhs_in_need = stock_of_newcomers + stock_of_returnees - hhs_assigned_until_now #- stock_of_soft_interventions
        
        apartments_assigned_until_now = flows.loc[idx[:yr,apartment_type,:]].sum() 
        total_stock_of_apartments = apartments.loc[yr,(apartment_type,'entry_cumsum')] 
        available_apartments = total_stock_of_apartments - apartments_assigned_until_now

        assignment = min(available_apartments, hhs_in_need)
        
        #if assignment < -1:
        #    pdb.set_trace()
        flows.loc[(yr,apartment_type, hh_type)] = assignment

        return flows

    def fill_soft_interventions(yr, flows, hhs, hh_type, soft_intervention_share):
        hhs_intervened_until_now = flows.loc[idx[:yr,:,hh_type]].sum()
        stock_of_newcomers = hhs.loc[yr,(hh_type,'entry_cumsum')]
        stock_of_returnees = hhs.loc[:yr,(hh_type,'returnees')].sum()

        hhs_in_need = hhs_in_need = stock_of_newcomers + stock_of_returnees - hhs_intervened_until_now
        
        soft_interventions = hhs_in_need * soft_intervention_share
        flows.loc[(yr, 'soft_intervention', hh_type)] = soft_interventions
        
        return flows
    
    for yr in years:

        active_returnees = flows.loc[idx[yr-apartment_returnee_delay, ['private','municipal'],'active']].sum() * apartment_relapse_rate if yr >= apartment_returnee_delay else 0
        inactive_returnees = flows.loc[idx[yr-apartment_returnee_delay, ['private','municipal'],'inactive']].sum() * apartment_relapse_rate if yr >= apartment_returnee_delay else 0

        active_soft_returnees = flows.loc[idx[yr-1, 'soft_intervention','active']] * soft_relapse_rate if yr > 0 else 0
        inactive_soft_returnees = flows.loc[idx[yr-1, 'soft_intervention','inactive']] * soft_relapse_rate if yr > 0 else 0
        
        hhs.loc[yr,('active','returnees')] = active_returnees + active_soft_returnees
        hhs.loc[yr,('inactive','returnees')] = inactive_returnees + inactive_soft_returnees

        flows = fill_soft_interventions(yr, flows, hhs, 'active', soft_intervention_share)
        flows = fill_soft_interventions(yr, flows, hhs, 'inactive', soft_intervention_share)
        
        flows = fill_apartment_flows(yr, flows, apartments, hhs, 'private', 'active')
        flows = fill_apartment_flows(yr, flows, apartments, hhs, 'municipal', 'inactive')
        flows = fill_apartment_flows(yr, flows, apartments, hhs, 'private', 'inactive')
        flows = fill_apartment_flows(yr, flows, apartments, hhs, 'municipal', 'active')
        
    return flows


def generate_hhs_stats(hhs, flows, private_years_of_support, municipal_years_of_support, apartment_cost):
    def hhs_stats(hhs,flows,hh_type,private_years_of_support,municipal_years_of_support):
        total_cumsum = hhs[hh_type].entry_cumsum + hhs[hh_type].returnees.cumsum()

        supported = flows.loc[idx[:,:,hh_type]].unstack('apartment')
        
        outside_cumsum = pd.DataFrame({
            'private':supported.private.shift(private_years_of_support).cumsum(),
            'municipal':supported.municipal.shift(municipal_years_of_support).cumsum(),
            'soft_intervention':supported.shift(1).soft_intervention.cumsum()
        })

        currently_in_municipal = supported.municipal.rolling(municipal_years_of_support,center=False, min_periods=1).sum()
        currently_in_private = supported.private.rolling(private_years_of_support,center=False, min_periods=1).sum()
        recent_soft = supported.soft_intervention

        
        queue = total_cumsum - currently_in_municipal - currently_in_private - recent_soft - outside_cumsum.sum(axis=1)
        
        df = pd.DataFrame({
            (hh_type,'in_queue'):queue,
            (hh_type,'currently_in_municipal'):currently_in_municipal,
            (hh_type,'currently_in_private'):currently_in_private,
            (hh_type,'recent_soft'):recent_soft,
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
        apartment_relapse_rate=apartment_relapse_rate,
        apartment_returnee_delay=apartment_returnee_delay,
        soft_relapse_rate=soft_relapse_rate,
        soft_intervention_share=soft_intervention_share,
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
