import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
import matplotlib.colors as mc
from main import simulate_social_housing
from matplotlib.ticker import FuncFormatter
from matplotlib.ticker import PercentFormatter
from main import simulate_social_housing
COLOR_PALETTE = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
CUSTOM_COLORS = [tuple(list(mc.to_rgb(c)) + [alpha]) for c in COLOR_PALETTE for alpha in (.5,1)]   
MLN_FORMATTER = FuncFormatter(lambda x, pos: f'{round(x/1000000)} mln. Kč')
PCT_FORMATTER = FuncFormatter(lambda x, pos: f'{round(x*100)} %')

def plot_interventions(interventions, title='Počet podpořených domácností v daném roce', ax=None, figsize=(12,6), ylim=None):
    colmap = {
        'self_help': 'Svépomoc',
        'mop_payment': 'Mimořádná okamžitá pomoc',
        'consulting': 'Poradenství',
        'guaranteed': 'Garantované bydlení',
        'municipal': 'Obecní bydlení',
    }

    df = interventions.groupby('intervention_type',axis=1).sum().rename(columns=colmap)
    
    return df[colmap.values()].plot.bar(title=title, grid=True, figsize=figsize,color=CUSTOM_COLORS[1::2],ax=ax, ylim=ylim)
    
def plot_hhs(hhs, title='Rozdělení domácností do segmentů', shares = False, ax = None, figsize=(12,6), ylim=None):
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
    }).plot.bar(stacked=True, figsize=figsize, grid=True, title=title,ax=ax, color=CUSTOM_COLORS[1::2] + [CUSTOM_COLORS[2],CUSTOM_COLORS[4],CUSTOM_COLORS[6],CUSTOM_COLORS[8]], ylim=ylim);
       
def plot_costs(costs, title='Přímé náklady intervencí sociálního bydlení',ax=None, include_queue_budget=True, include_queue_social=False, figsize=(12,6), ylim=None,rot=0):
    
    #df = costs.copy()

    df = pd.DataFrame({
        'Byty s garancí pro majitele': costs.apartments_yearly_guaranteed + costs.apartments_entry_guaranteed,
        'Obecní bydlení pro CS': costs.apartments_yearly_municipal + costs.apartments_entry_municipal,
        'Poradenství': costs.consulting,
        'Vyplacené MOP': costs.mop_payment,
        'Asistence v bydlení': costs.social_assistence,
        'IT systém': costs.IT_system,
        'Náklady na výkon veřejné správy': costs.regional_administration,
        'Rozpočtové náklady bytové nouze':costs.queue_budget,
        'Společenské náklady bytové nouze':costs.queue_social
    })
    
    
    if not include_queue_budget:
        df = df.drop('Rozpočtové náklady bytové nouze',axis=1)
    if not include_queue_social:
        df = df.drop('Společenské náklady bytové nouze',axis=1)
    
    colmap = {
        'apartments_yearly_guaranteed': 'Garantované bydlení - průběžné',
        'apartments_entry_guaranteed': 'Garantované bydlení - vstupní',
        'apartments_yearly_municipal': 'Obecní bydlení - průběžné',
        'apartments_entry_municipal': 'Obecní bydlení - vstupní',
        'consulting': 'Poradenství',
        'mop_payment': 'Mimořádná okamžitá pomoc',
        'social_assistence': 'Sociální asistence',
        'queue_budget': 'Rozpočtové náklady bytové nouze',
        'queue_social': 'Společenské náklady bytové nouze',
        'IT_system':'Náklady na IT systém',
        'regional_administration':'Náklady veřejné správy'
    }
        
    ax = df.plot.bar(stacked=True, grid=True, title=title, figsize=figsize,color=plt.rcParams['axes.prop_cycle'].by_key()['color'][:len(df.columns)-1] + ['gray'],ax=ax,ylim=ylim,rot=rot)
    ax.yaxis.set_major_formatter(MLN_FORMATTER)
    ax.set_xlabel('')
    
    return ax

#def simulate_social_housing(variant):
#    interventions, hhs, returnees, costs, costs_units, costs_discounted = simulate_social_housing(**variant)
#    return {'interventions':interventions,'hhs':hhs,'returnees':returnees,'costs':costs,'costs_units':costs_units, 'costs_discounted':costs_discounted}

