import os
import sys
import subprocess
import argparse
from datetime import datetime
import shutil
import time
import glob

import generate_templates as gt
from rsmas_logging import RsmasLogger, loglevel
from dataset_template import Template
import download_ssara_rsmas as ssara_rsmas
import _process_utilities as putils

OPERATIONS_DIRECTORY = os.getenv('OPERATIONS')
STORED_DATE_FILE = OPERATIONS_DIRECTORY + "/stored_date.date"
TEMPLATE_DIRECTORY = OPERATIONS_DIRECTORY + "/TEMPLATES"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"

def create_process_rsmas_parser():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                     description="""Submits processing jobs for each datasest template present in the 
                                     $OPERATIONS/TEMPLATES/ directory.  \nPlace run_operations_LSF.job file into 
                                     $OPERATIONS directory and submit with bsub < run_operations_LSF.job. \nIt runs 
                                     run_operations.py once daily at 12:00 PM.""")

    parser.add_argument('-v', '--version', action='version', version='%(prog)s 0.1')

    data_args = parser.add_argument_group("Dataset and Template Files", "Dataset and Template Files")
    data_args.add_argument('-dataset', dest='dataset', metavar="DATASET", help='Particular dataset to run')
    data_args.add_argument('-templatecsv', dest='template_csv', metavar='FILE', help='local csv file containing template info.')
    data_args.add_argument('-singletemplate', dest='single_template', metavar='FILE', help='singular template file to run on')
    data_args.add_argument('--sheet_id', dest="sheet_id", metavar='SHEET ID', help='sheet id to use')
    data_args.add_argument('--restart', dest='restart', action='store_true', help='remove $OPERATIONS directory before starting')

    process_args = parser.add_argument_group("Processing steps", "processing Steps")
    process_args.add_argument('--startssara', dest='startssara', action='store_true', help='process_rsmas.py --startssara')
    process_args.add_argument('--stopssara', dest='stopssara', action='store_true', help='stop after downloading')
    process_args.add_argument('--startprocess', dest='startprocess', action='store_true', help='process using sentinelstack package')
    process_args.add_argument('--stopprocess', dest='stopprocess', action='store_true', help='stop after processing')
    process_args.add_argument('--startpysar', dest='startpysar', action='store_true', help='run pysar')
    process_args.add_argument('--stoppysarload', dest='stoppysarload', action='store_true', help='stop after loading into pysar')
    process_args.add_argument('--stoppysar', dest='stoppysar', action='store_true', help='stop after pysar processing')
    process_args.add_argument('--startinsarmaps', dest='startinsarmaps', action='store_true', help='ingest into insarmaps')

    return parser


def command_line_parse(args):

    parser = create_process_rsmas_parser()
    inps = parser.parse_args(args)

    return inps


def initiate_operations():

    operations_directory = os.getenv('OPERATIONS')
    templates_directory = operations_directory + "/TEMPLATES/"
    logs_directory = operations_directory + "/LOGS/"
    errors_directory = operations_directory + "/ERRORS/"

    if not os.path.isdir(operations_directory):
        os.mkdir(operations_directory)
    if not os.path.isdir(templates_directory):
        os.mkdir(templates_directory)
    if not os.path.isdir(logs_directory):
        os.mkdir(logs_directory)
        open(logs_directory + '/generate_templates.log', 'a').close()  # create empty file
    if not os.path.isdir(errors_directory):
        os.mkdir(errors_directory)
    if not os.path.exists(os.getenv('OPERATIONS') + '/stored_date.date'):
        open(os.getenv('OPERATIONS') + '/stored_date.date', 'a').close()  # create empty file


def generate_templates_with_options(inps):

    template_options = []
    if inps.template_csv:
        template_options.append('--csv')
        template_options.append(inps.template_csv)
    if inps.dataset:
        template_options.append('--dataset')
        template_options.append(inps.dataset)
    if inps.sheet_id:
        template_options.append('--sheet_id')
        template_options.append(inps.sheet_id)

    gt.main(template_options)


def get_datasets_to_process(dataset=None):

    # Obtains list of datasets to run processSentinel on
    if dataset:
        datasets = [dataset]
    else:
        template_files = glob.glob("{}/*.template".format(TEMPLATE_DIRECTORY))
        datasets = [putils.get_project_name(template) for template in template_files]

    return datasets

def get_newest_data_date(dset):

    template_file = "{}/{}.template".format(TEMPLATE_DIRECTORY, dset)

    dset_template = Template(template_file)
    ssaraopt_string = dset_template.generate_ssaraopt_string()

    ssaraopt_cmd = 'ssara_federated_query.py {} --print'.format(ssaraopt_string)

    ssara_output = subprocess.check_output(ssaraopt_cmd)

    newest_data = ssara_output.split("\n")[-2]
    date = datetime.strptime(newest_data.split(",")[3], DATE_FORMAT)

    return date

def get_last_downloaded_date(dset):

    dataset_line = ""
    with open(STORED_DATE_FILE) as date_file:
        for line in date_file.readlines():
            if dset in line:
                dataset_line = line
                break

    last_date = dataset_line.split(": ")[1]

    return datetime.strptime(last_date, DATE_FORMAT)

def run_operations(args):

    inps = command_line_parse(args)

    # Remove and reinitiate $OPERATIONS directory
    if inps.restart:
        shutil.rmtree(os.getenv('OPERATIONS'))
        initiate_operations()

    generate_templates_with_options(inps)
    datasets = get_datasets_to_process(inps.dataset)

    for dset in datasets:

        newest_date = get_newest_data_date(dset)
        last_date = get_last_downloaded_date(dset)





if __name__ == "__main__":

    run_operations()