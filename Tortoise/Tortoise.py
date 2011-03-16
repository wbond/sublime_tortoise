import sublime
import sublime_plugin
import os.path
import subprocess

class TortoiseCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		self.handle_error('The tortoise command does nothing. Please use tortoise_commit, tortoise_explore, tortoise_sync, tortoise_status, tortoise_log, tortoise_add_file, tortoise_delete_file, tortoise_diff_file, tortoise_explore_file or tortoise_log_file.')

	def get_vcs(self, file):
		settings = sublime.load_settings('Tortoise.sublime-settings')

		try:
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

		except (NotFoundError) as (exception):
			sublime.error_message('Tortoise: ' + str(exception))
			raise NotFoundError(str(exception))

def silenced(fn):
	def silencer(self, edit):
		try:
			fn(self, edit)
		except (NotFoundError):
			pass
	return silencer

class TortoiseExploreCommand(TortoiseCommand):
	@silenced
	def run(self, edit):
		file = self.view.file_name()
		self.get_vcs(file).explore()


class TortoiseCommitCommand(TortoiseCommand):
	@silenced
	def run(self, edit):
		file = self.view.file_name()
		self.get_vcs(file).commit()


class TortoiseStatusCommand(TortoiseCommand):
	@silenced
	def run(self, edit):
		file = self.view.file_name()
		self.get_vcs(file).status()


class TortoiseSyncCommand(TortoiseCommand):
	@silenced
	def run(self, edit):
		file = self.view.file_name()
		self.get_vcs(file).sync()


class TortoiseLogCommand(TortoiseCommand):
	@silenced
	def run(self, edit):
		file = self.view.file_name()
		self.get_vcs(file).log()


class TortoiseLogFileCommand(TortoiseCommand):
	@silenced
	def run(self, edit):
		file = self.view.file_name()
		self.get_vcs(file).log(file)


class TortoiseDiffFileCommand(TortoiseCommand):
	@silenced
	def run(self, edit):
		file = self.view.file_name()
		self.get_vcs(file).diff(file)


class TortoiseAddFileCommand(TortoiseCommand):
	@silenced
	def run(self, edit):
		file = self.view.file_name()
		self.get_vcs(file).add(file)


class TortoiseRemoveFileCommand(TortoiseCommand):
	@silenced
	def run(self, edit):
		file = self.view.file_name()
		self.get_vcs(file).remove(file)


class TortoiseExploreFileCommand(TortoiseCommand):
	@silenced
	def run(self, edit):
		file = self.view.file_name()
		self.get_vcs(file).explore(file)
		

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
		cur_dir  = os.path.dirname(path)
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
	def status(self):
		ForkGui(self.path, '/command:repostatus', '/path:%s' % self.root_dir)

	def commit(self):
		ForkGui(self.path, '/command:commit', '/path:%s' % self.root_dir)

	def log(self, path=None):
		path = self.root_dir if path == None else path
		ForkGui(self.path, '/command:log', '/path:%s' % path)

	def diff(self, path):
		ForkGui(self.path, '/command:diff', '/path:%s' % path)

	def add(self, path):
		ForkGui(self.path, '/command:add', '/path:%s' % path)

	def remove(self, path):
		ForkGui(self.path, '/command:remove', '/path:%s' % path)


class TortoiseSVN(TortoiseProc):
	def __init__(self, binary_path, file):
		self.find_root('.svn', file)
		if binary_path != None:
			self.binary_path = binary_path
		else:
			self.set_binary_path('TortoiseSVN\\bin\\TortoiseProc.exe',
				'TortoiseProc.exe', 'svn_tortoiseproc_path')

	def sync(self):
		ForkGui(self.path, '/command:update', '/path:%s' % self.root_dir)
	

class TortoiseGit(TortoiseProc):
	def __init__(self, binary_path, file):
		self.find_root('.git', file)
		if binary_path != None:
			self.binary_path = binary_path
		else:
			self.set_binary_path('TortoiseGit\\bin\\TortoiseProc.exe',
				'TortoiseProc.exe', 'git_tortoiseproc_path')
	
	def sync(self):
		ForkGui(self.path, '/command:sync', '/path:%s' % self.root_dir)
	

class TortoiseHg(Tortoise):
	def __init__(self, binary_path, file):
		self.find_root('.hg', file)
		if binary_path != None:
			self.binary_path = binary_path
		else:
			self.set_binary_path('TortoiseHg\\hgtk.exe',
				'hgtk.exe', 'hg_hgtk_path')
	
	def status(self):
		ForkGui(self.path, 'status', '-R', self.root_dir, True)

	def commit(self):
		ForkGui(self.path, 'commit', '-R', self.root_dir, True)
	
	def sync(self):
		ForkGui(self.path, 'synch', '-R', self.root_dir, True)
	
	def log(self, path=None):
		if path == None:
			ForkGui(self.path, 'log', '-R', self.root_dir, True)
		else:
			ForkGui(self.path, 'log', path, '-R', self.root_dir, True)

	def diff(self, path):
		ForkGui(self.path, 'vdiff', path, '-R', self.root_dir, True)
	
	def add(self, path):
		ForkGui(self.path, 'add', '-R', self.root_dir, path, True)
	
	def remove(self, path):
		ForkGui(self.path, 'remove', '-R', self.root_dir, path, True)


class RepositoryNotFoundError(Exception):
	pass


class NotFoundError(Exception):
	pass