def plot_4_variants(tables_1A, tables_1B, tables_2A, tables_2B, plot_function = 'plot_hhs', excel_file = None):       

    fig, axs = plt.subplots(nrows=2,ncols=2,figsize=(15, 10), sharex=True, sharey=True)
    
    if plot_function == 'plot_hhs':
        axs[0,0] = plot_hhs(tables_1A['hhs'],ax=axs[0,0],title=tables_1A['title'],figsize=None)
        axs[1,0] = plot_hhs(tables_1B['hhs'],ax=axs[1,0],title=tables_1B['title'],figsize=None)
        axs[0,1] = plot_hhs(tables_2A['hhs'],ax=axs[0,1],title=tables_2A['title'],figsize=None)
        axs[1,1] = plot_hhs(tables_2B['hhs'],ax=axs[1,1],title=tables_2B['title'],figsize=None)

        handles, labels = axs[0,0].get_legend_handles_labels()
        fig.legend(handles, labels, loc='lower center', ncol=5, frameon=False)
        [ax.get_legend().remove() for ax in axs.flatten()]
        fig.suptitle('Rozdělení domácností do segmentů',y=.95)
        #fig.tight_layout()
        return fig, axs
    elif plot_function == 'plot_costs':
        axs[0,0] = plot_costs(tables_1A['costs'], ax=axs[0,0], title=tables_1A['title'], figsize=None, include_queue_budget=True, include_queue_social=False)
        axs[1,0] = plot_costs(tables_1B['costs'], ax=axs[1,0], title=tables_1B['title'], figsize=None, include_queue_budget=True, include_queue_social=False)
        axs[0,1] = plot_costs(tables_2A['costs'], ax=axs[0,1], title=tables_2A['title'], figsize=None, include_queue_budget=True, include_queue_social=False)
        axs[1,1] = plot_costs(tables_2B['costs'], ax=axs[1,1], title=tables_2B['title'], figsize=None, include_queue_budget=True, include_queue_social=False)

        handles, labels = axs[0,0].get_legend_handles_labels()
        fig.legend(handles, labels, loc='lower center', ncol=5, frameon=False)
        [ax.get_legend().remove() for ax in axs.flatten()]
        fig.suptitle('Náklady systému sociálního bydlení',y=.95)
        #fig.tight_layout()
        return fig, axs
    elif plot_function == 'plot_costs_discounted':
        axs[0,0] = plot_costs(tables_1A['costs_discounted'], ax=axs[0,0], title=tables_1A['title'], figsize=None, include_queue_budget=True, include_queue_social=False)
        axs[1,0] = plot_costs(tables_1B['costs_discounted'], ax=axs[1,0], title=tables_1B['title'], figsize=None, include_queue_budget=True, include_queue_social=False)
        axs[0,1] = plot_costs(tables_2A['costs_discounted'], ax=axs[0,1], title=tables_2A['title'], figsize=None, include_queue_budget=True, include_queue_social=False)
        axs[1,1] = plot_costs(tables_2B['costs_discounted'], ax=axs[1,1], title=tables_2B['title'], figsize=None, include_queue_budget=True, include_queue_social=False)

        handles, labels = axs[0,0].get_legend_handles_labels()
        fig.legend(handles, labels, loc='lower center', ncol=5, frameon=False)
        [ax.get_legend().remove() for ax in axs.flatten()]
        fig.suptitle('Náklady systému sociálního bydlení',y=.95)
        #fig.tight_layout()
        return fig, axs

    elif plot_function == 'plot_interventions':
        axs[0,0] = plot_interventions(tables_1A['interventions'], ax=axs[0,0], title=tables_1A['title'], figsize=None)
        axs[1,0] = plot_interventions(tables_1B['interventions'], ax=axs[1,0], title=tables_1B['title'], figsize=None)
        axs[0,1] = plot_interventions(tables_2A['interventions'], ax=axs[0,1], title=tables_2A['title'], figsize=None)
        axs[1,1] = plot_interventions(tables_2B['interventions'], ax=axs[1,1], title=tables_2B['title'], figsize=None)

        handles, labels = axs[0,0].get_legend_handles_labels()
        fig.legend(handles, labels, loc='lower center', ncol=5, frameon=False)
        [ax.get_legend().remove() for ax in axs.flatten()]
        fig.suptitle('Provedené intervence',y=.95)
        #fig.tight_layout()
        return fig, axs


