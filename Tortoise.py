import sublime
import sublime_plugin
import os.path
import subprocess
import re
from datetime import datetime
from time import mktime

file_status_cache = {}

def get_timestamp():
	t=datetime.now()
	return int(mktime(t.timetuple())+1e-6*t.microsecond)

def intersect(a, b):
    return bool(set(a) & set(b))

def get_vcs(file):
	settings = sublime.load_settings('Tortoise.sublime-settings')

	if file == None:
		raise NotFoundError('Unable to run commands on an unsaved file')
	vcs = None

	try:
		vcs = TortoiseSVN(settings.get('svn_tortoiseproc_path', None), file)
	except (RepositoryNotFoundError) as (exception):
		pass
	
	try:
		vcs = TortoiseGit(settings.get('git_tortoiseproc_path', None), file)
	except (RepositoryNotFoundError) as (exception):
		pass
	
	try:
		vcs = TortoiseHg(settings.get('hg_hgtk_path', None), file)
	except (RepositoryNotFoundError) as (exception):
		pass

	if vcs == None:
		raise NotFoundError('The current file does not appear to be in an SVN, Git or Mercurial working copy')
	
	return vcs


def handles_not_found(fn):
	def handler(self, *args, **kwargs):
		try:
			fn(self, *args, **kwargs)
		except (NotFoundError) as (exception):
			sublime.error_message('Tortoise: ' + str(exception))
	return handler

def invisible_when_not_found(fn):
	def handler(self, *args, **kwargs):
		try:
			res = fn(self, *args, **kwargs)
			if res != None:
				return res
			return True
		except (NotFoundError) as (exception):
			return False
	return handler

class TortoiseExploreCommand(sublime_plugin.TextCommand):
	@handles_not_found
	def run(self, edit):
		file = self.view.file_name()
		get_vcs(file).explore()


class TortoiseCommitCommand(sublime_plugin.TextCommand):
	@handles_not_found
	def run(self, edit):
		file = self.view.file_name()
		get_vcs(file).commit()


class TortoiseCommitPathCommand(sublime_plugin.WindowCommand):
	@handles_not_found
	def run(self, dirs):
		path = dirs[0]
		get_vcs(path).commit(path=path)
	
	@invisible_when_not_found
	def is_visible(self, **kwargs):
		dirs = kwargs['dirs']
		return len(dirs) > 0 and get_vcs(dirs[0]).get_status(dirs[0]) in ['A', '', 'M', 'R', 'C', 'U']


class TortoiseStatusCommand(sublime_plugin.TextCommand):
	@handles_not_found
	def run(self, edit):
		file = self.view.file_name()
		get_vcs(file).status()


class TortoiseStatusPathCommand(sublime_plugin.WindowCommand):
	@handles_not_found
	def run(self, dirs):
		path = dirs[0]
		get_vcs(path).status(path=path)
	
	@invisible_when_not_found
	def is_visible(self, **kwargs):
		dirs = kwargs['dirs'] if kwargs.has_key('dirs') else []
		return len(dirs) > 0 and get_vcs(dirs[0]).get_status(dirs[0]) in ['A', '', 'M', 'R', 'C', 'U']


class TortoiseSyncCommand(sublime_plugin.TextCommand):
	@handles_not_found
	def run(self, edit):
		file = self.view.file_name()
		get_vcs(file).sync()


class TortoiseSyncPathCommand(sublime_plugin.WindowCommand):
	@handles_not_found
	def run(self, dirs):
		path = dirs[0]
		get_vcs(path).sync(path=path)
	
	@invisible_when_not_found
	def is_visible(self, **kwargs):
		dirs = kwargs['dirs']
		return len(dirs) > 0 and get_vcs(dirs[0]).get_status(dirs[0]) in ['A', '', 'M', 'R', 'C', 'U']


class TortoiseLogCommand(sublime_plugin.TextCommand):
	@handles_not_found
	def run(self, edit):
		file = self.view.file_name()
		get_vcs(file).log()


