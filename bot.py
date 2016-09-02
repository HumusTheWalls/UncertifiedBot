import praw
import time
import sys
import os
import regex #Best regex tester for indev package: www.regex101.com

from itertools import tee

import config
 
# No need to be explicit...
from Classes import *

# Temporary workaround while I work out what's causing the:
# sys:1: ResourceWarning: unclosed <ssl.SSLSocket fd=4, family=AddressFamily.AF_INET, type=2049, proto=6, laddr=('10.0.110.122', 46010), raddr=('198.41.208.141', 443)>
# /usr/lib/python3.4/importlib/_bootstrap.py:2127: ImportWarning: sys.meta_path is empty
from warnings import simplefilter
simplefilter("ignore", ResourceWarning)

   #########
  # TO DO #
 #########
# Work out verdicts (always innocent, matches empty?)
# Set up conditionals for charge-based verdicts
# Add regex for Charges
# Work out charge-based verdicts
# Set up recording of invalid cases
# Attempt to send log if error encountered
# Set up Oauth certification
# Add "Manual" checking of certain cases
# Add "Recheck" run through of invalid cases
# Add support for jury-polling
# Flesh out config.py

  ################
 # LATEST ERROR #
################
# Case Exists does not appear to 
# properly identify cases. Duplicates
# cases every run.
# 
# on large cases (3bycnj), bottom comments
# are ignored - verdict found at bottom


# ATTEMPT 1 at verdict
re_verdict = regex.compile(r'(?mi)((?<!or)(?!or)(?:not\sguilty|innocent)|(?<!or)(?!or\s*)(?<!not\s)guilty)')
re_defense = regex.compile(r'(?mi)(?:(?!\A)\G|defen(?:(?:s|c)e|der)).*?\/u\/([a-zA-Z0-9-_]{3,20})')
re_prosecution = regex.compile(r'(?mi)(?:(?!\A)\G|prosecut(?:or|ion)).*?\/u\/([a-zA-Z0-9-_]{3,20})')
re_judge = regex.compile(r'(?mi)(?:(?!\A)\G|ju(?:dge|stice)).*?\/u\/([a-zA-Z0-9-_]{3,20})')
re_jury = regex.compile(r'(?mi)(?:(?!\A)\G|jur(?:y|or)).*?\/u\/([a-zA-Z0-9-_]{3,20})')

# FLAGS
flag_clean = False # used to delete existing data before run
flag_manual = False # used to check a single case --UNIMPLEMENTED--
flag_recheck = False # used to check list of invalid cases --UNIMPLEMENTED--
flag_quick = False # used to run only first [config.batch_size] on top of all
flag_quiet = False # reduces log() output to terminal

log_string = ""
attorney_list = []
case_list = []
invalid_list = []

