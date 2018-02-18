import sys
import traceback
import subprocess
from subprocess import CalledProcessError

# logging setup
import logging
from logging import handlers
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        handlers.RotatingFileHandler('updater.log', maxBytes=(1048576*5), backupCount=7)
    ])
log = logging.getLogger(__name__)

# github setup
from github import Github
from config import gh_token, gh_user
github = Github(gh_token)
bounties_repo_name = 'bounties'
bounties_repo = github.get_repo('%s/%s' % (gh_user, bounties_repo_name))

# mongodb setup
import pymongo
from config import mongo_connection_string
client = pymongo.MongoClient(mongo_connection_string)
database = client.github
c_issues = database.issues # index id
c_issue_tips = database.issue_tips # index address
c_pulls = database.pulls # index id
c_variables = database.variables


def ctu(url):
    return url.replace('https://github.com', 'http://github.chaintip.org')

price = c_variables.find_one({})['bch_price']
readme = """# Available Bounties

Bounty | Issue | Repository | Fixing
--- | --- | --- | ---
"""
for issue in bounties_repo.get_issues(state='open'):
    i = c_issues.find_one({'bounties_issue_number': issue.number})
    if i:
        pulls = []
        if 'pulls' in i:
            pulls = c_pulls.find({'id': {'$in': i['pulls']}})
        pulls_string = ''
        for pull in pulls:
            if len(pulls_string) > 0:
                pulls_string += ','
            pulls_string += 'PR [#%s](%s)' % (pull['number'], ctu(pull['url']))

        split = i['repo_full_name'].split('/')
        repo_string = "[%s](%s)" % (split[0], ctu('https://github.com/' + split[0]))
        repo_string += " / "
        repo_string += "[%s](%s)" % (split[1], ctu(i['repo_url']))
        amount_usd = float(i['amount']) * price
        readme += """~ $%7.2f | [[#%s](%s)] %s | %s | %s
""" % (amount_usd, i['number'], ctu(i['url']), i['title'], repo_string, pulls_string)


readme += """
# Collected Bounties

Bounty | Issue | Repository | Fixed By
--- | --- | --- | ---
"""
for issue in bounties_repo.get_issues(state='closed'):
    i = c_issues.find_one({'bounties_issue_number': issue.number})
    if i:
        if 'linked_pull_id' in i:
            pull = c_pulls.find_one({'id': i['linked_pull_id']})
            pull_string = 'PR [#%s](%s)' % (pull['number'], ctu(pull['url']))
            split = i['repo_full_name'].split('/')
            repo_string = "[%s](%s)" % (split[0], ctu('https://github.com/' + split[0]))
            repo_string += " / "
            repo_string += "[%s](%s)" % (split[1], ctu(i['repo_url']))
            amount_usd = float(i['amount']) * price
            readme += """~ $%7.2f | [[#%s](%s)] %s | %s | %s
""" % (amount_usd, i['number'], ctu(i['url']), i['title'], repo_string, pull_string)

with open("README.md", "w") as readme_file:
    print(readme, file = readme_file)

log.info(subprocess.check_output(['git','add', '.']))
try:
    log.info(subprocess.check_output(['git','commit', '-m', 'Auto update']))
except CalledProcessError:
    print('Error commiting')

log.info(subprocess.check_output(['git','push']))