class TortoiseLogPathCommand(sublime_plugin.WindowCommand):
	@handles_not_found
	def run(self, paths):
		path = paths[0]
		get_vcs(path).log(path=path)
	
	@invisible_when_not_found
	def is_visible(self, **kwargs):
		paths = kwargs['paths']
		return get_vcs(paths[0]).get_status(paths[0]) in ['A', '', 'M', 'R', 'C', 'U']
	
	@invisible_when_not_found
	def is_enabled(self, **kwargs):
		paths = kwargs['paths'] if kwargs.has_key('paths') else []
		return len(paths) > 0 and get_vcs(paths[0]).get_status(paths[0]) in ['', 'M', 'R', 'C', 'U']


class TortoiseLogFileCommand(sublime_plugin.TextCommand):
	@handles_not_found
	def run(self, edit):
		file = self.view.file_name()
		get_vcs(file).log(file)
	
	@invisible_when_not_found
	def is_visible(self):
		file = self.view.file_name()
		vcs = get_vcs(file)
		return vcs.get_status(file) in ['A', '', 'M', 'R', 'C', 'U']
	
	@invisible_when_not_found
	def is_enabled(self):
		file = self.view.file_name()
		vcs = get_vcs(file)
		return vcs.get_status(file) in ['', 'M', 'R', 'C', 'U']


class TortoiseDiffFileCommand(sublime_plugin.TextCommand):
	@handles_not_found
	def run(self, edit):
		file = self.view.file_name()
		get_vcs(file).diff(file)
	
	@invisible_when_not_found
	def is_visible(self):
		file = self.view.file_name()
		return get_vcs(file).get_status(file) in ['A', '', 'M', 'R', 'C', 'U']
	
	@invisible_when_not_found
	def is_enabled(self):
		file = self.view.file_name()
		vcs = get_vcs(file)
		if isinstance(vcs, TortoiseHg):
			return vcs.get_status(file) in ['M']
		else:
			return vcs.get_status(file) in ['A', 'M', 'R', 'C', 'U']


class TortoiseDiffPathCommand(sublime_plugin.WindowCommand):
	@handles_not_found
	def run(self, paths):
		path = paths[0]
		get_vcs(path).diff(path=path)
	
	@invisible_when_not_found
	def is_visible(self, **kwargs):
		paths = kwargs['paths']
		return len(paths) > 0 and get_vcs(paths[0]).get_status(paths[0]) in ['A', '', 'M', 'R', 'C', 'U']
	
	@invisible_when_not_found
	def is_enabled(self, **kwargs):
		paths = kwargs['paths']
		if len(paths) < 1:
			return False
		file = paths[0]
		if os.path.isdir(paths[0]):
			return True
		vcs = get_vcs(file)
		if isinstance(vcs, TortoiseHg):
			return vcs.get_status(file) in ['M']
		else:
			return vcs.get_status(file) in ['A', 'M', 'R', 'C', 'U']


class TortoiseAddFileCommand(sublime_plugin.TextCommand):
	@handles_not_found
	def run(self, edit):
		file = self.view.file_name()
		get_vcs(file).add(file)
	
	@invisible_when_not_found
	def is_visible(self):
		file = self.view.file_name()
		return get_vcs(file).get_status(file) in ['D', '?']


class TortoiseAddPathCommand(sublime_plugin.WindowCommand):
	@handles_not_found
	def run(self, paths):
		path = paths[0]
		get_vcs(path).add(path=path)
	
	@invisible_when_not_found
	def is_visible(self, **kwargs):
		paths = kwargs['paths']
		return get_vcs(paths[0]).get_status(paths[0]) in ['D', '?']


class TortoiseRemoveFileCommand(sublime_plugin.TextCommand):
	@handles_not_found
	def run(self, edit):
		file = self.view.file_name()
		get_vcs(file).remove(file)
	
	@invisible_when_not_found
	def is_visible(self):
		file = self.view.file_name()
		return get_vcs(file).get_status(file) in ['A', '', 'M', 'R', 'C', 'U']
	
	@invisible_when_not_found
	def is_enabled(self):
		file = self.view.file_name()
		return get_vcs(file).get_status(file) in ['']