def run_cycle():
  global attorney_list
  global case_list
  global invalid_list
  log("Running with sub-arguments {}  \n".format(sys.argv[1:]))
  log("Logging in to /u/UncertifiedBot.  \n")
  bot = login()
  log("...logged in.  \n",verbose=False) #Log will attempt to send if error is encountered
  if flag_clean:
    log("...deleting old data.  \n",verbose=False)
    delete_data()
  log("Secreterrifying.  \n")
  case_list = load(config.case_data)
  if case_list:
    log("...loading cases.  \n")
    for case in case_list:
      log("    - "+str(case.report("name"))+"  \n")
      case.certify_attorneys(attorney_list)
  log("...fetching posts  \n")
  posts, post_count = tee(fetch_posts(bot))
  log("ed "+str(gen_len(post_count))+" posts.  \n",char_end=-12,verbose=False)
  for post in posts:
    #Form case name in format: [year]KCC-[month]-[fullname]
    post_date = time.strftime("%D", time.localtime(int(post.created_utc)))
    post_name = "{1}KCC-{2}-{0}".format(post.short_link[15:],post_date[6:],post_date[:2])
    log("   Post [{0}]({1})  \n".format(post_name,post.short_link))
    # If case already in case list, skip case
    if case_exists(post_name, case_list):
      continue
    roster = find_actors_in(post)
    #If no defense/prosecution/judge, case is invalid
    if not (roster[0] and roster[1] and roster[2]):
      log("...invalid case.  \n", char_end=-3) #removes newline and corresponding spaces
      invalid_case = Invalid([post_name])
      #Only display found members
      if roster[0]: #Defense
        invalid_case.set_defense(make_attorneys(roster[0], attorney_list))
        log("    --Defense(s)    : {}  \n".format(roster[0]),verbose=False)
      if roster[1]: #Prosecution
        invalid_case.set_prosecution(make_attorneys(roster[1], attorney_list))
        log("    --Prosecution(s): {}  \n".format(roster[1]),verbose=False)
      if roster[2]: #Judge
        invalid_case.set_judge(make_attorneys(roster[2], attorney_list))
        log("    --Judge(s)      : {}  \n".format(roster[2]),verbose=False)
      if roster[3]: #Jury
        invalid_case.set_jury(make_attorneys(roster[3], attorney_list))
        log("    --Jury          : {}  \n".format(roster[3]),verbose=False)
        #############################
       # Handle Invalid Cases Here #
      #############################
      invalid_list.append(invalid_case)
      continue
    #Valid post --> create case
    # Name must be passed as 1-element list, as per Case.__init__()
    case = Case([post_name])
    # find or create attorney records
    case.set_defense(make_attorneys(roster[0], attorney_list))
    case.set_prosecution(make_attorneys(roster[1], attorney_list))
    case.set_judge(make_attorneys(roster[2], attorney_list))
    case.set_jury(make_attorneys(roster[3], attorney_list))
    log("    --Defense(s)    : {}  \n".format(case.report("defense")),verbose=False)
    log("    --Prosecution(s): {}  \n".format(case.report("prosecution")),verbose=False)
    log("    --Judge(s)      : {}  \n".format(case.report("judge")),verbose=False)
    log("    --Jury          : {}  \n".format(case.report("jury")),verbose=False)
    comments = fetch_comments_from(post)
    #find all statements from the Judge
    judgements = find_statements_from(roster[2], comments)
    log("    Judicial Statements: "+str(len(judgements))+"  \n",verbose=False)
    raw_verdict = find_verdict_in(judgements)
    log("    Verdict: "+("Oops" if raw_verdict is None else "Guilty" if raw_verdict is True else "Innocent")+"  \n",verbose=False)
    if raw_verdict is not None:
      case.resolve(raw_verdict)
      case_list.append(case)
    else:
      invalid_list.append(Invalid(case))
  log("Logging off.  \n")
  log("...writing changes  \n",verbose=False)
  #Save all changes to Lawyer and Case lists
  save(attorney_list, config.attorney_data)
  save(case_list, config.case_data)
  save(invalid_list, config.invalid_data)
  log("...sending logs  \n",verbose=False)
  logout(bot)

def manual_run():
  pass

# Use in conjuction with Invalid Cases
def recheck():
  pass

def delete_data():
  try:
    os.remove(config.attorney_data)
    
  except FileNotFoundError as fnfe:
    pass
  try:
    os.remove(config.case_data)
  except FileNotFoundError as fnfe:
    pass
  try:
    os.remove(config.invalid_data)
  except FileNotFoundError as fnfe:
    pass
  try:
    os.remove(config.log_file)
  except FileNotFoundError as fnfe:
    pass
  return

def login():
  ### Logs into reddit
    # using information from the config file
  bot = praw.Reddit(config.bot_description)
  bot.login(config.UBname, config.UBpass, disable_warning=True)
  return bot

