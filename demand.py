import pandas as pd
import numpy as np

def simulate_hh_stock(
    active_current_hh_in_need: int,
    active_yearly_new_hh: int,
    inactive_current_hh_in_need: int,
    inactive_yearly_new_hh: int,
    years: np.ndarray
) -> pd.DataFrame :
    
    '''
    Houshold stock is simulated in two dimensions:
    
    1. Economically active population in housing emergency (those who can work, namely people in productive age). Note that also economically active population can be unemployed.
    2. Economically inactive population in housing emergency (those with no or low job perspective - elderly, caring for children etc.
    
    Both groups takes a current level (*active_current_hh_in_need*, *inactive_current_hh_in_need*) which is increased by constant yearly amount (*inactive_yearly_new_hh*, *active_yearly_new_hh*). 
    
    Note that number of households is in cumulative terms regardless of whether and how they have been intervened.
    
    Returns:
    pd.DataFrame with columns: (active, entry_cumsum), (inactive, entry_cumsum), (active, returnees), (inactive, returnees), 
     - only `entry_cumsum` columns filled - cumulative number of household ever being in housing emergency up to the given year (inclusive)
     - `returnees` with NaN (to be filled during settlement of the model)
    
    '''

    active =  pd.Series({
        yr: active_current_hh_in_need + (active_yearly_new_hh * yr )  for yr in years    
    })

    inactive =  pd.Series({
        yr: inactive_current_hh_in_need + (inactive_yearly_new_hh * yr )  for yr in years    
    })
    
    hhs = pd.DataFrame({('active','entry_cumsum'):active,('inactive','entry_cumsum'):inactive})
    
    hhs[('active','returnees')] = np.NaN
    hhs[('inactive','returnees')] = np.NaN

    return hhs.sort_index(axis=1)