class TortoiseRemovePathCommand(sublime_plugin.WindowCommand):
	@handles_not_found
	def run(self, paths):
		path = paths[0]
		get_vcs(path).remove(path=path)
	
	@invisible_when_not_found
	def is_visible(self, **kwargs):
		paths = kwargs['paths']
		return get_vcs(paths[0]).get_status(paths[0]) in ['', 'M', 'R', 'C', 'U']
	
	@invisible_when_not_found
	def is_enabled(self, **kwargs):
		paths = kwargs['paths']
		return get_vcs(paths[0]).get_status(paths[0]) in ['']


class TortoiseRevertFileCommand(sublime_plugin.TextCommand):
	@handles_not_found
	def run(self, edit):
		file = self.view.file_name()
		vcs = get_vcs(file)
		vcs.revert(file)
	
	@invisible_when_not_found
	def is_visible(self):
		file = self.view.file_name()
		return get_vcs(file).get_status(file) in ['A', '', 'M', 'R', 'C', 'U']
	
	@invisible_when_not_found
	def is_enabled(self):
		file = self.view.file_name()
		return get_vcs(file).get_status(file) in ['A', 'M', 'R', 'C', 'U']


class TortoiseRevertPathCommand(sublime_plugin.WindowCommand):
	@handles_not_found
	def run(self, paths):
		path = paths[0]
		get_vcs(path).revert(path)
	
	@invisible_when_not_found
	def is_visible(self, **kwargs):
		paths = kwargs['paths']
		return get_vcs(paths[0]).get_status(paths[0]) in ['A', '', 'M', 'R', 'C', 'U']
	
	@invisible_when_not_found
	def is_enabled(self, **kwargs):
		paths = kwargs['paths']
		return os.path.isdir(paths[0]) or get_vcs(paths[0]).get_status(paths[0]) in ['A', 'M', 'R', 'C', 'U']


class TortoiseExploreFileCommand(sublime_plugin.TextCommand):
	@handles_not_found
	def run(self, edit):
		file = self.view.file_name()
		get_vcs(file).explore(file)
		

class ForkGui():
	def __init__(self, *args):
		windowless=False
		if isinstance(args[-1], bool):
			windowless = args[-1]
			args = args[0:-1]
		self.args = args
		self.run(windowless)

	def run(self, windowless):
		startupinfo = None
		if os.name == 'nt' and windowless:
			startupinfo = subprocess.STARTUPINFO()
			startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

		proc = subprocess.Popen(self.args, stdin=subprocess.PIPE,
			stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
			startupinfo=startupinfo)


class Tortoise():
	def find_root(self, name, path):
		slash = '\\' if os.name == 'nt' else '/'
		
		root_dir = None
		last_dir = None
		cur_dir  = path if os.path.isdir(path) else os.path.dirname(path)
		while cur_dir != last_dir:
			if root_dir != None and not os.path.exists(cur_dir + slash + name):
				break
			if os.path.exists(cur_dir + slash + name):
				root_dir = cur_dir
			last_dir = cur_dir
			cur_dir  = os.path.dirname(cur_dir)
		
		if root_dir == None:
			raise RepositoryNotFoundError('Unable to find ' + name + ' directory')
		self.root_dir = root_dir

	def set_binary_path(self, path_suffix, binary_name, setting_name):
		root_drive = os.path.expandvars('%HOMEDRIVE%\\')
		
		possible_dirs = [
			'Program Files\\',
			'Program Files (x86)\\'
		]

		for dir in possible_dirs:
			path = root_drive + dir + path_suffix
			if os.path.exists(path):
				self.path = path
				return
		
		self.path = None
		normal_path = root_drive + possible_dirs[0] + path_suffix
		raise NotFoundError('Unable to find ' + self.__class__.__name__ +
							'.\n\nPlease add the path to ' + binary_name +
							' to the setting "' + setting_name + '" in "' +
							sublime.packages_path() +
							'\\Tortoise\\Tortoise.sublime-settings".\n\n' +
							'Example:\n\n' + '{"' + setting_name + '": r"' +
							normal_path + '"}')
	
	def explore(self, path=None):
		if path == None:
			ForkGui('explorer.exe', self.root_dir)
		else:
			ForkGui('explorer.exe', os.path.dirname(path))
	

