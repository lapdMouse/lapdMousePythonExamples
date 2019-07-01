#!/usr/bin/python
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

import argparse, urllib, json, os, datetime, fnmatch, time, sys
if (sys.version_info > (3, 0)): # urllib2 from python 2.x is  urllib.request in pyton 3.x
  import urllib.request as urllib2
  from urllib.parse import urlencode
else:
  import urllib2
  from urllib import urlencode

remoteFolderId = '0B8oknMRvtleaRXFkcGhZaFd0eUU'
class lapdMouseDBUtil():

  def __init__(self, lapdMouseDatabaseFolderId=remoteFolderId):
    self.gdriveRoot = lapdMouseDatabaseFolderId

  def canAccess(self):
    try:
      self._listFolderFromGoogleDrive(self.gdriveRoot,0)
      return True
    except:
      print("Unexpected error:", sys.exc_info()[0])
      return False

  def listDirectory(self, dirname='',depth=0):
    try:
      if dirname=='' or dirname=='.': return self._listFolderFromGoogleDrive(self.gdriveRoot, depth)
      directoryId = self._getResourceId(self.gdriveRoot, dirname)
      if directoryId==None: return None
      return self._listFolderFromGoogleDrive(directoryId, depth)
    except:
      return []

  def downloadFile(self, src, dst=None):
    if dst==None: dst=src
    srcId = self._getResourceId(self.gdriveRoot, src)
    if srcId==None: return None
    if not os.path.exists(os.path.dirname(dst)): os.makedirs(os.path.dirname(dst))
    self._downloadFileFromGoogleDrive(srcId, dst)

  def _downloadFileFromGoogleDrive(self,file_id, destination):
    queryParameters = {"export":"download", "id":file_id}
    queryParameters =  dict((k, v) for k, v in queryParameters.items() if v)
    queryString = "?%s" % urlencode(queryParameters)
    URL = "https://drive.google.com/uc"
    requestUrl = URL + queryString
    request = urllib2.Request(requestUrl)
    response = urllib2.urlopen(request)
    self._downloadURLStreaming(response, destination)
    cookie = response.headers.get('Set-Cookie')
    if os.stat(destination).st_size<10000:
      confirmationURL = self._getConfirmationURL(destination)
      if confirmationURL:
        confirmationURL = 'https://drive.google.com'+confirmationURL.replace('&amp;','&')
        req2 = urllib2.Request(confirmationURL)
        req2.add_header('cookie', cookie)
        response = urllib2.urlopen(req2)
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

  def _getConfirmationURL(self,destination):
    with open(destination) as f:
      for line in f:
        if (sys.version_info >= (3, 0)): line=bytes(line,"utf-8").decode('unicode_escape')
        starttoken='/uc?export=download&amp;'
        start = line.find(starttoken)
        if start!=-1:
          line = line[start:]
          end = line.find('">')
          value = line[0:end]
          return value if (sys.version_info >= (3, 0)) else value.decode('string-escape')
    return None

  def _listFolderFromGoogleDrive(self,folder_id,depth=0):
    URL = "https://drive.google.com/drive/folders/"+folder_id+"?usp=sharing"
    request = urllib2.Request(URL)
    response = urllib2.urlopen(request)
    if response.getcode()!=200:
      print('Error accessing resource')
      return
    jsondata = self._getDriveIvd(response)
    jsondata = json.loads(jsondata)
    dirlist = jsondata[0]
    dircontent = []    
    if dirlist is not None:
      for item in dirlist:
        identifier = item[0]
        name = item[2]
        ftype = item[3]
        fsize = item[13] if item[13] else 0
        creationTimestamp = item[9]
        modificationTimestamp = item[10]
        isFolder = ftype=='application/vnd.google-apps.folder'
        dircontent.append({'name':name, 'id':identifier, 'type': ftype, 'isFolder':isFolder, \
          'size':fsize, 'creationTimestamp':creationTimestamp, 'modificationTimestamp':modificationTimestamp})
        if isFolder and depth>0:
          subdir = self._listFolderFromGoogleDrive(identifier,depth-1)
          if subdir is not None:
            for sub in subdir:
              subname = os.path.join(name, sub['name'])
              dircontent.append({'name':subname, 'id':sub['id'], 'type': sub['type'], 'isFolder':sub['isFolder'], \
                'size':sub['size'], 'creationTimestamp':creationTimestamp, 'modificationTimestamp':modificationTimestamp})
    return dircontent

  def _splitPath(self, p):
    a,b = os.path.split(p)
    return (self._splitPath(a) if len(a) and len(b) else []) + [b]

  def _getResourceId(self, folder_id, relativePath):
    pathParts = self._splitPath(relativePath)
    finalNode = len(pathParts)==1
    currentName = pathParts[0]
    dircontent = self._listFolderFromGoogleDrive(folder_id)
    for d in dircontent:
      if d['name']==currentName:
        if finalNode: return d['id']
        else:
          remainingPath = pathParts[1]
          for p in pathParts[2:]: remainingPath = os.path.join(remainingPath, p)
          return self._getResourceId(d['id'], remainingPath)
    return None

  def _getDriveIvd(self,response):
    for line in response:
      if (sys.version_info >= (3, 0)): line=bytes(line).decode('unicode_escape')
      starttoken="window[\'_DRIVE_ivd\'] = \'"
      start = line.find(starttoken)
      if start!=-1:
        line = line[start+len(starttoken):]
        end = line.find('\'')
        value = line[0:end]
        return value if (sys.version_info >= (3, 0)) else value.decode('string-escape')
    return None

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
        status = 'required update'
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
  filesOutOfDate = [i for i in remoteFiles if i['status']=='required']
  summaryString += ', require update='+str(len(filesOutOfDate))
  if len(filesOutOfDate)>0: summaryString+='('+humanReadableSize(sum(i['size'] for i in filesOutOfDate))+')'
  print(summaryString)

def listItem(item):
  remoteName = item['name'] if len(root)==0 else root+'/'+item['name']
  localName = os.path.join(localBaseDir, remoteName)
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
  if lapdMouseDB.canAccess():
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
  #queryDepth = queryPattern[len(root)+1:].count('/')
  queryDepth = queryPattern.count('/')
  print('DB query: root='+queryRoot+', depth='+str(queryDepth)+', pattern='+queryPattern)

  # query DB and find matches
  items = lapdMouseDB.listDirectory(queryRoot,queryDepth)
  matchingItems = [i for i in items if fnmatch.fnmatch(i['name'], queryPattern)]

  # determine file status and print summary
  for i in matchingItems:
    i['remoteName'] = i['name'] if len(root)==0 else root+'/'+i['name']
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
