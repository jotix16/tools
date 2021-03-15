
import socket
from subprocess import Popen, PIPE, STDOUT
import xml.etree.ElementTree as ET
from . import str_
import fcntl
import select
import os
import time
from pipes import quote
import errno


notOnCluster = not socket.gethostname().startswith("cluster-")
if notOnCluster:
	print("Not on cluster, starting qstat on cluster.")



def sshCmd(hostname, cmd):
	return [
		"ssh",
		"-o", "BatchMode=yes",
		"-o", "ConnectTimeout=3",
		"-o", "ServerAliveInterval=2",
		"-o", "StrictHostKeyChecking=no",
		hostname,
		" ".join(map(quote, cmd))]

def clusterCmd(cmd):
	if notOnCluster:
		return sshCmd("cluster-cn-01", cmd)
	return cmd


def parseQstatInfo(out):
	field = None
	for line in out.splitlines():
		if line.startswith("==="): continue
		if not line[0:1].isspace():
			p = line.find(":")
			assert p > 0, "unexpected line: %s" % line
			field = line[:p]
			line = line[p+1:]
		line = line.strip()

		assert field is not None
		yield (field, line)

def collectQstatInfo(out):
	info = {}
	for key, value in parseQstatInfo(out):
		if key in info:
			info[key] += "\n" + value
		else:
			info[key] = value
	return info

qstatInfoCache = {}

def getQstatInfo(jobId):
	if jobId in qstatInfoCache:
		return qstatInfoCache[jobId]
	qcmd = ["qstat", "-j", str(jobId)]
	qcmd = clusterCmd(qcmd)
	out, err = Popen(qcmd, stdout=PIPE, stderr=PIPE).communicate()
	out, err = map(str_.get_str, (out, err))
	if "Following jobs do not exist:" in err:
		# Can happen if job already quit.
		return None
	info = collectQstatInfo(out)
	qstatInfoCache[jobId] = info
	return info

def parseQstatOverviewLine(xmlNode):
	info = {}
	info["id"] = int(xmlNode.find("JB_job_number").text)
	info["name"] = xmlNode.find("JB_name").text
	info["user"] = xmlNode.find("JB_owner").text
	info["state"] = xmlNode.find("state").text
	startTime = xmlNode.find("JAT_start_time")
	if startTime is not None:
		info["date_time"] = startTime.text
	else:
		info["date_time"] = xmlNode.find("JB_submission_time").text
	info["host"] = xmlNode.find("queue_name").text or ""
	info["slots"] = xmlNode.find("slots").text
	tasks = xmlNode.find("tasks")
	if tasks is not None:
		info["tasks"] = tasks.text
	else:
		info["tasks"] = "0"
	return info

def getJobCwd(info):
	if "sge_o_workdir" in info:
		return info["sge_o_workdir"]
	elif "cwd" in info:
		return info["cwd"]
	else:
		return None

def getCurrentJobs(user=None):
	if user is None:
		from .user import LocalUser
		user = LocalUser
	qcmd = ["qstat", "-u", user, "-xml"]
	qcmd = clusterCmd(qcmd)

	xml = Popen(qcmd, stdout=PIPE).stdout.read()
	if not xml.strip():
		return []

	root = ET.fromstring(xml)
	assert root.tag == "job_info"

	jobs = []
	for l in root:
		assert l.tag in ["queue_info", "job_info"]
		for node in l:
			assert node.tag == "job_list"
			info = parseQstatOverviewLine(node)
			jobs += [info]
	return jobs


def getCurrentJobsMoreInfo(user=None):
	jobs = []
	for info in getCurrentJobs(user):
		moreInfo = getQstatInfo(info["id"])
		for k in set(moreInfo or ()).difference(info):
			info[k] = moreInfo[k]
		info["cwd"] = getJobCwd(info)
		jobs += [info]
	return jobs


def _checkReadableStream(stream, timeout):
	while True:
		try:
			readable, writable, exceptional = select.select([stream], [], [stream], timeout)
			return readable
		except EnvironmentError as e:
			if e.errno == errno.EINTR:
				# http://stackoverflow.com/questions/14136195
				# We can just keep trying.
				continue
			raise
		except select.error as e:  # Deprecated, Python 2 and Python <=3.2
			if e.args[0] == errno.EINTR:
				continue
			raise

class CheckException(Exception): pass
class HangingException(CheckException): pass
class TimeoutException(HangingException): pass
class ProcModulesHangingException(HangingException): pass

def checkHangingHost(hostname):
	begin_str, end_str = "__BEGIN", "__END"
	cmd = [
		"/bin/bash", "-c",
		"echo %s && cat /proc/modules && echo %s" % (begin_str, end_str)]
	cmd = sshCmd(hostname, cmd)
	cmd = clusterCmd(cmd)
	proc = Popen(cmd, stderr=STDOUT, stdout=PIPE, stdin=PIPE)
	fl = fcntl.fcntl(proc.stdout, fcntl.F_GETFL)
	fcntl.fcntl(proc.stdout, fcntl.F_SETFL, fl | os.O_NONBLOCK)
	start_time = time.time()
	have_begin = False
	begin_timeout = 10.0
	cat_proc_timeout = 10.0
	out = b""
	while True:
		proc.poll()
		if proc.returncode is not None:
			# Finished. Read remaining data.
			while True:
				readable = _checkReadableStream(proc.stdout, 0.1)
				if not readable: break
				buf = os.read(proc.stdout.fileno(), 1024)
				if not buf: break
				out += buf
		else:
			readable = _checkReadableStream(proc.stdout, 0.1)
			if readable:
				buf = os.read(proc.stdout.fileno(), 1024)
				out += buf
		if not have_begin:
			# Ignore other prefix. Some SSHs will output some welcome msg or so.
			if out.startswith(("%s\n" % begin_str).encode("utf8")) or ("\n%s\n" % begin_str).encode("utf8") in out:
				have_begin = True
				start_time = time.time()
		if proc.returncode is None:  # still running
			if not have_begin:
				if time.time() - start_time > begin_timeout:
					raise TimeoutException("%s: no connection after timeout. output so far: %r" % (hostname, out))
			else:
				if time.time() - start_time > cat_proc_timeout:
					proc.kill()
					raise ProcModulesHangingException(hostname)  # hanging!
		else:
			break
	if not have_begin:
		raise CheckException("%s: did not get prefix output: %r" % (hostname, out))
	if not out.endswith((end_str + "\n").encode("utf8")):
		raise CheckException("%s: unexpected postfix output: %r" % (hostname, out))
	return  # everything ok

