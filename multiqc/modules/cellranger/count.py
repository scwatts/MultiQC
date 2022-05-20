#!/usr/bin/env python

""" MultiQC module to parse output from Cellranger count """

import logging
import json
from collections import OrderedDict
from multiqc import config
from multiqc.plots import linegraph, table
from .utils_functions import update_dict, set_hidden_cols, transform_data

# Initialise the logger
log = logging.getLogger(__name__)

class CellRangerCountMixin:
    """Cellranger count report parser"""

    def parse_count_html(self):
        self.cellrangercount_data = dict()
        self.cellrangercount_general_data = dict()
        self.cellrangercount_warnings = dict()
        self.cellrangercount_plots_conf = {'bc': dict(), 'genes': dict()}
        self.cellrangercount_plots_data = {'bc': dict(), 'genes': dict()}
        self.count_general_data_headers = OrderedDict()
        self.count_data_headers = OrderedDict()
        self.count_warnings_headers = OrderedDict()

        for f in self.find_log_files("cellranger/count_html", filehandles=True):
            self.parse_count_report(f)
        
        self.cellrangercount_data = self.ignore_samples(self.cellrangercount_data)
        self.cellrangercount_general_data = self.ignore_samples(self.cellrangercount_general_data)
        self.cellrangercount_warnings = self.ignore_samples(self.cellrangercount_warnings)
        for k in self.cellrangercount_plots_data.keys():
            self.cellrangercount_plots_data[k] = self.ignore_samples(self.cellrangercount_plots_data[k])

        self.count_general_data_headers['COUNT reads'] = {
            'title': 'COUNT {} Reads'.format(config.read_count_prefix),
            'description': 'Number of reads ({})'.format(config.read_count_desc),
            'modify': lambda x: x * config.read_count_multiplier,
        }
        self.count_general_data_headers = set_hidden_cols(
            self.count_general_data_headers, 
            ['COUNT Q30 bc', 'COUNT Q30 UMI', 'COUNT Q30 read']
        )

        self.count_data_headers['reads'] = {
            'title': '{} Reads'.format(config.read_count_prefix),
            'description': 'Number of reads ({})'.format(config.read_count_desc),
            'modify': lambda x: x * config.read_count_multiplier,
        }
        self.count_data_headers = set_hidden_cols(
            self.count_data_headers,
            ['Q30 bc', 'Q30 UMI', 'Q30 read', 
            'confident transcriptome', 'confident intronic', 'confident intergenic', 
            'reads antisense', 'saturation']
        )

        if len(self.cellrangercount_data) == 0:
            raise UserWarning

        self.general_stats_addcols(self.cellrangercount_general_data, self.count_general_data_headers)

        # Write parsed report data to a file
        self.write_data_file(self.cellrangercount_data, "multiqc_cellranger_count")

        #Add sections to the report
        if len(self.cellrangercount_warnings) > 0:
            self.add_section(
                name = 'Count - Warnings',
                anchor = 'cellranger-count-warnings',
                description = 'Warnings encountered during the analysis',
                plot = table.plot(
                    self.cellrangercount_warnings, 
                    self.count_warnings_headers,
                    {'namespace': 'Cellranger Count'}
                )
            )

        self.add_section(
            name = 'Count - Summary stats',
            anchor = 'cellranger-count-stats',
            description = 'Summary QC metrics from Cellranger count',
            plot = table.plot(
                self.cellrangercount_data, 
                self.count_data_headers,
                {'namespace': 'Cellranger Count'}
            )
        )

        self.add_section(
            name = 'Count - BC rank plot',
            anchor = 'cellranger-count-bcrank-plot',
            description = self.cellrangercount_plots_conf['bc']['description'],
            helptext = self.cellrangercount_plots_conf['bc']['helptext'],
            plot = linegraph.plot(self.cellrangercount_plots_data['bc'], self.cellrangercount_plots_conf['bc']['config'])
        )

        self.add_section(
            name = 'Count - Median genes',
            anchor = 'cellranger-count-genes-plot',
            description = self.cellrangercount_plots_conf['genes']['description'],
            helptext = self.cellrangercount_plots_conf['genes']['helptext'],
            plot = linegraph.plot(self.cellrangercount_plots_data['genes'], self.cellrangercount_plots_conf['genes']['config'])
        )

        return len(self.cellrangercount_general_data)

    def parse_count_report(self, f):
        """Go through the html report of cellranger and extract the data in a dics"""
  
        for line in f['f']:
            line = line.strip()
            if line.startswith('const data'):
                line = line.replace('const data = ', '')
                mydict = json.loads(line)
                mydict = mydict['summary']
                break
        
        s_name = mydict['sample']['id']
        data = dict()
        data_general_stats = dict()

        #Store general stats from cells and sequencing tables 
        col_dict = {
            'Estimated Number of Cells': 'estimated cells',
            'Mean Reads per Cell': 'avg reads/cell',
            'Fraction Reads in Cells': 'reads in cells'
        }
        data_general_stats, self.count_general_data_headers = update_dict(
            data_general_stats, self.count_general_data_headers, 
            mydict['summary_tab']['cells']['table']['rows'], 
            col_dict, "COUNT")

        col_dict = {
            'Number of Reads': 'reads',
            'Valid Barcodes': 'valid bc',
            'Q30 Bases in Barcode': 'Q30 bc',
            'Q30 Bases in UMI': 'Q30 UMI',
            'Q30 Bases in RNA Read': 'Q30 read'
        }
        data_general_stats, self.count_general_data_headers = update_dict(
            data_general_stats, self.count_general_data_headers, 
            mydict['summary_tab']['sequencing']['table']['rows'], 
            col_dict, "COUNT")
        
        #Store full data from cellranger count report
        data_rows = mydict['summary_tab']['sequencing']['table']['rows'] + \
            mydict['summary_tab']['cells']['table']['rows'] + \
                mydict['summary_tab']['mapping']['table']['rows']
        col_dict = {
            'Number of Reads': 'reads',
            'Estimated Number of Cells': 'estimated cells',
            'Mean Reads per Cell': 'avg reads/cell',
            'Total Genes Detected': 'genes detected',
            'Median Genes per Cell': 'median genes/cell',
            'Fraction Reads in Cells': 'reads in cells',
            'Valid Barcodes': 'valid bc',
            'Valid UMIs': 'valid umi',
            'Median UMI Counts per Cell': 'median umi/cell',
            'Sequencing Saturation': 'saturation',
            'Q30 Bases in Barcode': 'Q30 bc',
            'Q30 Bases in UMI': 'Q30 UMI',
            'Q30 Bases in RNA Read': 'Q30 read',
            'Reads Mapped to Genome': 'reads mapped',
            'Reads Mapped Confidently to Genome': 'confident reads',
            'Reads Mapped Confidently to Transcriptome': 'confident transcriptome',
            'Reads Mapped Confidently to Exonic Regions': 'confident exonic',
            'Reads Mapped Confidently to Intronic Regions': 'confident intronic',
            'Reads Mapped Confidently to Intergenic Regions': 'confident intergenic',
            'Reads Mapped Antisense to Gene': 'reads antisense'
        }
        data, self.count_data_headers = update_dict(
            data_general_stats, self.count_data_headers, 
            data_rows, 
            col_dict)
        
        # Extract warnings if any
        warnings = dict()
        alarms_list = mydict['alarms'].get('alarms', [])
        for alarm in alarms_list:
            warnings[alarm['id']] = "FAIL"
            self.count_warnings_headers[alarm['id']] = {
                'title': alarm['id'],
                'description': alarm['title'],
                'bgcols': {'FAIL': '#f06807'}
            }

        # Extract data for plots
        help_dict = {x[0]: x[1][0] for x in mydict['summary_tab']['cells']['help']['data']}
        plots = {
            'bc': {
                'config': {
                    'id': 'mqc_cellranger_count_bc_knee',
                    'title': f"Cellranger count: {mydict['summary_tab']['cells']['barcode_knee_plot']['layout']['title']}",
                    'xlab': mydict['summary_tab']['cells']['barcode_knee_plot']['layout']['xaxis']['title'],
                    'ylab': mydict['summary_tab']['cells']['barcode_knee_plot']['layout']['yaxis']['title'],
                    'yLog': True,
                    'xLog': True
                    },
                'description': 'Barcode knee plot',
                'helptext': help_dict['Barcode Rank Plot']
            },
            'genes': {
                'config': {
                    'id': 'mqc_cellranger_count_genesXcell',
                    'title': f"Cellranger count: {mydict['analysis_tab']['median_gene_plot']['help']['title']}",
                    'xlab': mydict['analysis_tab']['median_gene_plot']['plot']['layout']['xaxis']['title'],
                    'ylab': mydict['analysis_tab']['median_gene_plot']['plot']['layout']['yaxis']['title'],
                    'yLog': False,
                    'xLog': False
                    },
                'description': 'Median gene counts per cell',
                'helptext': mydict['analysis_tab']['median_gene_plot']['help']['helpText']
            }
        }
        plots_data = {
            'bc': transform_data(mydict['summary_tab']['cells']['barcode_knee_plot']['data'][0]),
            'genes': transform_data(mydict['analysis_tab']['median_gene_plot']['plot']['data'][0])
        }

        if len(data) > 0:
            if s_name in self.cellrangercount_general_data:
                log.debug("Duplicate sample name found in {}! Overwriting: {}".format(f["fn"], s_name))
            self.add_data_source(f, s_name, module="cellranger", section="count")
            self.cellrangercount_data[s_name] = data
            self.cellrangercount_general_data[s_name] = data_general_stats
            if len(warnings) > 0: self.cellrangercount_warnings[s_name] = warnings
            self.cellrangercount_plots_conf = plots
            for k in plots_data.keys():
                self.cellrangercount_plots_data[k][s_name] = plots_data[k]