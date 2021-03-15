
GoodPathLen = 5

def goodPathRepr(pathStr, goodPathLen=GoodPathLen):
	if pathStr is None:
		return "<None>"
	if pathStr == "":
		return "<Empty>"
	assert pathStr
	path = pathStr.split("/")
	pathStr = path[-1]
	path = path[:-1]
	while len(path) > 0:
		if len(pathStr) >= goodPathLen: break
		newPathStr = path[-1] + "/" + pathStr
		if len(newPathStr) > goodPathLen: break
		pathStr = newPathStr
		path = path[:-1]
	return pathStr



