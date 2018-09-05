from collections import OrderedDict
import os

import yaml


class CmdlineParser(object):
    def __init__(self):
        self.template = []
        self.configuration = OrderedDict()
        self._preparsed = False

    def format(self, configuration):
        curated_config = {}
        for key, item in configuration.items():
            if isinstance(item, dict):
                item = item['file']

            curated_config[key] = item

        return " ".join(self.template).format(**curated_config)

    def parse(self, commandline):
        if not commandline:
            return {}

        self.configuration = OrderedDict(self.parse_arguments(commandline))
        for key, value in self.configuration.items(): 
            # TODO: Support passing the same commandline but slightly different
            if key.startswith("_") and self._preparsed:
                raise RuntimeError("Cannot branch using positional arguments.")
            # Positional
            elif key.startswith("_"):
                self.template.append("{" + key + "}")
               
            # Optional
            else:
                template = self.key_to_arg(key)
                if template in self.template:
                    continue

                self.template.append(self.key_to_arg(key))

                # Ignore value as key is a boolean argument
                if isinstance(value, bool):
                    continue

                if not isinstance(value, list):
                    template = "{" + key + "}"
                    self.template.append(template)
                    continue

                for pos, item in enumerate(value):
                    template = "{" + key + "[" + str(pos) + "]}"
                    self.template.append(template)

        self._preparsed = True

        self.fetch_configurations()

        return self.configuration

    def arg_to_key(self, arg):
        arg = arg.split("=")[0]

        if arg.startswith("--") and len(arg) == 3:
            raise ValueError(
                "Arguments with two dashes should have more than one letter: {}".format(arg))

        elif not arg.startswith("--") and arg.startswith("-") and len(arg) > 2:
            raise ValueError(
                "Arguments with one dashes should have only one letter: {}".format(arg))

        return arg.lstrip("-").replace("_", "__").replace("-", "_")

    def key_to_arg(self, key):
        arg = key.replace("__", "!!!!").replace("_", "-").replace("!!!!", "_")
        if len(arg) > 1:
            return "--" + arg
        
        return "-" + arg

    def parse_paths(self, value):
        if isinstance(value, list):
            return [self.parse_paths(item) for item in value]

        if isinstance(value, str) and os.path.exists(value):
            return os.path.abspath(value)

        return value

    def parse_arguments(self, arguments):
        positional_index = 0
        argument_name = None
        pairs = []
        argument_names = set()
        for arg in arguments:
            # Key
            if arg.startswith("-"):
                arg = arg.split("=")
                argument_name = self.arg_to_key(arg[0])
                if argument_name in argument_names:
                    raise ValueError("Two arguments have the same name: {}".format(argument_name))

                argument_names.add(argument_name)
                pairs.append([argument_name, []])
                if len(arg) > 1 and "=".join(arg[1:]).strip(" "):
                    pairs[-1][1].append("=".join(arg[1:]))
            # Optional
            elif argument_name is not None and arg.strip(" "):
                pairs[-1][1].append(arg)
            # Positional
            elif argument_name is None:
                pairs.append(["_pos_{}".format(len(pairs)), arg])

        for i, [key, value] in enumerate(pairs):
            if not value:
                value = True
            elif isinstance(value, list) and len(value) == 1:
                value = value[0]

            value = self.parse_paths(value)

            pairs[i][1] = value

        return pairs

    def fetch_configurations(self, configuration=None):
        if configuration is None:
            configuration = self.configuration

        for key, item in self.configuration.items():
            if isinstance(item, str) and os.path.exists(item):
                file_config = self.load_conf_file(item)
                if file_config is None:
                    continue 

                self.configuration[key] = {'file': item, 'content': file_config}

    def load_conf_file(self, name):
        if name.endswith('.yaml'):
            with open(name, 'r') as f:
                return yaml.load(f)

        return None
