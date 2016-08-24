import praw
import time
import sys
import os
import regex #Best regex tester for indev package: www.regex101.com

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
# Traceback (most recent call last):
#  File "bot.py", line 349, in <module>
#    run_cycle()
#  File "bot.py", line 65, in run_cycle
#    case.certify_attorneys(attorney_list)
#  File "/home/humusthewalls/UncertifiedBot/Classes.py", line 110, in certify_attorneys
#    attorneys.remove(attorney.name) #attorney already exists
#AttributeError: 'filter' object has no attribute 'remove'


# ATTEMPT 1 at verdict
re_verdict = regex.compile(r'((?<!or)(?!or)(?:not\sguilty|innocent)|(?<!or)(?!or\s*)(?<!not\s)guilty)')
re_defense = regex.compile(r'(?mi)(?:(?!\A)\G|defen(?:(?:s|c)e|der)).*?\/u\/(\w{3,20})')
re_prosecution = regex.compile(r'(?mi)(?:(?!\A)\G|prosecut(?:or|ion)).*?\/u\/(\w{3,20})')
re_judge = regex.compile(r'(?mi)(?:(?!\A)\G|ju(?:dge|stice)).*?\/u\/(\w{3,20})')
re_jury = regex.compile(r'(?mi)(?:(?!\A)\G|jur(?:y|or)).*?\/u\/(\w{3,20})')

log = ""
attorney_list = []
case_list = []
invalid_list = []

def run_cycle():
  global log
  global attorney_list
  global case_list
  global invalid_list
  log += "Running with sub-arguments {}  \n".format(sys.argv[1:])
  log += "Logging in to /u/UncertifiedBot.  \n"
  bot = login()
  log += "...logged in.  \n" #Log will attempt to send if error is encountered
  log += "Secreterrifying.  \n"
  case_list = load(config.case_data)
  if case_list:
    for case in case_list:
      case.certify_attorneys(attorney_list)
  log += "...fetching posts  \n"
  posts = fetch_posts(bot)
  for post in posts:
    #Form case name in format: [year]KCC-[month]-[fullname]
    post_date = time.strftime("%D", time.localtime(int(post.created_utc)))
    post_name = "{1}KCC-{2}-{0}".format(post.short_link[15:],post_date[6:],post_date[:2])
    log += "   Post [{0}]({1})  \n".format(post_name,post.short_link)
    # If case already in case list, skip case
    if case_exists(post_name, case_list):
      continue
    roster = find_actors_in(post)
    #If no defense/prosecution/judge, case is invalid
    if not (roster[0] and roster[1] and roster[2]):
      log = log[:-3] #removes newline and corresponding spaces
      log += "...invalid case.  \n"
      #Only display found members
      if roster[0]: #Defense
        log += "    --Defense(s)    : {}  \n".format(roster[0])
      if roster[1]: #Prosecution
        log += "    --Prosecution(s): {}  \n".format(roster[1])
      if roster[2]: #Judge
        log += "    --Judge(s)      : {}  \n".format(roster[2])
      if roster[3]: #Jury
        log += "    --Jury          : {}  \n".format(roster[3])
      continue
        #############################
       # Handle Invalid Cases Here #
      #############################
    #Valid post --> create case
    case = None
    # Name must be passed as 1-element list, as per Case.__init__()
    case = Case([post_name])
    case_list.append(case)
    # find or create attorney records
    log += ("    "+post_name+" is not alone.  \n" if len(case.defense)>0 else "")
    case.set_defense(make_attorneys(roster[0], attorney_list))
    case.set_prosecution(make_attorneys(roster[1], attorney_list))
    case.set_judge(make_attorneys(roster[2], attorney_list))
    case.set_jury(make_attorneys(roster[3], attorney_list))
    log += "    --Defense(s)    : {}  \n".format(case.report("defense"))
    log += "    --Prosecution(s): {}  \n".format(case.report("prosecution"))
    log += "    --Judge(s)      : {}  \n".format(case.report("judge"))
    log += "    --Jury          : {}  \n".format(case.report("jury"))
    comments = fetch_comments_from(post)
    log += "    Comments:  \n"
    #find all statements from the Judge
    judgements = find_statements_from(roster[2], comments)
    raw_verdict = find_verdict_in(judgements)
    log += "    Verdict: "+str(raw_verdict)+"  \n"
    case.resolve(True if raw_verdict is "Guilty" else False if raw_verdict is "Innocent" else None)
  log += "Logging off.  \n"
  log += "...writing changes  \n"
  #Save all changes to Lawyer and Case lists
  save(attorney_list, config.attorney_data)
  save(case_list, config.case_data)
  save(invalid_list, config.invalid_data)
  log += "...sending logs  \n"
  logout(bot)
  log = ""

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
  global log
  end_time = time.asctime(time.localtime(time.time()))
  bot.clear_authentication()
  # Currently not sending supervisor
  # messages until bot is functional
  #bot.send_message(config.supervisor,"Session: "+end_time, log)
  try:
    with open(config.log_file, "w") as file:
      file.write(log)
  except IOError as IOE:
    print ("Error saving log to "+config.log_file+", flushing log to terminal.")
    print (log)

