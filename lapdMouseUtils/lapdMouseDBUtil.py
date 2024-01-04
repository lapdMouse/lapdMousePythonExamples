#!/usr/bin/python3
""" lapdMouseDBUtil

lapdMouseDBUtil is a command line tool to list, search, and download files from
the ToxMouse database. For more information about the ToxMouse project and
available data visit the "Lung anatomy + particle deposition (lapd) mouse
archive": https://doi.org/10.25820/9arg-9w56.
"""
__author__ = "Christian Bauer"
__copyright__ = "Copyright 2018 University of Iowa"
__date__ = "2018/02/13"
__license__ = "3-clause BSD license"
__version__ = "1.0.0"

import argparse, json, os, datetime, fnmatch, time, sys, urllib.request, urllib.error
MIN_PYTHON = (3, 6)
if (sys.version_info < MIN_PYTHON):
   sys.exit("Python %s.%s or later is required.\n" % MIN_PYTHON)

remoteFolderUrl = 'https://cebs-ext.niehs.nih.gov/cahs/file/download/lapd/'

class lapdMouseDBUtil():

  def __init__(self, lapdMouseDatabaseUrl=remoteFolderUrl):
    self.gdriveURL = lapdMouseDatabaseUrl

  def _canAccess(self):
    import ssl
    # Create a secure SSL context
    ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    ctx.options |= 0x4  # OP_LEGACY_SERVER_CONNECT

    try:
      httpCode = urllib.request.urlopen(self.gdriveURL+'m01/MD5SUMS',context=ctx).getcode()
      if (httpCode == 200):
        return True
      else:
        print(f"Unexpected HTTP error ({httpCode}.")
        return False
    except urllib.error.HTTPError as e:
      print('The server couldn\'t fulfill the request.')
      print('Error code: ', e.code)
      return False
    except urllib.error.URLError as e:
      print('We failed to reach a server.')
      print('Reason: ', e.reason)
      return False
    except:
      print("Unexpected error:", sys.exc_info()[0])
      return False

  def listDirectory(self, dirname='',depth=0):
    return self._listFolderRemote(dirname, depth)
    
  def downloadFile(self, src, dst=None):
    if dst==None:
        dst=src
    if not os.path.exists(dst):
        if not os.path.exists(os.path.dirname(dst)):
            sos.makedirs(os.path.dirname(dst))
        self._downloadFileFromRemote(src, dst)

  def _downloadFileFromRemote(self, src, destination):
    requestUrl = self.gdriveURL + src
    request = urllib.request.Request(requestUrl)
    response = urllib.request.urlopen(request)
    self._downloadURLStreaming(response, destination)

  def _downloadURLStreaming(self,response,destination):
    if response.getcode() == 200:
      destinationFile = open(destination, "wb")
      bufferSize = 1024*1024
      while True:
        buffer = response.read(bufferSize)
        if not buffer: break
        destinationFile.write(buffer)
      destinationFile.close()

  def _listFolderRemote(self,dirname,depth=0):
    # Read file with file names and metadata
    try:
      with open("allfiles.json") as infile:
        data = infile.read()
      allcontent = json.loads(data)
    except:
      return []

    dircontent = []
    for oneFile in allcontent:
      if (dirname == '.' or os.path.commonprefix([dirname,oneFile['name']]) == dirname):
        remainingPath = oneFile['name'][len(dirname)+1:]
        if (remainingPath.count('/') <= depth):
          dircontent.append(oneFile)
    return dircontent

  def _splitPath(self, p):
    a,b = os.path.split(p)
    return (self._splitPath(a) if len(a) and len(b) else []) + [b]

def humanReadableSize(size):
  if size==None: return ""
  sizeString = "%.1f B"%size
  if (size>pow(1024.0,1)): sizeString="%.1f KB"%(size/pow(1024.0,1))
  if (size>pow(1024.0,2)): sizeString="%.1f MB"%(size/pow(1024.0,2))
  if (size>pow(1024.0,3)): sizeString="%.1f GB"%(size/pow(1024.0,3))
  if (size>pow(1024.0,4)): sizeString="%.1f TB"%(size/pow(1024.0,4))
  return sizeString

def humanReadableTime(seconds):
  return time.strftime("%H:%M:%S", time.gmtime(seconds))

def getStatus(item):
  remoteSize = item['size']
  remoteModificationTime = item['modificationTimestamp']/1000
  realPath = os.path.realpath(os.path.expanduser(item['localName']))
  status = 'require download'
  if os.path.exists(realPath):
    localModificationTime = os.path.getmtime(realPath)
    status = 'downloaded'
    if not item['isFolder']:
      localSize = os.path.getsize(realPath)
      if remoteSize!=localSize or \
        remoteModificationTime>localModificationTime:
        status = 'require update'
  return status

def summarizeItems(items):
  summaryString = ''
  remoteFiles = items
  summaryString += 'Matching files/folders: total='+str(len(remoteFiles))
  if len(remoteFiles)>0: summaryString+='('+humanReadableSize(sum(i['size'] for i in remoteFiles))+')'
  filesAlreadyDownloaded = [i for i in remoteFiles if i['status']=='downloaded']
  summaryString += ', downloaded='+str(len(filesAlreadyDownloaded))
  if len(filesAlreadyDownloaded)>0: summaryString+='('+humanReadableSize(sum(i['size'] for i in filesAlreadyDownloaded))+')'
  filesForDownload = [i for i in remoteFiles if i['status']=='require download']
  summaryString += ', require download='+str(len(filesForDownload))
  if len(filesForDownload)>0: summaryString+='('+humanReadableSize(sum(i['size'] for i in filesForDownload))+')'
  filesOutOfDate = [i for i in remoteFiles if i['status']=='require update']
  summaryString += ', require update='+str(len(filesOutOfDate))
  if len(filesOutOfDate)>0: summaryString+='('+humanReadableSize(sum(i['size'] for i in filesOutOfDate))+')'
  print(summaryString)

