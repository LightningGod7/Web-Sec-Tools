class waf_fingerprint:
    def __init__(self, variables):
        self.module_variables = variables["module_variables"]

    def initialize_before_run(self,tools,variables):
        ### GET common variables
        self.variables = variables
        common_vars = variables.get("common_variables")
        self.target = common_vars["RHOST"]["Value"]
        self.port = common_vars["RPORT"]["Value"]
        self.xss = tools.get("wafw00f")

    def test(self):
        print("Imported this module")
        print(self.target)
        print(self.wafw00f)

    def get_command_list(self):
        return self.waf_fingerprint()

    def waf_fingerprint(self):
        if not self.target:
            print("Not all compulsory options are set. Check with `options` command")
            return
        self.url = "http://" + self.target

        prefix = self.wafw00f
        target_arg = "-a " + self.url
        command_list = [prefix, target_arg]
        return command_list