def compare_variants(output_1, output_2, ylim_costs=(0,5000000000), ylim_interventions=(0, 25000), ylim_hhs=(0,200000),discount_costs=True):
    
    fig, axs = plt.subplots(nrows=3, ncols=2,figsize=(15, 10),sharex=True,sharey=False)
    fig.subplots_adjust(right=0.8)

    # Interventions
    axs[0,0] = plot_interventions(output_1['interventions'], ax=axs[0,0], title=f'{output_1["title"]} - Intervence', figsize=None,ylim=ylim_interventions)
    axs[0,1] = plot_interventions(output_2['interventions'], ax=axs[0,1], title=f'{output_2["title"]} - Intervence', figsize=None,ylim=ylim_interventions)            
    axs[0,0].get_legend().remove()
    axs[0,1].legend(loc='center left', bbox_to_anchor=(1, 0.5))
    
    
    # Hhs
    axs[1,0] = plot_hhs(output_1['hhs'],ax=axs[1,0],title=f'{output_1["title"]} - Domácnosti',figsize=None,ylim=ylim_hhs)
    axs[1,1] = plot_hhs(output_2['hhs'],ax=axs[1,1],title=f'{output_2["title"]} - Domácnosti',figsize=None,ylim=ylim_hhs)
    axs[1,0].get_legend().remove()
    axs[1,1].legend(loc='center left', bbox_to_anchor=(1, 0.5))

    # Costs
    if discount_costs:
        axs[2,0] = plot_costs(output_1['costs_discounted'], ax=axs[2,0], title=f'{output_1["title"]} - Náklady (diskontované)', figsize=None, include_queue_budget=True, include_queue_social=False,ylim=ylim_costs)
        axs[2,1] = plot_costs(output_2['costs_discounted'], ax=axs[2,1], title=f'{output_2["title"]} - Náklady (diskontované)', figsize=None, include_queue_budget=True, include_queue_social=False,ylim=ylim_costs)
    else:
        axs[2,0] = plot_costs(output_1['costs'], ax=axs[2,0], title=f'{output_1["title"]} - Náklady', figsize=None, include_queue_budget=True, include_queue_social=False,ylim=ylim_costs)
        axs[2,1] = plot_costs(output_2['costs'], ax=axs[2,1], title=f'{output_2["title"]} - Náklady', figsize=None, include_queue_budget=True, include_queue_social=False,ylim=ylim_costs)

    axs[2,0].get_legend().remove()
    axs[2,1].legend(loc='center left', bbox_to_anchor=(1, 0.5))

    return fig, axs

def save_tables_to_excel(tbl_dicts, excel_file):
    
    tables = ['interventions','returnees','hhs','costs','costs_units','costs_discounted', 'social_assistence_breakdown']

    with pd.ExcelWriter(excel_file) as writer:  
        for table in tables:
                pd.concat([tbl_dict[table].assign(variant=tbl_dict['title']) for tbl_dict in tbl_dicts]).to_excel(writer, sheet_name=table)
        #pd.concat([tbl_dicts[key]['interventions'].assign(variant=key) for key in tbl_dicts]).to_excel(writer, sheet_name='interventions')
        #pd.concat([tbl_dicts[key]['returnees'].assign(variant=key) for key in tbl_dicts]).to_excel(writer, sheet_name='returnees')
        #pd.concat([tbl_dicts[key]['hhs'].assign(variant=key) for key in tbl_dicts]).to_excel(writer, sheet_name='hhs')
        #pd.concat([tbl_dicts[key]['costs'].assign(variant=key) for key in tbl_dicts]).to_excel(writer, sheet_name='costs')
        #pd.concat([tbl_dicts[key]['costs_units'].assign(variant=key) for key in tbl_dicts]).to_excel(writer, sheet_name='costs_units')
        #pd.concat([tbl_dicts[key]['costs_discounted'].assign(variant=key) for key in tbl_dicts]).to_excel(writer, sheet_name='costs_discounted')


