class Case:
  
  @staticmethod
  def make(data, case_list):
    ### Class Creation Method
      # data must be a list of correct size for initialization
      # as defined by __init__. No error checking here.
      # Throws InitError if any error occurs.
      # Returns initialized class reference.
    try:
      case_list.append(Case(data))
    except NameError as ne:
      # Raise new error to give better description of issue
      raise InitError("Case was not created: "+ne.strerror)
  
  def __init__(self, *name, verdict=None, charges=[],jury=[], defense=[], prosecution=[], judge=[]):
    ### Case initialization
      # Cases need a minimum of a name to be initialized
      # but all members can be passed for loading of
      # a pre-existing case.
      # Note: Initializations will either be Case("name") or Case(*all)
      # Piecemeal initializations should not occur
    if type(name) is list:
      self.name = name[0]
      self.verdict = name[1] if len(name) > 1 else verdict
      self.charges = name[2] if len(name) > 2 else charges
      self.jury = name[3] if len(name) > 3 else jury
      self.defense = name[4] if len(name) > 4 else defense
      self.prosecution = name[5] if len(name) > 5 else prosecution
      self.judge = name[6] if len(name) > 6 else judge
    else:
      self.name = str(name)
      self.verdict = verdict
      self.charges = charges
      self.jury = jury
      self.defense = defense
      self.prosecution = prosecution
      self.judge = judge
  
  def resolve(self, verdict):
    ### Processes the verdict of the case forcefully by
      # editting each participating attorney's case record
      # to include itself. Attorneys store their win/loss records,
      # but do not have control over them internally.
    if not verdict: #invalid resolution, do not process
      return
    self.verdict = verdict
    for defender in self.defense:
      defender.loses.append(self.name) if verdict else defender.wins.append(self.name)
    for prosecutor in self.prosecution:
      prosecutor.wins.append(self.name) if verdict else prosecutor.loses.append(self.name)
    for judger in self.judge:
      judger.judgements.append(self.name)
    for juror in self.jury:
      juror.jury_duty.append(self.name)
    return
  
  def set_defense(self, attorneys):
    ### Takes list of Attorneys
      # involved with case defense
      # and stores names in
      # the case record
    for attorney in attorneys:
      if attorney.__class__.__name__ is not "Attorney":
        raise NameError("Attorney given has not passed the BAR.")
      self.defense.append(attorney.name)
  
  def set_prosecution(self, attorneys):
    ### Takes list of Attorneys
      # involved with case prosecution
      # and stores names in
      # the case record
    for attorney in attorneys:
      if attorney.__class__.__name__ is not "Attorney":
        raise NameError("Attorney given has not passed the BAR.")
      self.prosecution.append(attorney.name)
  
  def set_judge(self, attorneys):
    ### Takes list of Attorneys
      # involved with case judgement
      # and stores names in
      # the case record
    for attorney in attorneys:
      if attorney.__class__.__name__ is not "Attorney":
        raise NameError("Attorney given has not passed the BAR.")
      self.judge.append(attorney.name)
  
  def set_jury(self, attorneys):
    ### Takes list of Attorneys
      # involved with case jury
      # and stores names in
      # the case record
    for attorney in attorneys:
      if attorney.__class__.__name__ is not "Attorney":
        raise NameError("Attorney given has not passed the BAR.")
      self.jury.append(attorney.name)
  
  def certify_attorneys(self, archived_attorneys):
    ### Takes all attorneys present at this case
      # and ensures their record is archived
      # Archived attorneys are stored
      # in the attorney_data file from config
      # Main purpose of this function
      # is for file-loaded cases
    attorneys = []
    attorneys.extend(self.defense)
    attorneys.extend(self.prosecution)
    attorneys.extend(self.judge)
    attorneys.extend(self.jury)
    
    for attorney in archived_attorneys:
      if attorney.name in attorneys:
        attorneys.remove(attorney.name) #attorney already exists
    for name in attorneys:
      Attorney.make((name), archived_attorneys)
  
  def report(self, type="name"):
    ### Returns information about the case
      # depending on the requested type
      # Mainly used to report the case name or
      # the full "file" report
    string = ""
    #NAME
    if type is "name":
      string += self.name
      return string
    #VERDICT
    if type is "verdict":
      string += str(self.verdict)
      return string
    #CHARGES
    if type is "charges":
      for charge in self.charges:
        string += charge.replace('&',';').replace(';',' ')+" & " #charges are full sentences with possible '&' and ';'
      if self.charges:
        string = string[:-3]
      return string
    #DEFENSE
    if type is "defense":
      for defender in self.defense:
        string += defender+" & "
      if self.defense:
        string = string[:-3]
      return string
    #PROSECUTION
    if type is "prosecution":
      for prosecutor in self.prosecution:
        string += prosecutor+" & "
      if self.prosecution:
        string = string[:-3]
      return string
    #JUDGE
    if type is "judge":
      for judger in self.judge:
        string += judger+" & "
      if self.judge:
        string = string[:-3]
      return string
    #JURY
    if type is "jury":
      for juror in self.jury:
        string += juror+" & "
      if self.jury:
        string = string[:-3]
      return string
    #FILE
    if type is "file":
      string += self.report("name")+";"
      string += self.report("verdict")+";"
      string += self.report("charges")+";"
      string += self.report("jury")+";"
      string += self.report("defense")+";"
      string += self.report("prosecution")+";"
      string += self.report("judge")+"\n"
      return string

