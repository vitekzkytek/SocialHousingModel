import pandas as pd
import numpy as np

def simulate_private(
        private_yearly_apartments: int,
        years: np.ndarray
    ) -> pd.Series:
    '''
    Simulates total number of private apartments available in the social housing system.
    
    Based on simple parameter *private_yearly_apartments* which constitues the number of apartments per year entering the system.
    
    Returns: pd.Series with the total number of private apartments that ever entered the social housing system.
    '''
    
    return pd.Series({yr:private_yearly_apartments for yr in years}).cumsum()
    
def simulate_municipal(
        municipal_apartments_today: int,
        municipal_yearly_new_apartments: int,
        municipal_existing_availability_rate: float,
        municipal_new_availability_rate: float,
        years: np.ndarray
) -> pd.Series:
    '''
    Simulates total number of municipal apartments available in the social housing system.
    
    The municipal apartments are derived from two sources:
     1. *existing stock of municipal aparments*: from which a share (municipal_existing_availability_rate) is released each year to the stock. The existing stock starts at *municipal_apartments_today* and is gradually increased
     2. *new municipal apartment*: Each year *municipal_yearly_new_apartments*  are built from which a share (*municipal_new_availability_rate*) is put into the system.

    Returns: pd.Series with the total number of municipal apartments that ever entered the social housing system.
    '''
    
    apartment_stock = pd.Series({yr: municipal_apartments_today + municipal_yearly_new_apartments*(yr-1) for yr in years})
    return (apartment_stock.shift(1,fill_value=apartment_stock.iloc[0]) * municipal_existing_availability_rate + municipal_yearly_new_apartments * municipal_new_availability_rate).cumsum()


def simulate_apartment_stock(
        private_yearly_apartments,
        municipal_apartments_today,
        municipal_yearly_new_apartments,
        municipal_existing_availability_rate,
        municipal_new_availability_rate,
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
        years=years
    )
    
    private = simulate_private(        
        private_yearly_apartments=private_yearly_apartments,
        years=years
    )
    apartments = pd.DataFrame({
        ('private','entry_cumsum'):private,
        ('municipal','entry_cumsum'):municipal
    })
        
    return apartments.sort_index(axis=1).astype(int)

