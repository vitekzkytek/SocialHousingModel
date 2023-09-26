import pandas as pd
import numpy as np
import pdb

def simulate_guaranteed(
        guaranteed_yearly_apartments: int,
        startup: pd.Series,
        years: np.ndarray
    ) -> pd.Series:
    '''
    Simulates total number of private apartments available in the social housing system.
    
    Based on simple parameter *private_yearly_apartments* which constitues the number of apartments per year entering the system.
    
    Returns: pd.Series with the total number of private apartments that ever entered the social housing system.
    '''
    inflow = pd.Series({yr:guaranteed_yearly_apartments for yr in years})
    inflow.loc[startup.index] = inflow.loc[startup.index] * startup 
    return inflow.cumsum()
    
def simulate_municipal(
        municipal_apartments_today: int,
        municipal_yearly_new_apartments: int,
        municipal_existing_availability_rate: float,
        municipal_new_availability_rate: float,
        startup: pd.Series,
        years: np.ndarray
) -> pd.Series:
    '''
    Simulates total number of municipal apartments available in the social housing system.
    
    The municipal apartments are derived from two sources:
     1. *existing stock of municipal aparments*: from which a share (municipal_existing_availability_rate) is released each year to the stock. The existing stock starts at *municipal_apartments_today* and is gradually increased
     2. *new municipal apartment*: Each year *municipal_yearly_new_apartments*  are built from which a share (*municipal_new_availability_rate*) is put into the system.

    Returns: pd.Series with the total number of municipal apartments that ever entered the social housing system.
    '''
    
    municipal_stock = pd.Series({yr: municipal_apartments_today + municipal_yearly_new_apartments*(yr-1) for yr in years})
    
    
    existing_stock = municipal_stock.shift(1,fill_value=municipal_stock.iloc[0]) * municipal_existing_availability_rate
    new_stock = municipal_yearly_new_apartments * municipal_new_availability_rate
    inflow = existing_stock + new_stock
    inflow.loc[startup.index] = inflow.loc[startup.index] * startup 
    return inflow.cumsum()


def simulate_apartment_stock(
        guaranteed_yearly_apartments,
        municipal_apartments_today,
        municipal_yearly_new_apartments,
        municipal_existing_availability_rate,
        municipal_new_availability_rate,
        startup_coefficients,
        years
    ):
    '''
    Creates a dataframe with the total number of apartments that ever entered the social housing system (no matter whether assigned or not)
    '''
    
    municipal = simulate_municipal(
        municipal_apartments_today = municipal_apartments_today,
        municipal_yearly_new_apartments = municipal_yearly_new_apartments,
        municipal_existing_availability_rate = municipal_existing_availability_rate,
        municipal_new_availability_rate = municipal_new_availability_rate,
        startup=startup_coefficients.municipal,
        years=years
    )
    
    guaranteed = simulate_guaranteed(        
        guaranteed_yearly_apartments=guaranteed_yearly_apartments,
        startup=startup_coefficients.guaranteed,
        years=years
    )
       
    apartments = pd.DataFrame({
        'guaranteed':guaranteed,
        'municipal':municipal
    })
    
    return apartments.sort_index(axis=1).astype(int)