class Invalid(Case):
  
  @staticmethod
  def make(data, invalid_list):
    ### Class Creation Method
      # data must be a list of correct size for initialization
      # as defined by __init__. No error checking here.
      # Throws InitError if any error occurs.
      # Returns initialized class reference.
    pass
  
  def __init__(self, name):
    Case.__init__(self, name)

  def resolve(self, verdict):
    pass
  
  def certify_attorneys(self, archived_attorneys):
    pass
  
  def report(self, type="name"):
    return self.name

class Attorney:
  
  @staticmethod
  def make(data, attorney_list):
    ### Class Creation Method
      # data must be a list of correct size for initialization
      # as defined by __init__. No error checking here.
      # Throws InitError if any error occurs.
      # Returns initialized class reference.
    try:
      attorney_list.append(Attorney(data))
    except NameError as ne:
      # Raise new error to give better description of issue
      raise InitError("Attorney was not created: "+ne.strerror)

  def __init__(self, *stats):
    ### Attorney initialization
      # Requires a valid name at a minimum
      # Handled differently than Case initialization
      # because attorneys can have special notes or
      # records or stats that may not be uniform
      # among all attorneys. Cases will always be uniform.
    if not stats[0] or type(stats[0]) is not str:
      raise NameError("No valid name passed: "+str(stats[0]))
    self.name = stats[0]
    # Following stats are lists of strings (or at least should be)
    self.wins = stats[1] if len(stats) > 1 else []
    self.loses = stats[2] if len(stats) > 2 else []
    self.judgements = stats[3] if len(stats) > 3 else []
    self.jury_duty = stats[4] if len(stats) > 4 else []
  
  def report(self, type="name"):
    ### Reports information about attorney
      # depending on the type requested
      # Error handling is very primitive.
    if type is "name":
      return self.name
    if type is "wins":
      return str(self.wins)[1:-1]
    if type is "loses":
      return str(self.loses)[1:-1]
    if type is "judgements":
      return str(self.judgements)[1:-1]
    if type is "jury":
      return str(self.jury_duty)[1:-1]
    if type is "file":
      return "%s;%s;%s;%s;%s\n" % (self.report("name"),self.report("wins"),self.report("loses"),self.report("judgements"),self.report("jury"))
    else:
      return "OMG AN ERROR KILL IT WITH FIRE!!!"


#
  #############################
 # Uncertifed Error Handling #
#############################

class UncertifiedError(Exception):
  def __init__(self, string = "An Uncertified Error has occurred!"):
    self.strerror = string

class NameError(UncertifiedError):
  pass

class InitError(UncertifiedError):
  pass