def logout(bot):
  ### Closing script for the bot
    # Clears authentication with
    # reddit ("logs out")
    # And handles reporting the bot's actions
    # to the designated supervisor
  end_time = time.asctime(time.localtime(time.time()))
  bot.clear_authentication()
  # Currently not sending supervisor
  # messages until bot is functional
  #bot.send_message(config.supervisor,"Session: "+end_time, log)
  global log_string
  try:
    with open(config.log_file, "w") as file:
      file.write(log_string)
  except IOError as IOE:
    print ("Error saving log to "+config.log_file+", flushing log to terminal.")

def fetch_posts(bot):
  ### Requests list of posts from reddit
    # Amount of posts based on config
    # Type of sorting will be based on config
    # once I figured out the syntax for the call
  if flag_quick:
    subreddit = bot.get_subreddit("KarmaCourt")
    return subreddit.get_top_from_all(limit=config.batch_size)
  return praw.helpers.submissions_between(bot, "KarmaCourt", newest_first=False, verbosity=1)
  
def case_exists(name, cases):
  for case in cases:
    if name == case.report("name"):
      return True
  return False

# LIterally only used for debugging atm
def gen_len(generator):
  return sum(1 for _ in generator)

def fetch_comments_from(submission):
  ### Returns a flattened tree of comments
    # from given submission object
    # Ignores all comments heavily nested in trees.
    # API calls are WAY too long to wait for on large-scale runs.
    # ...may add optional override later...
  submission.replace_more_comments(limit=0, threshold=0)
  return praw.helpers.flatten_tree(submission.comments)

def find_actors_in(submission):
  ### Produces a list of all involved attorneys
    # based on regular expressions defined above
    # Actor-deficient cases are invalid
    # but that error-handling is external
    # due to plans for extended regex shenannigans
  body = submission.selftext
  #Find all defenses listed in body
  defense = [match.lower() for match in regex.findall(re_defense, body)]
  #Find all prosecutors listed in body
  prosecutor = [match.lower() for match in regex.findall(re_prosecution, body)]
  #Find all judges listed in body
  judge = [match.lower() for match in regex.findall(re_judge, body)]
  #Find all jury members listed in body
  jury = [match.lower() for match in regex.findall(re_jury, body)]
  #Assemble parts
  raw_roster = [defense, prosecutor, judge, jury]
  #Return as much information as was gathered
  return raw_roster

def find_statements_from(actors, stage):
  ### Returns list of comment bodies
    # from given actor
    # Can take a "stage" of a submission
    # due to plans for attorney "highlights"
    # to be implemented later
  #Can take either post or comment list
  if isinstance(stage, praw.objects.Submission):
    stage = fetch_comments_from(stage)
  statements = []
  for actor in actors:
    for statement in stage:
      if statement.author: #More_comment objects have no author
        if statement.author.name.lower() == actor: #actors stored as lower-case
          statements.append(statement)
  #Encode statements to str to prevent unicode errors
  str_statements = []
  for statement in statements:
    str_statements.append(statement.body)
  return str_statements

def make_attorneys(names, attorneys):
  ### Returns list of attorneys
    # based on list of names given
    # Checks for existing record
    # before creating a new attorney
  new_attorneys = []
  # Strings containing names of attorneys
  for name in names:
    newAttorney = None
    # List of Attorney classes
    for attorney in attorneys:
      if name == attorney.report("name"):
        newAttorney = attorney
        break
    if newAttorney is None:
      # Name must be passed as 1-element list, as per Attorney.__init__()
      newAttorney = Attorney([name])
      attorneys.append(newAttorney)
    new_attorneys.append(newAttorney)
  return new_attorneys