class TortoiseProc(Tortoise):
	def status(self, path=None):
		path = self.root_dir if path == None else path
		ForkGui(self.path, '/command:repostatus', '/path:%s' % path)

	def commit(self, path=None):
		path = self.root_dir if path == None else path
		ForkGui(self.path, '/command:commit', '/path:%s' % path)

	def log(self, path=None):
		path = self.root_dir if path == None else path
		ForkGui(self.path, '/command:log', '/path:%s' % path)

	def diff(self, path):
		ForkGui(self.path, '/command:diff', '/path:%s' % path)

	def add(self, path):
		ForkGui(self.path, '/command:add', '/path:%s' % path)

	def remove(self, path):
		ForkGui(self.path, '/command:remove', '/path:%s' % path)

	def revert(self, path):
		ForkGui(self.path, '/command:revert', '/path:%s' % path)


class TortoiseSVN(TortoiseProc):
	def __init__(self, binary_path, file):
		self.find_root('.svn', file)
		if binary_path != None:
			self.path = binary_path
		else:
			self.set_binary_path('TortoiseSVN\\bin\\TortoiseProc.exe',
				'TortoiseProc.exe', 'svn_tortoiseproc_path')

	def sync(self, path=None):
		path = self.root_dir if path == None else path
		ForkGui(self.path, '/command:update', '/path:%s' % path)

	def get_status(self, path):
		global file_status_cache
		if path in file_status_cache and file_status_cache[path]['time'] > get_timestamp() - 10:
			return file_status_cache[path]['status']
		
		svn = SVN()
		file_status_cache[path] = {"time": get_timestamp()}
		status = svn.check_status(path)
		file_status_cache[path]['status'] = status
		return status
	

class TortoiseGit(TortoiseProc):
	def __init__(self, binary_path, file):
		self.find_root('.git', file)
		if binary_path != None:
			self.path = binary_path
		else:
			self.set_binary_path('TortoiseGit\\bin\\TortoiseProc.exe',
				'TortoiseProc.exe', 'git_tortoiseproc_path')
	
	def sync(self, path=None):
		path = self.root_dir if path == None else path
		ForkGui(self.path, '/command:sync', '/path:%s' % path)

	def get_status(self, path):
		global file_status_cache
		if path in file_status_cache and file_status_cache[path]['time'] > get_timestamp() - 10:
			return file_status_cache[path]['status']
		
		git = Git(self.path, self.root_dir)
		file_status_cache[path] = {"time": get_timestamp()}
		try:
			status = git.check_status(path)
		except (Exception) as (exception):
			sublime.error_message(str(exception))
		file_status_cache[path]['status'] = status
		return status
	