def listItem(item):
  remoteName = item['remoteName'] 
  localName = item['localName']
  message = remoteName
  if i['isFolder']:
    message+=' -> '+localName+' (folder)'
  else:
    message+=' -> '+localName+' ('+item['status']+'; '+humanReadableSize(item['size'])+')'
  print(message)

def downloadItem(item, db):
  listItem(item)
  remoteName = item['remoteName']
  localName = item['localName']
  realPath = os.path.realpath(os.path.expanduser(localName))
  isFolder = item['isFolder']
  if os.path.exists(realPath) and os.path.isfile(realPath):
    os.remove(realPath)
  if isFolder and not(os.path.exists(realPath)):
    os.makedirs(realPath)
    return
  if not isFolder and not(os.path.exists(os.path.dirname(realPath))):
    os.makedirs(os.path.dirname(realPath))

  sys.stdout.write('  Downloading ...')
  sys.stdout.flush()
  t0 = time.time()
  try:
    db.downloadFile(remoteName, realPath)
  except:
    print("Unexpected error:", sys.exc_info()[0])
    if os.path.exists(realPath) and os.path.isfile(realPath): os.remove(realPath)
  t1 = time.time()
  downloadSucceeded = os.path.exists(realPath)
  sys.stdout.write( ( '[DONE]' if downloadSucceeded else ' [ERROR]')+' time: '+time.strftime("%M:%S", time.gmtime(t1-t0))+'(mm:ss)\n')
  if not downloadSucceeded:
    return 'ERROR: download failed for file: '+localName
  else:
    return None

def testDBAccess(db):
  serverStatus = 'unknown'
  if lapdMouseDB._canAccess():
    serverStatus = 'available'
  else:
    serverStatus = 'unavailable'
  print('DB access status: '+serverStatus)
  return True if serverStatus=='available' else False

if __name__=="__main__":
  parser = argparse.ArgumentParser(description='lapdMouse database access tool to list, search, and download files.',\
    epilog='lapdMouse project webpage including documentation and support:\n<https://lapdmouse.iibi.uiowa.edu>\nThis work was supported in part by NIH project R01ES023863.',
    formatter_class=argparse.RawTextHelpFormatter)
  parser.add_argument('-p','--pattern', nargs='?', default='*', help='file pattern', type=str)
  parser.add_argument('-l','--localDir', default='.', help='local base directory for download')
  parser.add_argument('-a','--action', choices=['list','download','update','none'], default='list', help='action to perform')
  args = parser.parse_args()
  pattern = args.pattern
  localBaseDir = args.localDir
  action = args.action

  # test server status
  lapdMouseDB = lapdMouseDBUtil()
  if not testDBAccess(lapdMouseDB):
    print('ERROR: Couldn\'t connect to database')
    exit(-1)

  # determine DB query pattern
  root = pattern
  if root.find('*')!=-1: root=root[0:root.find('*')]
  if root.find('?')!=-1: root=root[0:root.find('?')]
  if root.rfind('/')!=-1: root=root[0:root.rfind('/')]
  queryPattern = pattern[len(root)+1:] if len(root)>0 else pattern
  queryRoot = root if len(root)>0 else '.'
  queryDepth = queryPattern.count('/')
  print('DB query: root='+queryRoot+', depth='+str(queryDepth)+', pattern='+queryPattern)

  # query DB and find matches
  items = lapdMouseDB.listDirectory(queryRoot,queryDepth)
  if root == '.':
      matchingItems = [i for i in items if fnmatch.fnmatch(i['name'], queryPattern)]
  else:
      matchingItems = [i for i in items if fnmatch.fnmatch(i['name'], pattern)]

  # determine file status and print summary
  for i in matchingItems:
    i['remoteName'] = i['name'] # if len(root)==0 else root+i['name']
    i['localName'] = os.path.join(localBaseDir, i['remoteName'])
    i['status'] = getStatus(i)
  
  # apply action
  t0 = time.time()
  sizeItemsDownloaded = 0
  nItemsDownloaded = 0
  errors = []
  for i in matchingItems:
    if action=='list':
      listItem(i)
    elif (action=='download' and i['status']=='require download') or\
      (action=='update' and i['status']=='require update'):
      error = downloadItem(i, lapdMouseDB)
      if error:
        errors.append(error)
      else:
        nItemsDownloaded += 1
        sizeItemsDownloaded += i['size'] if i['size'] else 0
  t1 = time.time()

  # provide summary
  if action=='list' or action=='none':
    summarizeItems(matchingItems)
  elif action=='download' or action=='update':
    print('Download statistics: files='+str(nItemsDownloaded)+'('+\
      humanReadableSize(sizeItemsDownloaded)+\
      '), time='+time.strftime("%H:%M:%S", time.gmtime(t1-t0))+'(hh:mm:ss)'+\
      ', speed='+humanReadableSize(sizeItemsDownloaded/(t1-t0))+'/second')
    if len(errors)>0:
      print('Some errors occured: ')
      for e in errors: print(e)