def plot_grouped_stacked(df, title='', y_axis_formatter = None, reverse_alphas=False,ylim=None, color_leg_loc=[0.65, 0.62], alpha_leg_loc=[0.4,0.75]):
    variant_names = list(df.index.get_level_values('varianta').unique())
    col_names = list(df.columns)
    ind_names = list(df.index.get_level_values('rok').unique())
    
    n_df = len(variant_names)
    n_col = len(col_names) 
    n_ind = len(ind_names)
    
    hex_colors = [col['color'] for col in plt.rcParams['axes.prop_cycle']]
    rgb_colors = [tuple(int(col[i:i+2], 16)/255 for i in (1, 3, 5)) for col in hex_colors]

    if n_col == 3:
        alphas = (.33,.66,1.)
    elif n_col == 4:
        alphas = (.25,.5,.75,1.)
    elif n_col == 5:
        alphas = (.2,.4,.6,.8,1.)
    elif n_col == 2:
        alphas = (.5,1.)

    else:
        print('incorrect number of columns, specify alphas first')
        return
    
    if reverse_alphas:
        alphas = alphas[::-1]
        
    fig, axe = plt.subplots(ncols=1,nrows=1,figsize=(20,6))
    
    for order, variant in enumerate(variant_names):
        
        rgb = rgb_colors[order]
        df_var = df.loc[variant]
        
        axe = df_var.plot(
            kind='bar',
            ax=axe,
            stacked=True,
            linewidth=0,
            color = [rgb + (alpha,) for alpha in alphas],
            legend=False,
            grid=True,
            fontsize=15,rot=0,ylim=ylim
        )
    h,l = axe.get_legend_handles_labels() # get the handles we want to modify
    for i in range(0, n_df * n_col, n_col): # len(h) = n_col * n_df
        for j, pa in enumerate(h[i:i+n_col]):
            for rect in pa.patches: # for each index
                rect.set_x(rect.get_x() + 1 / float(n_df + 1) * i / float(n_col))
                #rect.set_hatch(H * int(i / n_col)) #edited part     
                rect.set_width(1 / float(n_df + 1))

    axe.set_xticks((np.arange(0, 2 * n_ind, 2) + 1 / float(n_df + 1)) / 2.)
    axe.set_xticklabels(ind_names, rotation = 0)
    axe.set_xlabel('')
    axe.set_title(title)
    
    if y_axis_formatter:
        axe.yaxis.set_major_formatter(y_axis_formatter)

    # Add invisible data to add variant legend
    n1 = [axe.bar(0, 0, color=rgb_colors[i] ) for i in range(n_df)]
    color_leg = axe.legend(n1, variant_names, loc=color_leg_loc,fontsize=15) 
    
    n2 = [axe.bar(0, 0, color=(0,0,0) + (alphas[i],) ) for i in range(n_col)]
    alpha_leg = axe.legend(n2, list(df.columns), loc=alpha_leg_loc,fontsize=15)

    # Add invisible data to add columns legend
    axe.add_artist(color_leg)
    axe.add_artist(alpha_leg)
    
    return axe



def get_costs_summary(variants, key='costs_discounted'):
    costs = pd.concat([variant[key].assign(varianta=variant['title']) for variant in variants]).reset_index().set_index(['varianta', 'rok'])
    
    soft = costs[['consulting','regional_administration','mop_payment','social_assistence','IT_system']].sum(axis=1)
    housing = costs[['apartments_yearly_guaranteed','apartments_yearly_municipal','apartments_entry_guaranteed','apartments_entry_municipal']].sum(axis=1)
    
    return pd.DataFrame({
        'Náklady měkkých opatření':soft,
        'Náklady zabydlení':housing,
        'Náklady bytové nouze':costs.queue_budget
    })

def plot_costs_summary(variants,title=None, key='costs_discounted'):
    
    summary = get_costs_summary(variants, key)
    return plot_grouped_stacked(summary,title = title,y_axis_formatter=MLN_FORMATTER,ylim=(0,7000000000))


def plot_hhs_in_emergency(variants, title='Počet domácností v bytové nouzi', visualize_risk_structure=False):
    
    def get_hhs_in_emergency(hhs, variant_title):
        return  hhs.assign(varianta=variant_title).rename({'low':'Nízké riziko','high':'Vysoké riziko'},axis=1)
        
    summary = pd.concat([get_hhs_in_emergency(variant['hhs'],variant['title']) for variant in variants]).reset_index().set_index(['varianta', 'rok'])[['guaranteed','municipal','mop_payment','self_help','consulting','queue']]#.sum(axis=1)
    #ax = summary.unstack('varianta').plot.bar(figsize=(20,6),title=title,grid=True,fontsize=15,rot=0)
    if visualize_risk_structure:
        ax = plot_grouped_stacked(summary.stack('hh_risk').sum(axis=1).unstack('hh_risk'),title = title)
        return ax
    else:
        ax = summary.sum(axis=1).unstack('varianta').plot.line(figsize=(20,6),grid=True,ylim=(0,100000),xlabel='',title=title,fontsize=15)
        ax.legend(fontsize=15)
        return ax




def get_intervention_costs(model_output, base_year=2025, costs_type='costs_discounted'):
    df = model_output[costs_type]
    return pd.DataFrame({
        'Byty s garancí pro majitele (náklady na aktuálně podporované byty)': df.apartments_yearly_guaranteed + df.apartments_entry_guaranteed,
        'Obecní byty pro CS (náklady na aktuálně podporované byty)':  df.apartments_yearly_municipal + df.apartments_entry_municipal,
        'Poradenství': df.consulting,
        'Vyplacené MOP': df.mop_payment,
        'Asistence v bydlení': df.social_assistence,
        'IT systém': df.IT_system,
        'Náklady na výkon veřejné správy': df.regional_administration
    })
def plot_interventions_costs(model_output, base_year=2025, costs_type='costs',ax=None,legend=True):
    
    df = get_intervention_costs(model_output, base_year, costs_type)
    
    ax = df.plot.area(
        grid=True,
        figsize=(12,6),
        title=model_output['title'],
        ax=ax,legend=legend
    )
    
    ax.yaxis.set_major_formatter(MLN_FORMATTER)
    return ax
