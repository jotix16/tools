

def loginUsername():
	"""
	Returns the username of the current user.
	Use this as a replacement for os.getlogin().
	"""     
	import pwd, os
	return pwd.getpwuid(os.getuid())[0]

LocalUser = loginUsername()


