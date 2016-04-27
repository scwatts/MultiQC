#!/usr/bin/env python

""" MultiQC functions to plot a beeswarm group """

import json
import logging
import os
import random

from multiqc.utils import config
from multiqc.plots import table_object

logger = logging.getLogger(__name__)

letters = 'abcdefghijklmnopqrstuvwxyz'

def plot (data, headers=[], pconfig={}):
    """ Helper HTML for a beeswarm plot.
    :param data: A list of data dicts
    :param headers: A list of Dicts / OrderedDicts with information
                    for the series, such as colour scales, min and
                    max values etc.
    :return: HTML string
    """
    
    # Make a datatable object
    dt = table_object.datatable(data, headers, pconfig)
    
    return make_beeswarm_plot( dt )
    
    
def make_plot(dt):    
    categories = []
    s_names = []
    data = []
    for idx, hs in enumerate(dt.headers):
        for k, header in hs.items():
            
            rid = header['rid']
            bcol = 'rgb({})'.format(header.get('colour', '204,204,204'))

            categories.append({
                'namespace': header['namespace'],
                'title': header['title'],
                'description': header['description'],
                'max': header['dmax'],
                'min': header['dmin'],
                'suffix': header.get('suffix', ''),
                'decimalPlaces': header.get('decimalPlaces', '2'),
                'bordercol': bcol
            });
            
            # Add the data
            thisdata = []
            these_snames = []
            for (s_name, samp) in dt.data[idx].items():
                if k in samp:
                    
                    val = samp[k]
                    
                    if 'modify' in header and callable(header['modify']):
                        val = header['modify'](val)
                    
                    thisdata.append(val)
                    these_snames.append(s_name)
            
            data.append(thisdata)
            s_names.append(these_snames)
    
    # Plot and javascript function
    html = """<div class="hc-plot-wrapper"><div id="general_stats_beeswarm" class="hc-plot not_rendered hc-beeswarm-plot"><small>loading..</small></div></div>
    <script type="text/javascript">
        mqc_plots["general_stats_beeswarm"] = {{
            "plot_type": "beeswarm",
            "samples": {s},
            "datasets": {d},
            "categories": {c}
        }}
    </script>""".format(s=json.dumps(s_names), d=json.dumps(data), c=json.dumps(categories))
    
    return html
    
    