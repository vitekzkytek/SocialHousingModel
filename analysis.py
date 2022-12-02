import pandas as pd
from matplotlib import pyplot as plt
import matplotlib.colors as mc
from main import simulate_social_housing
from matplotlib.ticker import FuncFormatter

from main import simulate_social_housing

CUSTOM_COLORS = [tuple(list(mc.to_rgb(c)) + [alpha]) for c in ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'] for alpha in (.5,1)]   
MLN_FORMATTER = FuncFormatter(lambda x, pos: f'{round(x/1000000)} mln. Kč')

def plot_interventions(interventions, title='Počet podpořených domácností v daném roce', ax=None, figsize=(12,6)):
    colmap = {
        'self_help': 'Svépomoc',
        'mop_payment': 'Mimořádná okamžitá pomoc',
        'consulting': 'Poradenství',
        'guaranteed': 'Garantované bydlení',
        'municipal': 'Obecní bydlení',
    }

    df = interventions.groupby('intervention_type',axis=1).sum().rename(columns=colmap)
    
    return df[colmap.values()].plot.bar(stacked=True, title=title, grid=True, figsize=figsize,color=CUSTOM_COLORS[1::2],ax=ax)
    
def plot_hhs(hhs, title='Rozdělení domácností do segmentů', shares = False, ax = None, figsize=(12,6)):
    df = hhs.groupby('hh_status',axis=1).sum()
    
    if shares: 
        df = df.div(df.sum(axis=1),axis=0)
        
    return pd.DataFrame({
        'Bytová nouze':df.queue,
        'Soukromý trh - bez systému': df.self_help,
        'Soukromý trh - měkká opatření': df.consulting + df.mop_payment,
        'V garantovaném bydlení': df.guaranteed,
        'V obecním bydlení': df.municipal,
        'Vyřešeno - bez systému': df.outside_self_help,
        'Vyřešeno - měkká opatření':df.outside_consulting + df.outside_mop_payment,
        'Vyřešeno - garantované bydlení': df.outside_guaranteed,
        'Vyřešeno - obecní bydlení': df.outside_municipal
    }).plot.bar(stacked=True, figsize=figsize, grid=True, title=title,ax=ax, color=CUSTOM_COLORS[1::2] + [CUSTOM_COLORS[2],CUSTOM_COLORS[4],CUSTOM_COLORS[6],CUSTOM_COLORS[8]] );
       
def plot_costs(costs, title='Přímé náklady intervencí sociálního bydlení',ax=None, include_queue_budget=True, include_queue_social=False, figsize=(12,6)):
    
    df = costs.copy()

    if not include_queue_budget:
        df = df.drop('queue_budget',axis=1)
    if not include_queue_social:
        df = df.drop('queue_social',axis=1)
    
    colmap = {
        'apartments_yearly_guaranteed': 'Garantované bydlení - průběžné',
        'apartments_entry_guaranteed': 'Garantované bydlení - vstupní',
        'apartments_yearly_municipal': 'Obecní bydlení - průběžné',
        'apartments_entry_municipal': 'Obecní bydlení - vstupní',
        'consulting': 'Poradenství',
        'mop_payment': 'Mimořádná okamžitá pomoc',
        'social_assistence': 'Sociální asistence',
        'queue_budget': 'Rozpočtové náklady bytové nouze',
        'queue_social': 'Společenské náklady bytové nouze'
    }
    
    
    ax = df.rename(columns=colmap).plot.bar(stacked=True, grid=True, title=title, figsize=None,color=CUSTOM_COLORS[:len(costs.columns)-2] + ['gray','lightgray'],ax=ax)
    ax.yaxis.set_major_formatter(MLN_FORMATTER);
    
    return ax
def simulate_social_housing_to_dict(variant):
    interventions, hhs, returnees, costs, costs_units = simulate_social_housing(**variant)
    return {'interventions':interventions,'hhs':hhs,'returnees':returnees,'costs':costs,'costs_units':costs_units}

def plot_4_variants(variant_1A, variant_1B, variant_2A, variant_2B, plot_function = 'plot_hhs', excel_file = None):
        
    tables_1A = simulate_social_housing_to_dict(variant_1A)
    tables_1B = simulate_social_housing_to_dict(variant_1B)
    tables_2A = simulate_social_housing_to_dict(variant_2A)
    tables_2B = simulate_social_housing_to_dict(variant_2B)

    fig, axs = plt.subplots(nrows=2,ncols=2,figsize=(15, 10), sharex=True, sharey=True)
    
    if plot_function == 'plot_hhs':
        axs[0,0] = plot_hhs(tables_1A['hhs'],ax=axs[0,0],title=variant_1A['title'],figsize=None)
        axs[1,0] = plot_hhs(tables_1B['hhs'],ax=axs[1,0],title=variant_1B['title'],figsize=None)
        axs[0,1] = plot_hhs(tables_2A['hhs'],ax=axs[0,1],title=variant_2A['title'],figsize=None)
        axs[1,1] = plot_hhs(tables_2B['hhs'],ax=axs[1,1],title=variant_2B['title'],figsize=None)

        handles, labels = axs[0,0].get_legend_handles_labels()
        fig.legend(handles, labels, loc='lower center', ncol=5, frameon=False)
        [ax.get_legend().remove() for ax in axs.flatten()]
        fig.suptitle('Rozdělení domácností do segmentů',y=.95)
        #fig.tight_layout()
        return fig, axs
    elif plot_function == 'plot_costs':
        axs[0,0] = plot_costs(tables_1A['costs'], ax=axs[0,0], title=variant_1A['title'], figsize=None, include_queue_budget=True, include_queue_social=False)
        axs[1,0] = plot_costs(tables_1B['costs'], ax=axs[1,0], title=variant_1B['title'], figsize=None, include_queue_budget=True, include_queue_social=False)
        axs[0,1] = plot_costs(tables_2A['costs'], ax=axs[0,1], title=variant_2A['title'], figsize=None, include_queue_budget=True, include_queue_social=False)
        axs[1,1] = plot_costs(tables_2B['costs'], ax=axs[1,1], title=variant_2B['title'], figsize=None, include_queue_budget=True, include_queue_social=False)

        handles, labels = axs[0,0].get_legend_handles_labels()
        fig.legend(handles, labels, loc='lower center', ncol=5, frameon=False)
        [ax.get_legend().remove() for ax in axs.flatten()]
        fig.suptitle('Náklady systému sociálního bydlení',y=.95)
        #fig.tight_layout()
        return fig, axs
    elif plot_function == 'plot_interventions':
        axs[0,0] = plot_interventions(tables_1A['interventions'], ax=axs[0,0], title=variant_1A['title'], figsize=None)
        axs[1,0] = plot_interventions(tables_1B['interventions'], ax=axs[1,0], title=variant_1B['title'], figsize=None)
        axs[0,1] = plot_interventions(tables_2A['interventions'], ax=axs[0,1], title=variant_2A['title'], figsize=None)
        axs[1,1] = plot_interventions(tables_2B['interventions'], ax=axs[1,1], title=variant_2B['title'], figsize=None)

        handles, labels = axs[0,0].get_legend_handles_labels()
        fig.legend(handles, labels, loc='lower center', ncol=5, frameon=False)
        [ax.get_legend().remove() for ax in axs.flatten()]
        fig.suptitle('Provedené intervence',y=.95)
        #fig.tight_layout()
        return fig, axs


def compare_variants(params_1, params_2):
    
    interventions_1, hhs_1, returnees_1, costs_1, costs_units_1 = simulate_social_housing(**params_1)

    interventions_2, hhs_2, returnees_2, costs_2, costs_units_2 = simulate_social_housing(**params_2)
    
    fig, axs = plt.subplots(nrows=3, ncols=2,figsize=(15, 10),sharex=True,sharey=False)
    fig.subplots_adjust(right=0.8)

    # Interventions
    axs[0,0] = plot_interventions(interventions_1, ax=axs[0,0], title=f'{params_1["title"]} - Intervence', figsize=None)
    axs[0,1] = plot_interventions(interventions_2, ax=axs[0,1], title=f'{params_2["title"]} - Intervence', figsize=None)            
    axs[0,0].get_legend().remove()
    axs[0,1].legend(loc='center left', bbox_to_anchor=(1, 0.5))
    
    
    # Hhs
    axs[1,0] = plot_hhs(hhs_1,ax=axs[1,0],title=f'{params_1["title"]} - Domácnosti',figsize=None)
    axs[1,1] = plot_hhs(hhs_2,ax=axs[1,1],title=f'{params_2["title"]} - Domácnosti',figsize=None)
    axs[1,0].get_legend().remove()
    axs[1,1].legend(loc='center left', bbox_to_anchor=(1, 0.5))

    # Costs
    axs[2,0] = plot_costs(costs_1, ax=axs[2,0], title=f'{params_1["title"]} - Náklady', figsize=None, include_queue_budget=True, include_queue_social=False)
    axs[2,1] = plot_costs(costs_2, ax=axs[2,1], title=f'{params_2["title"]} - Náklady', figsize=None, include_queue_budget=True, include_queue_social=False)
    axs[2,0].get_legend().remove()
    axs[2,1].legend(loc='center left', bbox_to_anchor=(1, 0.5))

    return fig, axs

def save_tables_to_excel(variants, excel_file):
    
    tbl_dicts = {
        variant['title']: simulate_social_housing_to_dict(variant) for variant in variants
    }
    
    with pd.ExcelWriter(excel_file) as writer:  
        pd.concat([tbl_dicts[key]['interventions'].assign(variant=key) for key in tbl_dicts]).to_excel(writer, sheet_name='interventions')
        pd.concat([tbl_dicts[key]['returnees'].assign(variant=key) for key in tbl_dicts]).to_excel(writer, sheet_name='returnees')
        pd.concat([tbl_dicts[key]['hhs'].assign(variant=key) for key in tbl_dicts]).to_excel(writer, sheet_name='hhs')
        pd.concat([tbl_dicts[key]['costs'].assign(variant=key) for key in tbl_dicts]).to_excel(writer, sheet_name='costs')
        pd.concat([tbl_dicts[key]['costs_units'].assign(variant=key) for key in tbl_dicts]).to_excel(writer, sheet_name='costs_units')

