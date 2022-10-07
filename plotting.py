import pandas as pd
from matplotlib import pyplot as plt
from main import simulate_social_housing

def subplot_hhs_stats(flows,hhs_stats,title,ax,cols):
    colnames = {
        'currently_in_municipal': 'v obecních bytech',
        'currently_in_private': 'v soukromých bytech',
        'recent_soft':'jednorázová podpora v tomto roce',
        'recent_self_help':'svépomocí v tomto roce',
        'in_queue':'čekající v bytové nouzi',
        'outside':'mimo systém'
    }
    
    df = hhs_stats.stack(1).sum(axis=1).unstack()[cols].rename(colnames,axis=1)
    return df.plot.bar(stacked=True,figsize=(12,6),grid=True,ax=ax,title=title,legend=False)

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
