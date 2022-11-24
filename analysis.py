import pandas as pd
from matplotlib import pyplot as plt
import matplotlib.colors as mc
from main import simulate_social_housing
from matplotlib.ticker import FuncFormatter

from main import simulate_social_housing

CUSTOM_COLORS = [tuple(list(mc.to_rgb(c)) + [alpha]) for c in ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'] for alpha in (.5,1)]   
MLN_FORMATTER = FuncFormatter(lambda x, pos: f'{round(x/1000000)} mln. Kč')

def plot_basic_interventions(interventions, title='Počet podpořených domácností v daném roce', ax=None):
    return interventions.unstack(['intervention_type','hh_risk']).plot.bar(stacked=True, title=title, grid=True, figsize=(12,6),color=CUSTOM_COLORS,ax=ax)
    
def plot_basic_hhs(hhs, title='Počet domácností v systému (nebere v potaz navrátilce)', ax=None):
    return hhs.plot.bar(stacked=True, figsize=(12,6),grid=True,color=CUSTOM_COLORS, title=title,ax=ax);

def plot_basic_returnees(returnees,title='Počet navrátilců v daném roce', ax=None):
    return returnees.plot.bar(stacked=True, grid=True, figsize=(12,6),title=title,color=CUSTOM_COLORS,ax=ax);
        
def plot_basic_costs(costs, title='Přímé náklady intervencí sociálního bydlení',ax=None):
    ax = costs[[col for col in costs.columns if 'costs' in col]].plot.bar(stacked=True, grid=True, title=title, figsize=(12,6),color=CUSTOM_COLORS,ax=ax)
    ax.yaxis.set_major_formatter(MLN_FORMATTER);
    
    return ax


def compute_variants(params_1, params_2, label_1 = 'variant 1', label_2 = 'variant 2',plot_function='plot_basic_costs'):
    
    interventions_1, hhs_1, returnees_1, costs_1 = simulate_social_housing(**params_1)

    interventions_2, hhs_2, returnees_2, costs_2 = simulate_social_housing(**params_2)
    
    
    fig, axs = plt.subplots(nrows=2,ncols=1,figsize=(15,15),sharex=True,sharey=True)
    
    if plot_function == 'plot_basic_costs':
        axs[0] = plot_basic_costs(costs_1,ax=axs[0],title=label_1)
        axs[1] = plot_basic_costs(costs_2,ax=axs[1],title=label_2)
        
        handles, labels = axs[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc=(0,-0.01), ncol=4, frameon=False)
        [ax.get_legend().remove() for ax in axs]
        fig.tight_layout()
        return fig, axs
    elif plot_function == 'plot_basic_interventions':
        axs[0] = plot_basic_interventions(interventions_1,ax=axs[0],title=label_1)
        axs[1] = plot_basic_interventions(interventions_2,ax=axs[1],title=label_2)
        
        handles, labels = axs[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc=(0,-0.01), ncol=5, frameon=False)
        [ax.get_legend().remove() for ax in axs]
    
        fig.tight_layout()
        return fig, axs
    elif plot_function == 'plot_basic_hhs':
        axs[0] = plot_basic_costs(costs_1,ax=axs[0],title=label_1)
        axs[1] = plot_basic_costs(costs_2,ax=axs[1],title=label_2)
        
        handles, labels = axs[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc=(0,-0.01), ncol=4, frameon=False)
        [ax.get_legend().remove() for ax in axs]
        fig.tight_layout()
        return fig, axs

    else:
        'unknown plot function'
        return




def plot_single_param_variation(varied_param, variations, title_blueprint, suptitle, default_params, plot_outside = False):
    cols = ['currently_in_municipal','currently_in_private','recent_soft','recent_self_help','in_queue']
    
    if plot_outside:
        cols = ['outside'] + cols
        
    fig, axs = plt.subplots(nrows=len(variations), ncols=1, figsize=(len(variations)*5,9))
    config = {key:default_params[key] for key in default_params if key != varied_param}        
    
    for i, param in enumerate(variations):
        config[varied_param] = param
        flows, hhs_stats = simulate_social_housing(**config)
        title = title_blueprint.format(**{varied_param:param*100}) if f'{{{varied_param}}}%' in title_blueprint else title_blueprint.format(**{varied_param:param})
        axs[i] = subplot_hhs_stats(flows, hhs_stats, title, axs[i], cols)
    fig.suptitle(suptitle)
    handles, labels = axs[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc=(0.1,0),ncol=len(cols),frameon=False)
    fig.tight_layout()
    return fig

def plot_two_param_variation(first_param, first_variations, second_param, second_variations, title_blueprint, suptitle, default_params, plot_outside = False):
    cols = ['currently_in_municipal','currently_in_private','recent_soft','recent_self_help','in_queue']
    
    if plot_outside:
        cols = ['outside'] + cols
    
    fig, axs = plt.subplots(nrows=len(first_variations), ncols=len(second_variations), figsize=(len(first_variations)*5,9/len(second_variations)),sharex=True,sharey=True)
    config = {key:default_params[key] for key in default_params if key not in (first_param, second_param)}

    for i, first_variation in enumerate(first_variations):
        config[first_param] = first_variation
        for j, second_variation in enumerate(second_variations):
            config[second_param] = second_variation

            flows, hhs_stats = simulate_social_housing(**config)
            title = title_blueprint.format(**{
                first_param: first_variation*100 if f'{{{first_param}}}%' in title_blueprint else first_variation, 
                second_param: second_variation*100 if f'{{{second_param}}}%' in title_blueprint else second_variation,                 
            })
            axs[i,j] = subplot_hhs_stats(flows, hhs_stats, title, axs[i,j], cols)
    fig.suptitle(suptitle)
    handles, labels = axs[0,0].get_legend_handles_labels()
    fig.legend(handles, labels, loc=(0.1,0),ncol=len(cols),frameon=False)
    fig.tight_layout()
    return fig
