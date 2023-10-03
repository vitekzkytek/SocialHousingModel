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
    Assign `hh_risk` households into `apartment_type` apartments for year `yr`. 

    All households that can be assigned to available apartments are assigned
    
    Records an intervention into `hhs` and `interventions` dataframes.
    '''

    # Number of households that are currently waiting for an intervention
    hhs_in_need = hhs.loc[yr, ('queue', hh_risk)]

    # Number of apartments that were assigned up to this moment (note that no apartment can be used twice)
    apartments_assigned_until_now = interventions.loc[:yr,idx[apartment_type,:]].sum().sum()
    
    # Derive number of available apartments

    total_stock_of_apartments = apartments.loc[yr,apartment_type] 
    available_apartments = total_stock_of_apartments - apartments_assigned_until_now

    assignment = min(available_apartments, hhs_in_need)

    interventions.loc[yr,(apartment_type, hh_risk)] = assignment
        
    # Remove from queue
    hhs.loc[yr, ('queue', hh_risk)] -= assignment
    
    #last_year = hhs.loc[yr-1, (apartment_type, hh_risk)] if yr > 0 else 0
    hhs.loc[yr, (apartment_type, hh_risk)] += assignment 
    
    return interventions, hhs

def fill_share_interventions(yr: int, interventions: pd.Series, hhs: pd.DataFrame, intervention_shares: pd.DataFrame, hh_risks, intervention_types, startup_coefficients: pd.Series,hhs_inflow: pd.DataFrame, ) -> pd.Series:
    '''
    Assign soft `intervention_type` to `hh_risk` households. The share is determined from `intervention_shares`.
    
    Records an intervention into `hhs` and `interventions` dataframes.
    '''
    if (intervention_shares.sum(axis=1) > 1).any():
        raise Exception('Intervention shares cannot sum above 100% in one hh group...')
    
    # Number of households that are currently waiting for an intervention
    #if yr == 0:
    eligible_hhs = hhs.loc[yr, 'queue']
    #else:
    #   eligible_hhs = hhs_inflow.yearly_growth
        
    real_intervention_shares = intervention_shares.copy()
    if yr in (startup_coefficients.index):
        real_intervention_shares[startup_coefficients.columns] = intervention_shares[startup_coefficients.columns] * startup_coefficients.loc[yr]
    
    # number of hhs to receive queue intervention
    intervened = (eligible_hhs * real_intervention_shares.T).stack()
    
    # Record interventions
    interventions.loc[yr, intervened.index] = intervened
    
    # Remove from queue
    hhs.loc[yr, [('queue',hh_risk) for hh_risk in HH_RISKS]] -= intervened.unstack(1).sum().loc[HH_RISKS].to_list()
    
    # Record hhs interventions
    hhs.loc[yr, intervened.index] += intervened 
    
    return hhs, interventions

def determine_hhs_queue(yr, hhs, returnees, interventions, relapse_rates, years_of_support, hhs_inflow, low_to_high_risk_share):
    '''
    To find how many hhs in queue is going to be on the beginning of year `yr` it is necessary:
    
        1. To determine number of returnees
        2. To account for an inflow of new hhs
        
    Also number of ongoing interventions is stated on the beginning of each year - that is in later steps adjusted.   
    '''
    # startyears of interventions that end this year (np.nan if none)
    years_of_interest = (yr - years_of_support).apply(lambda x: x if x >= 0 else np.nan).dropna()

    if not years_of_interest.empty:
        # Some low risks in queue are now high-risks
        #pdb.set_trace()
        old_queue = hhs.loc[yr-1].loc['queue'] 
        new_queue = old_queue.copy()
        
        old_queue_risk_transfer = old_queue.loc['low'] * low_to_high_risk_share
        

        new_queue.loc['low'] -= old_queue_risk_transfer
        new_queue.loc['high'] += old_queue_risk_transfer
        
            
        # New inflow to queue # TODO check functionality of transfer from if statement below
        hhs.loc[yr, [('queue',h) for h in HH_RISKS]] = (new_queue.loc[HH_RISKS] + hhs_inflow.loc[HH_RISKS,'yearly_growth']).loc[HH_RISKS].to_list()

        # Find ending interventions - accounting for years of interest nans!       
        ending_interventions = pd.Series(0,index=pd.MultiIndex.from_product([INTERVENTION_TYPES, HH_RISKS], names=('intervention_type', 'hh_risk')))
        ending = interventions[years_of_interest.index].apply(lambda col: col.loc[years_of_interest.loc[col.name[0]]])
        ending_interventions.loc[ending.index] = ending
        
        # How many interventions are currently in place?
        ongoing_interventions = hhs.loc[yr - 1, ending_interventions.index] - ending_interventions
        hhs.loc[yr, ongoing_interventions.index] = ongoing_interventions


        # Returnees back to queue
        number_of_returnees = ending_interventions * relapse_rates.unstack().loc[ending_interventions.index]
        returnees.loc[yr] = number_of_returnees
        #hhs.loc[yr, ('queue','high')] = hhs.loc[yr, ('queue','high')] + number_of_returnees.sum() 
        
        returnees_to_queue = number_of_returnees.unstack('hh_risk').sum()
        returnees_risk_transfer = returnees_to_queue.loc['low'] * low_to_high_risk_share
        
        returnees_to_queue.loc['low'] -= returnees_risk_transfer
        returnees_to_queue.loc['high'] += returnees_risk_transfer
        
        hhs.loc[yr, [('queue',h) for h in HH_RISKS]] += returnees_to_queue        
        
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
    low_to_high_risk_share: float,
    startup_coefficients: pd.DataFrame,
    years: np.ndarray
) -> pd.DataFrame:
    '''
    Generates interventions within the social housing system. 
    
    5 types of interventions are simulated:
        - `guaranteed`: household is assigned to private guaranteed apartment
        - `municipal`: household is assigned to municipal apartment
        - `mop_payment`: household is assigned a mop payment intervention
        - `consulting`: hhs finds a stable housing outside of social housing system
        - `self_help`: household gets out of housing emergency by other means than social housing system and/or soft intervention
        
    Interventions are done on two groups of households
        - `low_risk`
        - `high_risk`
        
    The interventions are computed sequentially, taking into account all of the previous interventions. 
    
    Each year the interventions are done in the following order: 
        1. Determine hhs and particularly queue (so that they can be intervened)
        3. Self-helps (separately for high risk and low risks)
        4. Consultings
        5. MOPs
        5. Low risk households to guaranteed apartments
        6. High risk households to municipal apartments
        7. High risk households to guaranteed apartments
        8. Low risk households to municipal apartments
    '''    
    # Pregenerate table for households
    hhs = pd.DataFrame(0,index=years, columns=pd.MultiIndex.from_product([HH_STATUSES, HH_RISKS], names=('hh_status', 'hh_risk')),dtype=float)

    # Pregenerate Interventions and Returnees (Returnees only for tracking purpose)
    interventions = pd.DataFrame(index=years,columns=pd.MultiIndex.from_product([INTERVENTION_TYPES, HH_RISKS], names=('intervention_type', 'hh_risk')),dtype=float)
    returnees = pd.DataFrame(index=years, columns=pd.MultiIndex.from_product([INTERVENTION_TYPES,HH_RISKS], names=('intervention_type', 'hh_risk')),dtype=float)
     
    # Assign hhs currently in queue (current level)
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
                hhs_inflow = hhs_inflow,
                low_to_high_risk_share = low_to_high_risk_share
            )
        
        # Assign soft interventions for both low risks and high risks
        hhs, interventions = fill_share_interventions(
            yr = yr, 
            interventions = interventions,
            hhs = hhs,
            intervention_shares = intervention_shares,
            hh_risks = HH_RISKS, 
            intervention_types = ['self_help','consulting','mop_payment'],
            startup_coefficients = startup_coefficients[['consulting','mop_payment']],
            hhs_inflow = hhs_inflow,
        )
                
        # Priority assignments of apartments
        interventions, hhs = fill_apartment_interventions(yr, interventions, apartments, hhs, 'guaranteed', 'low')
        interventions, hhs = fill_apartment_interventions(yr, interventions, apartments, hhs, 'municipal', 'high')
        
        # Secondary assignments of apartments
        interventions, hhs = fill_apartment_interventions(yr, interventions, apartments, hhs, 'guaranteed', 'high')
        interventions, hhs = fill_apartment_interventions(yr, interventions, apartments, hhs, 'municipal', 'low')
        #pdb.set_trace()
    return interventions, hhs, returnees


def calculate_costs(interventions, hhs, years_of_support, social_assistences, intervention_costs, discount_rate, mop_housing_share):
    '''
    At the end of the simulation process use simulated interventions to determine costs of the system
    '''
    
    yrs_index = interventions.index
    
    # Number of apartment interventions in given year
    
    entry_apartments = interventions.loc[:,idx[['guaranteed', 'municipal'],:]].groupby('intervention_type',axis=1).sum()

    # Number of apartments assigned in the given year (years_of_support included)
    yearly_apartments = pd.DataFrame({
         col: entry_apartments[col].rolling(years_of_support.loc[col], min_periods=1).sum() for col in ['guaranteed', 'municipal']
    })

    # Number of consultings - all interventions in 'guaranteed', 'municipal','consulting','mop_payment'
    consulting_units = interventions.loc[:,idx[['guaranteed', 'municipal','consulting','mop_payment'],:]].sum(axis=1).rename('consulting')
    
    # Number of Mops
    mops = interventions.loc[:,idx['mop_payment',:]].sum(axis=1).rename('mop_payment')
    housing_mops = interventions[['guaranteed','municipal']].apply(lambda col: col * mop_housing_share.loc[col.name[0],col.name[1]]).sum(axis=1).rename('mop_payment')
    mops = mops + housing_mops
    
    # Number of social assistnces - defined by social_assistences table
    social_assistence_breakdown = (entry_apartments.join(mops-housing_mops) * social_assistences.share)

    social_assistence_breakdown = pd.DataFrame({
        col: (social_assistence_breakdown[col]).rolling(int(social_assistences.years.loc[col]), min_periods=1).sum() for col in ['guaranteed', 'mop_payment','municipal']
    })

    # Rename columns
    entry_apartments.columns = [f'apartments_entry_{col}' for col in entry_apartments.columns]
    yearly_apartments.columns = [f'apartments_yearly_{col}' for col in yearly_apartments.columns] 

    ## Queue units
    queue = hhs.queue.sum(axis=1).rename('queue')
    
    # Combine units into a dataframe
    costs_units = pd.concat([entry_apartments, yearly_apartments, consulting_units, mops,  social_assistence_breakdown.sum(axis=1).rename('social_assistance'),queue],axis=1)
    
    # Fixed costs for consulting
    consulting = pd.Series(intervention_costs.loc['yearly','consulting'], index = yrs_index)
    consulting.iloc[0] += intervention_costs.loc['one_off','consulting']

    # Fixed costs for regional administration
    regional_administration = pd.Series(intervention_costs.loc['yearly','regional_administration'], index = yrs_index)

    # IT system - one-off accounted to the first year
    fixed_it = pd.Series(0, index = yrs_index)
    fixed_it.loc[0] = intervention_costs.loc['one_off','IT_system']
    
    
    it_system = pd.DataFrame({
        # one off costs
        'one_off': fixed_it,
        # operational/yearly costs
        'yearly':pd.Series(intervention_costs.loc['yearly','IT_system'], index = yrs_index)
    })

    # Convert units to costs ("labelling price tags")
    costs = pd.DataFrame({
        'IT_system':it_system.sum(axis=1),
        'apartments_yearly_guaranteed': costs_units['apartments_yearly_guaranteed'] * intervention_costs.loc['yearly','guaranteed'],
        'apartments_entry_guaranteed': costs_units['apartments_entry_guaranteed'] * intervention_costs.loc['entry','guaranteed'],
        'apartments_yearly_municipal': costs_units['apartments_yearly_municipal'] * intervention_costs.loc['yearly','municipal'],
        'apartments_entry_municipal': costs_units['apartments_entry_municipal'] * intervention_costs.loc['entry','municipal'],
        'consulting': consulting,
        'regional_administration': regional_administration,
        'mop_payment': costs_units['mop_payment'] * intervention_costs.loc['entry','mop_payment'],
        'social_assistence': costs_units['social_assistance'] * intervention_costs.loc['yearly','social_assistance'],
        'queue_budget': costs_units['queue'] * intervention_costs.loc['yearly','queue_budget'],
        'queue_social': costs_units['queue'] * intervention_costs.loc['yearly','queue_social'],
    })    

    # discounting future costs
    costs_discounted = costs.apply(lambda row: row/((1+discount_rate) ** row.name), axis=1)

    return costs, costs_units, costs_discounted, social_assistence_breakdown

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
    discount_rate,
    low_to_high_risk_share,
    startup_coefficients,
    mop_housing_share,
    years,
    base_year=2025,
    title=None
):
    '''
    An entering function into model. If not interested in breaking the model to pieces, you most likely want to use this function.
    
    Accepts all parameters (or dict to be decomposed by `**kwargs`)
    
    Procedure: 
        1. Simulation of apartments stock (in LEVELS)
        2. Generates all interventions
        3. Calculate costs
        
    Returns dataframes with relevant outputs:
        * `interventions` contain assigned interventions in each year
        * `hhs` contains status of hhs in given year
        * `
    
    '''
    apartments = simulate_apartment_stock(
        guaranteed_yearly_apartments=guaranteed_yearly_apartments,
        municipal_apartments_today = municipal_apartments_today,
        municipal_yearly_new_apartments = municipal_yearly_new_apartments,
        municipal_existing_availability_rate = municipal_existing_availability_rate,
        municipal_new_availability_rate = municipal_new_availability_rate,
        startup_coefficients = startup_coefficients[['guaranteed','municipal']],
        years=years,
    )
    
    interventions, hhs, returnees = generate_interventions(
        apartments = apartments,
        relapse_rates = relapse_rates,
        intervention_shares = intervention_shares,
        hhs_inflow =hhs_inflow,
        years_of_support = years_of_support,
        low_to_high_risk_share = low_to_high_risk_share,
        startup_coefficients = startup_coefficients,
        years = years
    )
    
    
    costs, costs_units, costs_discounted, social_assistence_breakdown = calculate_costs(
        interventions=interventions,
        hhs = hhs,
        years_of_support=years_of_support,
        social_assistences=social_assistences,
        intervention_costs=intervention_costs,
        discount_rate=discount_rate,
        mop_housing_share=mop_housing_share
    )
    
    interventions.index = (interventions.index + base_year).rename('rok')
    hhs.index = (hhs.index + base_year).rename('rok')
    returnees.index = (returnees.index + base_year).rename('rok')
    
    costs.index = (costs.index + base_year).rename('rok')
    costs_units.index = (costs_units.index + base_year).rename('rok')
    costs_discounted.index = (costs_discounted.index + base_year).rename('rok')
    social_assistence_breakdown.index = (social_assistence_breakdown.index + base_year).rename('rok')
    return {
        'interventions':interventions,
        'hhs':hhs.sort_index(),
        'returnees':returnees,
        'costs':costs,
        'costs_units':costs_units, 
        'costs_discounted':costs_discounted,
        'social_assistence_breakdown':social_assistence_breakdown,
        'title':title
    }