class TortoiseHg(Tortoise):
	def __init__(self, binary_path, file):
		self.find_root('.hg', file)
		if binary_path != None:
			self.path = binary_path
		else:
			try:
				self.set_binary_path('TortoiseHg\\hgtk.exe',
					'hgtk.exe', 'hg_hgtk_path')
			except (NotFoundError):
				self.set_binary_path('TortoiseHg\\thg.exe',
					'thg.exe (for TortoiseHg v2.x) or hgtk.exe (for TortoiseHg v1.x)',
					'hg_hgtk_path')
	
	def status(self, path=None):
		if path == None:
			ForkGui(self.path, 'status', '-R', self.root_dir, True)
		else:
			ForkGui(self.path, 'status', '-R', self.root_dir, path + '/*', True)

	def commit(self, path=None):
		if path == None:
			ForkGui(self.path, 'commit', '-R', self.root_dir, True)
		else:
			ForkGui(self.path, 'commit', '-R', self.root_dir, path, True)
	
	def sync(self, path=None):
		if path == None:
			ForkGui(self.path, 'synch', '-R', self.root_dir, True)
		else:
			ForkGui(self.path, 'synch', '-R', self.root_dir, path, True)
	
	def log(self, path=None):
		if path == None:
			ForkGui(self.path, 'log', '-R', self.root_dir, True)
		else:
			ForkGui(self.path, 'log', '-R', self.root_dir, path, True)

	def diff(self, path):
		ForkGui(self.path, 'vdiff', '-R', self.root_dir, path, True)
	
	def add(self, path):
		ForkGui(self.path, 'add', '-R', self.root_dir, path, True)
	
	def remove(self, path):
		ForkGui(self.path, 'remove', '-R', self.root_dir, path, True)
	
	def revert(self, path):
		ForkGui(self.path, 'revert', '-R', self.root_dir, path, True)

	def get_status(self, path):
		global file_status_cache
		if path in file_status_cache and file_status_cache[path]['time'] > get_timestamp() - 10:
			return file_status_cache[path]['status']
		
		hg = Hg(self.path)
		file_status_cache[path] = {"time": get_timestamp()}
		try:
			status = hg.check_status(path)
		except (Exception) as (exception):
			sublime.error_message(str(exception))

		file_status_cache[path]['status'] = status
		return status


class NonInteractiveProcess():
	def __init__(self, args, cwd=None):
		self.args = args
		self.cwd  = cwd


	def run(self):
		startupinfo = None
		if os.name == 'nt':
			startupinfo = subprocess.STARTUPINFO()
			startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

		proc = subprocess.Popen(self.args, stdin=subprocess.PIPE,
			stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
			startupinfo=startupinfo, cwd=self.cwd)
		
		return proc.stdout.read().replace('\r\n', '\n').rstrip(' \n\r')


class SVN():
	def check_status(self, path):
		slash = '\\'

		# Find the path the plugin in installed in
		cur_dir = None
		dirname = sublime.packages_path()
		for f in os.listdir(dirname):
			entry = os.path.join(dirname, f)
			if os.path.isdir(entry):
				if os.path.exists(os.path.join(entry, 'Tortoise.py')):
					cur_dir = entry
		
		svn_path = cur_dir + slash + 'svn' + slash + 'svn.exe'
		proc = NonInteractiveProcess([svn_path, 'status', path])
		result = proc.run().split('\n')
		for line in result:
			if len(line) < 1:
				continue
			
			return line[0]
		return ''


class Git():
	def __init__(self, tortoise_proc_path, root_dir):
		self.git_path = os.path.dirname(tortoise_proc_path) + '\\tgit.exe'
		self.root_dir = root_dir

	def check_status(self, path):
		if os.path.isdir(path):
			proc = NonInteractiveProcess([self.git_path, 'log', '-1', path], cwd=self.root_dir)
			result = proc.run().strip().split('\n')
			if result == ['']:
				return '?'
			return ''
		
		proc = NonInteractiveProcess([self.git_path, 'status', '--short'], cwd=self.root_dir)
		result = proc.run().strip().split('\n')
		for line in result:
			if len(line) < 2:
				continue
			if self.root_dir != path and re.search(re.escape(path.replace(self.root_dir + '\\', '', 1)) + '$', line) == None:
				continue
			return line[1].upper()
		return ''


class Hg():	
	def __init__(self, tortoise_proc_path):
		self.hg_path = os.path.dirname(tortoise_proc_path) + '\\hg.exe'

	def check_status(self, path):
		if os.path.isdir(path):
			proc = NonInteractiveProcess([self.hg_path, 'log', '-l', '1', path])
			result = proc.run().strip().split('\n')
			if result == ['']:
				return '?'
			return ''
		
		proc = NonInteractiveProcess([self.hg_path, 'status', path])
		result = proc.run().split('\n')
		for line in result:
			if len(line) < 1:
				continue
			return line[0].upper()
		return ''


class RepositoryNotFoundError(Exception):
	pass


class NotFoundError(Exception):
	pass