def fetch_posts(bot):
  ### Requests list of posts from reddit
    # Amount of posts based on config
    # Type of sorting will be based on config
    # once I figured out the syntax for the call
  subreddit = bot.get_subreddit("KarmaCourt")
  return subreddit.get_top_from_all(limit=config.batch_size)
  
def case_exists(name, cases):
  for case in cases:
    if name is case.report("name"):
      return True
  return False

def fetch_comments_from(submission):
  ### Returns a flattened tree of comments
    # from given submission object
    # Ignores all comments heavily nested in trees.
    # API calls are WAY too long to wait for on large-scale runs.
    # ...may add optional override later...
  submission.replace_more_comments(limit=0)
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
  for name in names:
    newAttorney = None
    for attorney in attorneys:
      if name is attorney.name:
        newAttorney = attorney
        break
    if newAttorney is None:
      # Name must be passed as 1-element list, as per Attorney.__init__()
      newAttorney = Attorney([name])
    new_attorneys.append(newAttorney)
  return new_attorneys

def find_verdict_in(judgements):
  ### Returns judge's verdict
    # in the form of a praw.comment
    # based on regex defined above
    # regex matches can be [guilty, not guilty, innocent]
  matches = []
  guilt_meter = 0
  for judgement in judgements:
    raw_matches = regex.findall(re_verdict, judgement)
    for match in raw_matches:
      if match:
        matches.append(match)
  for match in matches:
    if match.lower() is "guilty":
      guilt_meter += 1
      print ("<223>: Guilty")
    if match.lower() is "not guilty":
      guilt_meter -= 1
      print ("<223>: Not Guilty")
    if match.lower() is "innocent":
      guilt_meter -= 1
      print ("<223>: Innocent")
  #Innocent until proven guilty
  return "Oops" if len(matches)==0 else "Guilty" if guilt_meter>0 else "Innocent"

def save(saveable_list, filename):
  ### Saves list of saveables
    # to the filename provided
    # Will create file if "filename" does not exist
    # "Saveable" objects return a string
    # when saveable.report("file") is called
  try:
    with open(filename, 'w') as file:
      if saveable_list is not None and len(saveable_list) > 0:
        file.write(saveable_list[0].__class__.__name__+"\n")
        for item in saveable_list:
          file.write(item.report("file"))
      else:
        raise IOError() #Hackish: no saveable data to write.
  except IOError as IOE:
    global log
    log += "Error: "+filename+" could not be saved. No data was recorded.  \n"
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
    log += "Warning: "+filename+" could not be loaded: "+oops.strerror+"  \n Using empty list instead.  \n"
  for case in loaded:
    print(case.report("file"))
  return loaded

if __name__ == "__main__":
  try:
    if len(sys.argv) is 1:
      run_cycle()
    elif sys.argv[1] == "delete":
      delete_data()
      run_cycle()
    elif sys.argv[1] is "check":
      manual_run()
    elif sys.argv[1] is "retry":
      recheck()
    else:
      print ("\""+sys.argv[1]+"\" is not a valid argument.")
  except KeyboardInterrupt as e:
    #flush log and exit
    print (log)
    print ("~~~Keyboard Interrupt~~~")
  except: #Always print log for general location in loop exception occurred in.
    print (log)
    raise