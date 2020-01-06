"""
    @f1r3f0x - 25/11/2019
    License: MIT

    Azure DevOps Bypassed PRs:
    Hackish script to get a list with bypassed PRs
"""

# Azure
from msrest.authentication import BasicAuthentication
from msrest import exceptions as MSExceptions
from azure.devops import exceptions as AZExceptions
from azure.devops.v5_1.git import models as AZModels
from azure.devops.released import git as AZGit
from azure.devops.connection import Connection

# Other
from tqdm import tqdm

# Standard library
import logging
import json
import math
from collections import namedtuple


LOGFILE_NAME = 'bypassedPRs'

config_fields = ['access_token', 'organization_url', 'repository_name', 'pull_quantity']
Config = namedtuple('Config', config_fields, defaults=(None,) * len(config_fields))


def setup_logging(logfile_name: str) -> None:
    """
    Setups the script logging to a File and the console simultaneously
    """
    # Setup Logging
    root_logger = logging.getLogger()

    # Log File Config
    file_handler = logging.FileHandler(
        filename=f'{logfile_name}.log',
        mode='w',
        encoding='utf-8'
    )

    file_handler_formatter = logging.Formatter(
        fmt='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        datefmt='%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_handler_formatter)
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.DEBUG)


    # Console Log Config
    console_logger = logging.StreamHandler()
    console_logger.setLevel(logging.INFO)
    console_logger.setFormatter(
        logging.Formatter(
            fmt='%(asctime)s %(name)-12s: %(levelname)-8s %(message)s',
            datefmt='%H:%M:%S'
        )
    )
    root_logger.addHandler(console_logger)
    logging.info('Azure DevOps Bypassed PRs by @f1r3f0x.')


def get_config(file_path: str) -> Config:
    """
    Gets the config file and returns a Config tuple.

    Args:
        file_path (str): Path to config file (json)

    Returns:
        (Config) Config namedtupple.
    """
    try:
        config_file = json.load(open(file_path))
        return Config(
            access_token = config_file['access_token'],
            organization_url = config_file['organization_url'],
            repository_name = config_file['repository_name'],
            pull_quantity = int(config_file['pull_quantity'])

        )
    except FileNotFoundError as err:
        logging.error('Config file not found')
        if input('Do you want to create a new one? (Y/N) ').strip().lower() == 'y':
            config = Config(
                access_token = input('Access Token: '),
                organization_url = input('Organization URL: '),
                repository_name = input('Repository Name: ')
            )
            json.dump({
                'access_token': config.access_token,
                'organization_url': config.organization_url,
                'repository_name': config.repository_name,
                'pull_quantity': DEFAULT_PULL_QUANTITY
            }, open('config.json', 'w'))
            logging.info('Config file created')
            return config
        else:
            logging.info('Closing...')
            quit(1)
    except json.JSONDecodeError as err:
        logging.error('JSON Decoding Error -', str(err))
    except KeyError as err:
        logging.error('Error in JSON Keys:', str(err))
    except ValueError as err:
        logging.error('Pull quantity must be an Int')
    quit(1)


def get_client(org_url: str, access_token: str) -> AZGit.GitClient:
    """
    Connects to our desired Azure DevOps organization and returns a git_client if successfull.

    Args:
        org_url (str): Organization URL
        access_token (str): Organization User Access Token, the user needs to have repository read access.

    Returns:
        GitClient Object
    """
    logging.info('Connecting to Azure DevOps Org...')
    try:
        # Create a connection to the org
        credentials = BasicAuthentication('', access_token)
        connection = Connection(base_url=org_url, creds=credentials)

        # Get git Client
        # See azure.devops.v5_X.git.models for models
        #     azure.devops.git.git_client_base for git_client methods
        git_client = connection.clients.get_git_client()

        return git_client

    except MSExceptions.ClientRequestError as err:
        logging.error('Client Request Error:', str(err))
    except MSExceptions.AuthenticationError as err:
        logging.error('Authentication Error: ', str(err))
    quit(1)


def get_repository(git_client: AZGit.GitClient, target_repo_name: str) ->  AZModels.GitRepository:
    """
    Gets the repository based in the name from the git_client

    Args:
        git_client (GitClient): Git Client object
        target_repo_name (str): Repo Name to obtain
    
    Returns
        GitRepository Object
    """

    repositories = git_client.get_repositories()
    for repo in repositories:
        if repo.name == target_repo_name:
            return repo

    logging.error(f'Repository {target_repo_name} not found.')
    quit(1)


if __name__ == "__main__":
    setup_logging(LOGFILE_NAME)

    config = get_config('my_config.json')
    logging.debug(f'Config file: {config}')

    git_client = get_client(config.organization_url, config.access_token)
    logging.info('Connected!')

    repository = get_repository(git_client, config.repository_name)
    logging.info('Repo obtained!')

    repo_id = repository.id

    search_criteria = AZModels.GitPullRequestSearchCriteria(
        status='Completed',
    )

    logging.info('Scanning PRs...')
    bypassed_prs = []

    loops_qty = math.ceil(config.pull_quantity / 1000) + 1
    for i in range(loops_qty):
        pull_requests = git_client.get_pull_requests(repo_id, search_criteria, top=1000, skip=i*1000)
        pr: AZModels.GitPullRequest
        
        for pr in pull_requests:
            completion_options: AZModels.GitPullRequestCompletionOptions
            completion_options = pr.completion_options
            logging.debug(completion_options)
            
            if completion_options:
                if completion_options.bypass_policy:
                    bypassed_prs.append(f'{pr.pull_request_id} - {pr.completion_options.bypass_reason} - {pr.closed_date}')

    logging.info(f'Found {len(bypassed_prs)} PRs.')
    for pr in bypassed_prs:
        logging.info(pr)

            
    

    logging.info('by @f1r3f0x - https://github.com/F1r3f0x\n')
