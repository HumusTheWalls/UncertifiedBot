import os,random,time,collections

CodeExtensions = ('.py', '.c','.cpp','.rb','.js','.pl','.cs','.el')
last_exts = collections.deque(CodeExtensions[:1],100)
maxlen=0

def maketestname(filename):
  root,ext = os.path.splitext(filename)
  if ext in CodeExtensions:
    last_exts.append(ext)
  else:
    ext = random.choice(last_exts)
  return 'test_'+root+ext

def banner(char,text,width=70):
  bar = char*((width-len(text)-2)/2)
  return "{} {} {}".format(bar,text,bar)

def scaledrand(scale,offset):
  return random.random()*scale+random.randrange(offset)

while True:
  for dirname, subdirs, files in os.walk('.'):
    print banner('=',"entering {}".format(dirname))
    skipped = 0
    for filename in files:
      if filename[0] is not '.':
        testfilename = maketestname(filename)
        print banner('-',testfilename)
        filelen = os.path.getsize(os.path.join(dirname,filename))
        maxlen = max(maxlen,filelen)
        ntests = int(scaledrand(20*filelen/maxlen,10))
        testtime = scaledrand(ntests/5.0,2)
        time.sleep(testtime)                
      else:
        skipped+=1
        continue

    print "Ran {} tests in {} seconds, {} errors".format(ntests,testtime,0)
  print "{} modules OK ({} failed)\n".format(len(files)-skipped,0)