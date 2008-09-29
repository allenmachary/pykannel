#!/usr/bin/env python
# vim:tabstop=4:noexpandtab

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import cgi, urlparse, urllib, re


class SmsReceiver():
	class RequestHandler(BaseHTTPRequestHandler):
		def do_GET(self):
			try:
				# all responses from this handler are pretty much the
				# same - an http status and message - so let's abstract it!
				def respond(code, message=None):
					self.send_response(code)
					self.end_headers()
				
					# recycle the full HTTP status message if none were provided
					if message is None: message = self.responses[code][0]
					self.wfile.write(message)
			
			
				# explode the URI to pluck out the
				# query string as a dictionary
				parts = urlparse.urlsplit(self.path)
				vars = cgi.parse_qs(parts[3])
			
			
				# if this event is valid, then thank kannel, and
				# invoke the receiver function with the sms data
				if vars.has_key("callerid") and vars.has_key("message"):
					caller = re.compile('\D').sub("", vars["callerid"][0])
					self.server.receiver(caller, vars["message"][0])
					respond(200, "SMS Received OK")
			
				# the request wasn't valid :(
				else: respond(400)
			
			# something went wrong during the
			# request (probably within the receiver),
			# so cause an internal server error
			except:
				respond(500)
				raise
		
		
		# we don't need to see every request in the console, since the
		# app will probably log it anyway. note: errors are still shown!
		def log_request(self, code="-", size="-"):
			pass
	
	
	def __init__(self, receiver, port=4500):
		handler = self.RequestHandler
		self.serv = HTTPServer(("", port), handler)
		self.serv.receiver = receiver
	
	def run(self):
		self.serv.serve_forever()


class SmsSender():
	def __init__(self, username, password, server="localhost", port=13013):
		self.un = username
		self.pw = password
		self.server = server
		self.port = port
	
	def send(self, dest, message):

		# strip any junk from the destination -- the exact
		# characters allowed vary wildy between installations
		# and networks, so we'll play it safe here
		dest = re.compile('\D').sub("", dest)
		
		# urlencode to make special chars
		# safe to embed in the kannel url
		msg_enc = urllib.quote(message)
		
		# send the sms to kannel via a very
		# unpleasent-looking HTTP GET request
		# (which is a flagrant violation of the
		# HTTP spec - this should be POST!)
		res = urllib.urlopen(
			"http://%s:%d/cgi-bin/sendsms?username=%s&password=%s&to=%s&text=%s"\
			% (self.server, self.port, self.un, self.pw, dest, msg_enc)
		).read()
		
		# for now, just return a boolean to show whether
		# kannel accepted the sms or not. todo: raise an
		# exception with the error message upon failure
		return res.startswith("0: Accepted")




# if this is invoked directly, test things out by listening
# for incomming SMSs, and relaying them to a test number.
# obviously, for this to work, the kannel user + password 
# must be correct (see /etc/kannel/kannel.conf)
if __name__ == "__main__":
	
	dest = raw_input("Please enter a phone number to receive SMS: ").strip()
	sender = SmsSender(username="mobile", password="mobile")

	class TestReceiver():
		def iGotAnSMS(self, caller, msg):
			msg = "%s says: %s" % (caller, msg)
			sender.send(dest, msg)
			print msg
	
	tr = TestReceiver()
	print "Waiting for incomming SMS..."
	SmsReceiver(tr.iGotAnSMS).run()