def find_verdict_in(judgements):
  ### Returns judge's verdict
    # in the form of a praw.comment
    # based on regex defined above
    # regex matches can be [guilty, not guilty, innocent]
  matches = []
  # Guilt Meter is a temporary measure of
  # overall guiltiness until charge-based
  # verdicts get implemented.
  guilt_meter = 0
  for judgement in judgements:
    raw_matches = regex.findall(re_verdict, judgement)
    for match in raw_matches:
      if match:
        print("Found match: \""+str(match)+"\"")
        matches.append(match)
  for match in matches:
    if match.lower() == "guilty":
      guilt_meter += 1
    if (match.lower() == "not guilty" or
        match.lower() == "innocent"):
      guilt_meter -= 1
  #Innocent until proven guilty
  print("Guilt Meter: "+str(guilt_meter))
  return None if len(matches)==0 else True if guilt_meter>0 else False

def save(saveable_list, filename):
  ### Saves list of saveables
    # to the filename provided
    # Will create file if "filename" does not exist
    # "Saveable" objects return a string
    # when saveable.report("file") is called
  try:
    with open(filename, 'w') as file:
      if saveable_list is not None and len(saveable_list) > 0:
        saveable_list.sort()
        file.write(saveable_list[0].__class__.__name__+"\n")
        for item in saveable_list:
          file.write(item.report("file"))
      else:
        raise IOError() #Hackish: no saveable data to write.
  except IOError as IOE:
    log("Error: "+filename+" could not be saved. No data was recorded.  \n")
  return

def load(filename):
  ### Returns list of loaded
    # saveable objects
    # Determines type of object to load
    # dynamically based on the first line of the file
  loaded = []
  global log
  global attorney_list
  global case_list
  try:
    with open(filename, 'r') as file:
        ################
       # Generic Hack #
      ################
      # Flesh out later
      lines = file.readlines()
      if lines is not None and len(lines) > 1:
        if Case.__name__ in lines[0]:
          for line in lines[1:-1]:
            case_info = line[:-1].split(';')
            for i in range(2,7): # 2-7 are all potential lists separated by ' & '
              case_info[i] = case_info[i].split(' & ')
              case_info[i] = list(filter(None, case_info[i])) # remove empty strings from lists, preserving lists
            try:
              Case.make(case_info, loaded)
            except InitError as ie:
              log += ie.strerror+"  \n"
        elif Invalid.__name__ in lines[0]: # <-- turned this into a class. Still unplanned
          for line in lines[1:]:
            invalid_info = line[:-1].split(';')
            try:
              loaded.append(Invalid.make(invalid_info, invalid_list))
            except InitError as ie:
              log += ie.strerror+"  \n"
        else:
          raise InitError("No valid class to load.")
      else:
        raise InitError("No class type was provided.")
  except (InitError, FileNotFoundError) as oops:
    log("Warning: "+filename+" could not be loaded: "+oops.strerror+"  \n Using empty list instead.  \n")
  return loaded

def log(string, char_begin=0, char_end=0, verbose=True):
  # Function to write changes to log
  # applies changes to log file
  # as well as to console
  global log_string
  global flag_quiet
  if char_begin > 0:
    log_string = log_string[char_begin:]
  if char_end < 0:
    log_string = log_string[:char_end]
  log_string += string
  if flag_quiet and not verbose:
    return
  print(string.rstrip(), flush=True)

if __name__ == "__main__":
  try:
    flag_num = 0
    flags = sys.argv[1:]
    for flag in flags:
      if flag == "clean":
        flag_clean = True
        flag_num += 1
        continue
      if flag == "check":
        flag_manual = True
        flag_num += 1
        continue
      if flag == "retry":
        flag_recheck = True
        flag_num += 1
        continue
      if flag == "quick":
        flag_quick = True
        flag_num += 1
        continue
      if flag == "quiet":
        flag_quiet = True
        flag_num += 1
    if flag_num is len(flags):
      run_cycle()
    else:
      print("Invalid argument[s] passed: "+str(len(flags))+" passed, "+str(flag_num)+" used.")
  except KeyboardInterrupt as e:
    #flush log and exit
    print ("~~~Keyboard Interrupt~~~")
  except: #Always print log for general location in loop exception occurred in.
    raise